"""
Utility functions for the BioScout Streamlit frontend.

All API calls are centralised here so pages stay clean.
"""

import logging
from typing import Any

import requests

logger = logging.getLogger("bioscout")

API_BASE = "http://127.0.0.1:8000/api"
TIMEOUT = 15  # seconds


def _headers(token: str | None = None) -> dict:
    """Build request headers, optionally including JWT bearer token."""
    h = {"Accept": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def get_stats() -> dict | None:
    """
    Fetch platform-wide statistics from /api/stats/.

    Returns:
        Stats dict or None on failure.
    """
    try:
        resp = requests.get(f"{API_BASE}/stats/", timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("get_stats failed: %s", exc)
        return None


def get_observations(
    page: int = 1,
    species: str = "",
    category: str = "",
    date_from: str = "",
    date_to: str = "",
) -> dict | None:
    """
    Fetch paginated observations with optional filters.

    Args:
        page: Page number (1-indexed).
        species: Filter by species name (partial match).
        category: Filter by category (bird/mammal/etc).
        date_from: ISO date string YYYY-MM-DD.
        date_to: ISO date string YYYY-MM-DD.

    Returns:
        Paginated response dict with 'count', 'results', 'next', 'previous'.
    """
    params: dict[str, Any] = {"page": page}
    if species:
        params["species"] = species
    if category:
        params["category"] = category
    if date_from:
        params["date_from"] = date_from
    if date_to:
        params["date_to"] = date_to

    try:
        resp = requests.get(
            f"{API_BASE}/observations/", params=params, timeout=TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("get_observations failed: %s", exc)
        return None


def search_observations(query: str) -> list[dict] | None:
    """
    Full-text search across species name and notes.

    Args:
        query: Search term.

    Returns:
        List of matching observation dicts or None on failure.
    """
    try:
        resp = requests.get(
            f"{API_BASE}/observations/search/",
            params={"q": query},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("results", data) if isinstance(data, dict) else data
    except Exception as exc:
        logger.error("search_observations failed: %s", exc)
        return None


def submit_observation(payload: dict, image_file, token: str) -> tuple[bool, str]:
    """
    Submit a new observation to the API.

    Args:
        payload: Dict with species_name, latitude, longitude, date_observed, notes, category.
        image_file: File-like object for the image.
        token: JWT access token.

    Returns:
        Tuple of (success: bool, message: str).
    """
    try:
        files = {"image": image_file}
        resp = requests.post(
            f"{API_BASE}/observations/",
            data=payload,
            files=files,
            headers=_headers(token),
            timeout=TIMEOUT,
        )
        if resp.status_code == 201:
            return True, "Observation submitted successfully."
        return False, resp.json().get("detail", resp.text)
    except Exception as exc:
        logger.error("submit_observation failed: %s", exc)
        return False, str(exc)


def identify_species(image_file, latitude: float, longitude: float, token: str) -> dict | None:
    """
    Send an image to the AI identification endpoint.

    Args:
        image_file: File-like object.
        latitude: Observation latitude.
        longitude: Observation longitude.
        token: JWT access token.

    Returns:
        Response dict with species, confidence, method, species_details.
    """
    try:
        resp = requests.post(
            f"{API_BASE}/identify/",
            data={"latitude": latitude, "longitude": longitude},
            files={"image": image_file},
            headers=_headers(token),
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("identify_species failed: %s", exc)
        return None


def ask_species_question(question: str, species_name: str, token: str) -> dict | None:
    """
    Ask a question about a species (simple DeepSeek, no RAG).

    Args:
        question: User's question string.
        species_name: Species to ask about.
        token: JWT access token.

    Returns:
        Response dict with 'answer'.
    """
    try:
        resp = requests.post(
            f"{API_BASE}/species-qa/",
            json={"question": question, "species_name": species_name},
            headers=_headers(token),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("ask_species_question failed: %s", exc)
        return None


def ask_rag_question(question: str, token: str) -> dict | None:
    """
    Ask a question using the RAG hybrid retriever endpoint.

    Args:
        question: User's question string.
        token: JWT access token.

    Returns:
        Response dict with answer, sources, retrieval_method, scores, confidence.
    """
    try:
        resp = requests.post(
            f"{API_BASE}/species-qa/rag/",
            json={"question": question},
            headers=_headers(token),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("ask_rag_question failed: %s", exc)
        return None


def login(username: str, password: str) -> dict | None:
    """
    Authenticate and retrieve JWT tokens.

    Args:
        username: Account username.
        password: Account password.

    Returns:
        Dict with access, refresh, user info — or None on failure.
    """
    try:
        resp = requests.post(
            f"{API_BASE}/auth/login/",
            json={"username": username, "password": password},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as exc:
        logger.error("login failed: %s", exc)
        return None


def register(username: str, email: str, password: str) -> tuple[bool, str]:
    """
    Register a new user account.

    Args:
        username: Desired username.
        email: User email address.
        password: Password (min 8 chars).

    Returns:
        Tuple of (success: bool, message: str).
    """
    try:
        resp = requests.post(
            f"{API_BASE}/auth/register/",
            json={"username": username, "email": email, "password": password},
            timeout=TIMEOUT,
        )
        data = resp.json()
        if resp.status_code == 201:
            return True, data.get("message", "Registered successfully.")
        return False, data.get("error", "Registration failed.")
    except Exception as exc:
        logger.error("register failed: %s", exc)
        return False, str(exc)
