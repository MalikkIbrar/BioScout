"""
AI-powered views for species identification and Q&A.

Uses DeepSeek Vision API for image-based species identification
and the RAG hybrid retriever for grounded Q&A responses.
"""

import logging
import os

import requests
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from openai import OpenAI
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from .models import Observation

logger = logging.getLogger("bioscout")

# DeepSeek client — OpenAI-compatible
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)
MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# Dynamic base URL — no hardcoded ngrok
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

INAT_PLACE_ID = 27608  # Islamabad region


def get_species_details(species_name: str) -> str:
    """
    Generate a concise species fact summary using DeepSeek.

    Args:
        species_name: Common or scientific name of the species.

    Returns:
        A short paragraph describing the species, habitat, and conservation status.
    """
    prompt = (
        f"Give a concise description (3-4 sentences), typical habitat, and "
        f"conservation status for '{species_name}'. "
        f"Mention if it is found in Pakistan or South Asia. Be factual and brief."
    )
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.warning("DeepSeek species details failed for %s: %s", species_name, exc)
        return "No additional details available."


def _try_inat_identify(image_url: str) -> tuple[str, float, str]:
    """
    Attempt species identification via iNaturalist Identify API.

    Args:
        image_url: Publicly accessible URL of the uploaded image.

    Returns:
        Tuple of (species_name, confidence, method).
    """
    try:
        resp = requests.get(
            "https://api.inaturalist.org/v2/observations/identify",
            params={"images[0]": image_url, "preferred_place_id": INAT_PLACE_ID},
            timeout=10,
        )
        data = resp.json()
        if data.get("results"):
            best = data["results"][0]
            return best["taxon"]["name"], float(best.get("score", 0)), "iNaturalist"
    except Exception as exc:
        logger.warning("iNaturalist identify failed: %s", exc)
    return "", 0.0, ""


def _try_deepseek_vision(image_url: str) -> tuple[str, float, str]:
    """
    Identify species from an image using DeepSeek Vision.

    Args:
        image_url: Publicly accessible URL of the uploaded image.

    Returns:
        Tuple of (species_name, confidence, method).
    """
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert wildlife biologist. "
                        "When given an image, identify the species shown. "
                        "Respond with ONLY: Common Name (Scientific Name). "
                        "Example: House Sparrow (Passer domesticus)"
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Identify the species in this image.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                },
            ],
            max_tokens=80,
        )
        species = resp.choices[0].message.content.strip()
        return species, 0.75, "DeepSeek Vision"
    except Exception as exc:
        logger.error("DeepSeek vision identify failed: %s", exc)
    return "Unknown Species", 0.0, "Unknown"


