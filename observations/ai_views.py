# observations/ai_views.py

from http import client
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_datetime

import observations
from .models import Observation
from django.utils import timezone
import requests
import openai
from openai import OpenAI

import os

openai.api_key = os.getenv("OPENAI_API_KEY")

INAT_PLACE_ID = 27608  # Islamabad region

def get_species_details(species_name):
    """
    Uses GPT-4o to generate a concise fact summary for the given species.
    """
    prompt = (
        f"Give a concise description, typical habitat, and conservation status "
        f"for the species '{species_name}'. "
        f"Is it endangered in Islamabad, Pakistan? Answer concisely."
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200
    )
    return resp.choices[0].message.content.strip()

@api_view(['POST'])
@parser_classes([MultiPartParser])
def identify_and_save(request):
    img = request.FILES.get('image')
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')

    date_observed_raw = request.data.get('date_observed')
    if date_observed_raw:
        date_observed_stripped = date_observed_raw.strip()
        date_observed = parse_datetime(date_observed_stripped)
        if date_observed is None:
            date_observed = timezone.now()
    else:
        date_observed = timezone.now()
    
    notes = request.data.get('notes', '')

    if not img or not latitude or not longitude:
        return Response({"error": "Missing image or location."}, status=400)

    # Save image immediately to get its public URL
    obs = Observation.objects.create(
        latitude=latitude,
        longitude=longitude,
        date_observed=date_observed,
        notes=notes,
        image=img
    )
    image_url = request.build_absolute_uri(obs.image.url)
    
    image_url = image_url.replace("127.0.0.1:8000", "8cc7-103-248-222-204.ngrok-free.app")
    image_url = image_url.replace("localhost:8000", "8cc7-103-248-222-204.ngrok-free.app")
   # image_url = image_url.replace("localhost:8000", "ed68-103-248-222-205.ngrok-free.app")
   # image_url = image_url.replace("127.0.0.1", "192.168.1.16")

    # Step 1: Try iNaturalist Identify API
    try:
        inat_resp = requests.get(
            "https://api.inaturalist.org/v2/observations/identify",
            params={
                "images[0]": image_url,
                "preferred_place_id": INAT_PLACE_ID
            }
        )
        inat_json = inat_resp.json()
        pred_species = ""
        confidence = 0
        method = ""
        if inat_json.get("results"):
            best = inat_json["results"][0]
            pred_species = best["taxon"]["name"]
            confidence = best.get("score", 0)
            method = "iNaturalist"
    except Exception as e:
        pred_species = ""
        confidence = 0
        method = ""

    # Step 2: Fallback to ChatGPT Vision if needed
    if confidence < 0.3 or not pred_species:
        try:
            chatgpt_resp = openai.ChatCompletion.create(
                model="gpt-4-vision-preview",  # If not available, use 'gpt-4o' with image support
                messages=[
                    {"role": "system", "content": "You are an expert biologist."},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Identify the species (common and scientific name) in this image."},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                max_tokens=100
            )
            pred_species = chatgpt_resp.choices[0].message.content.strip()
            confidence = 0
            method = "ChatGPT"
        except Exception as e:
            pred_species = "Unknown"
            confidence = 0
            method = "Unknown"

    # Step 3: Get GPT-4o fact summary
    try:
        species_details = get_species_details(pred_species)
    except Exception as e:
        species_details = "No additional details available."

    # Step 4: Save everything to DB
    obs.species_name = pred_species
    obs.prediction_method = method
    obs.prediction_confidence = confidence
    obs.species_details = species_details
    obs.save()

    return Response({
        "species": pred_species,
        "confidence": confidence,
        "method": method,
        "species_details": species_details,
        "observation_id": obs.id
    })

@api_view(['POST'])
def species_qa(request):
    """
    Allows user to ask GPT-4o any question about a species.
    """
    question = request.data.get("question")
    species_name = request.data.get("species_name")
    if not question or not species_name:
        return Response({"error": "Provide both 'question' and 'species_name'"}, status=400)
    prompt = f"Answer about '{species_name}': {question}. Focus on Islamabad, Pakistan if relevant."
    try:
        resp = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200
        )
        answer = resp.choices[0].message.content.strip()
    except Exception as e:
        answer = "Could not get an answer from AI."
    return Response({"answer": answer})