@api_view(["POST"])
@parser_classes([MultiPartParser])
@permission_classes([IsAuthenticated])
def identify_and_save(request):
    """
    Identify a species from an uploaded image and save the observation.

    Workflow:
      1. Try iNaturalist Identify API (free, no key needed).
      2. If confidence < 0.3, fall back to DeepSeek Vision.
      3. Fetch species details from DeepSeek text model.
      4. Save everything to the database.

    Request (multipart/form-data):
        image: Image file (jpg/png)
        latitude: float
        longitude: float
        date_observed: ISO datetime string (optional)
        notes: string (optional)
        category: string (optional)

    Returns:
        JSON with species, confidence, method, details, observation_id.
    """
    img = request.FILES.get("image")
    latitude = request.data.get("latitude")
    longitude = request.data.get("longitude")

    if not img or not latitude or not longitude:
        return Response(
            {"error": "image, latitude, and longitude are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Parse date_observed
    date_observed_raw = request.data.get("date_observed", "").strip()
    date_observed = parse_datetime(date_observed_raw) if date_observed_raw else None
    if date_observed is None:
        date_observed = timezone.now()

    notes = request.data.get("notes", "")
    category = request.data.get("category", "other")

    # Save image first to get a URL
    obs = Observation.objects.create(
        species_name="Identifying...",
        latitude=float(latitude),
        longitude=float(longitude),
        date_observed=date_observed,
        notes=notes,
        category=category,
        image=img,
        ai_identified=True,
    )

    # Build absolute image URL using configured BASE_URL
    image_url = f"{BASE_URL}{obs.image.url}"
    logger.info("Identifying species from image: %s", image_url)

    # Step 1: iNaturalist
    pred_species, confidence, method = _try_inat_identify(image_url)

    # Step 2: DeepSeek Vision fallback
    if confidence < 0.3 or not pred_species:
        pred_species, confidence, method = _try_deepseek_vision(image_url)

    # Step 3: Species details
    species_details = get_species_details(pred_species)

    # Step 4: Update observation
    obs.species_name = pred_species
    obs.prediction_method = method
    obs.prediction_confidence = confidence
    obs.species_details = species_details
    obs.save()

    logger.info("Identified: %s (%.2f) via %s", pred_species, confidence, method)

    return Response(
        {
            "species": pred_species,
            "confidence": confidence,
            "method": method,
            "species_details": species_details,
            "observation_id": obs.id,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def species_qa(request):
    """
    Answer a question about a species using DeepSeek (no RAG).

    Request JSON:
        question: str
        species_name: str

    Returns:
        JSON with answer string.
    """
    question = request.data.get("question", "").strip()
    species_name = request.data.get("species_name", "").strip()

    if not question or not species_name:
        return Response(
            {"error": "Both 'question' and 'species_name' are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    prompt = (
        f"Answer this question about '{species_name}': {question}\n"
        f"Focus on Pakistan and South Asia where relevant. Be factual and concise."
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert wildlife biologist specializing in South Asian fauna and flora.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
        )
        answer = resp.choices[0].message.content.strip()
    except Exception as exc:
        logger.error("DeepSeek Q&A failed: %s", exc)
        return Response(
            {"error": "AI service unavailable. Please try again later."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({"answer": answer}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def species_qa_rag(request):
    """
    Answer a question using the RAG hybrid retriever + DeepSeek.

    Retrieves relevant species documents from the knowledge base
    (BM25 + vector hybrid search), then sends grounded context to
    DeepSeek to generate a factual answer.

    Request JSON:
        question: str

    Returns:
        JSON with answer, sources, retrieval metadata.
    """
    question = request.data.get("question", "").strip()
    if not question:
        return Response(
            {"error": "'question' is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        from .rag.hybrid_retriever import HybridRetriever

        retriever = HybridRetriever()
        results = retriever.hybrid_search(question, top_k=3)
        context = retriever.format_context(results)
        sources = [r["species_name"] for r in results]
        scores = [round(r.get("combined_score", 0.0), 3) for r in results]
    except Exception as exc:
        logger.error("RAG retrieval failed: %s", exc)
        context = ""
        sources = []
        scores = []

    system_prompt = (
        "You are an expert wildlife biologist specializing in South Asian and Pakistani wildlife. "
        "Answer questions using ONLY the provided context. "
        "If the information is not in the context, say: "
        "'I don't have specific information about that in my knowledge base, but I can tell you...' "
        "Always mention the source species name when referencing facts."
    )

    user_prompt = (
        f"Context from knowledge base:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Provide a detailed, accurate answer based on the context above."
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=400,
        )
        answer = resp.choices[0].message.content.strip()
        confidence = "high" if len(sources) >= 2 else "medium" if sources else "low"
    except Exception as exc:
        logger.error("DeepSeek RAG answer failed: %s", exc)
        return Response(
            {"error": "AI service unavailable. Please try again later."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response(
        {
            "answer": answer,
            "sources": sources,
            "retrieval_method": "hybrid_bm25_vector",
            "docs_retrieved": len(results) if "results" in dir() else 0,
            "retrieval_scores": scores,
            "confidence": confidence,
        },
        status=status.HTTP_200_OK,
    )
