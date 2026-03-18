"""
Backend API integration tests — runs against live Django server on port 8000.
Tests every endpoint: auth, observations, stats, AI, RAG Q&A.
"""

import requests
import pytest

BASE = "http://localhost:8000"

# ── Helpers ───────────────────────────────────────────────────────────────────

def register_and_login(username="testplayer", password="Testpass123!"):
    requests.post(f"{BASE}/api/auth/register/", json={
        "username": username, "email": f"{username}@test.com", "password": password
    })
    r = requests.post(f"{BASE}/api/auth/login/", json={
        "username": username, "password": password
    })
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access"]


TOKEN = None

def get_token():
    global TOKEN
    if TOKEN is None:
        TOKEN = register_and_login("pw_tester", "Testpass123!")
    return TOKEN


def auth_headers():
    return {"Authorization": f"Bearer {get_token()}"}


# ── Server health ─────────────────────────────────────────────────────────────

class TestServerHealth:
    def test_django_is_running(self):
        r = requests.get(f"{BASE}/api/stats/", timeout=5)
        assert r.status_code == 200

    def test_api_docs_accessible(self):
        r = requests.get(f"{BASE}/api/docs/", timeout=5)
        assert r.status_code == 200

    def test_schema_endpoint(self):
        r = requests.get(f"{BASE}/api/schema/", timeout=5)
        assert r.status_code == 200


# ── Auth endpoints ────────────────────────────────────────────────────────────

class TestAuth:
    def test_register_new_user(self):
        import time
        uname = f"user_{int(time.time())}"
        r = requests.post(f"{BASE}/api/auth/register/", json={
            "username": uname, "email": f"{uname}@x.com", "password": "Pass1234!"
        })
        assert r.status_code == 201
        assert "message" in r.json()

    def test_register_duplicate_fails(self):
        requests.post(f"{BASE}/api/auth/register/", json={
            "username": "dupuser", "email": "dup@x.com", "password": "Pass1234!"
        })
        r = requests.post(f"{BASE}/api/auth/register/", json={
            "username": "dupuser", "email": "dup2@x.com", "password": "Pass1234!"
        })
        assert r.status_code == 400

    def test_login_valid(self):
        requests.post(f"{BASE}/api/auth/register/", json={
            "username": "logintest", "email": "lt@x.com", "password": "Pass1234!"
        })
        r = requests.post(f"{BASE}/api/auth/login/", json={
            "username": "logintest", "password": "Pass1234!"
        })
        assert r.status_code == 200
        data = r.json()
        assert "access" in data
        assert "refresh" in data
        assert "user" in data

    def test_login_invalid(self):
        r = requests.post(f"{BASE}/api/auth/login/", json={
            "username": "nobody", "password": "wrongpass"
        })
        assert r.status_code == 401

    def test_me_requires_auth(self):
        r = requests.get(f"{BASE}/api/auth/me/")
        assert r.status_code == 401

    def test_me_with_auth(self):
        r = requests.get(f"{BASE}/api/auth/me/", headers=auth_headers())
        assert r.status_code == 200
        assert "username" in r.json()


# ── Observations endpoints ────────────────────────────────────────────────────

class TestObservations:
    def test_list_public(self):
        r = requests.get(f"{BASE}/api/observations/")
        assert r.status_code == 200
        data = r.json()
        assert "results" in data
        assert "count" in data

    def test_list_has_seeded_data(self):
        r = requests.get(f"{BASE}/api/observations/")
        assert r.json()["count"] >= 22

    def test_filter_by_category_bird(self):
        r = requests.get(f"{BASE}/api/observations/?category=bird")
        assert r.status_code == 200
        results = r.json()["results"]
        for obs in results:
            assert obs["category"] == "bird"

    def test_filter_by_category_mammal(self):
        r = requests.get(f"{BASE}/api/observations/?category=mammal")
        assert r.status_code == 200
        results = r.json()["results"]
        for obs in results:
            assert obs["category"] == "mammal"

    def test_filter_by_species(self):
        r = requests.get(f"{BASE}/api/observations/?species=sparrow")
        assert r.status_code == 200
        results = r.json()["results"]
        assert any("Sparrow" in o["species_name"] for o in results)

    def test_search_endpoint(self):
        r = requests.get(f"{BASE}/api/observations/search/?q=cobra")
        assert r.status_code == 200
        results = r.json()["results"]
        assert any("Cobra" in o["species_name"] for o in results)

    def test_search_requires_q(self):
        r = requests.get(f"{BASE}/api/observations/search/")
        assert r.status_code == 400

    def test_create_requires_auth(self):
        r = requests.post(f"{BASE}/api/observations/", json={
            "species_name": "Eagle", "latitude": 33.0, "longitude": 73.0,
            "date_observed": "2025-01-01T00:00:00Z"
        })
        assert r.status_code == 401

    def test_create_authenticated(self):
        r = requests.post(f"{BASE}/api/observations/", json={
            "species_name": "Golden Eagle",
            "category": "bird",
            "latitude": 35.0,
            "longitude": 74.0,
            "date_observed": "2025-06-01T10:00:00Z",
            "notes": "Spotted near Gilgit"
        }, headers=auth_headers())
        assert r.status_code == 201
        assert r.json()["species_name"] == "Golden Eagle"

    def test_retrieve_single(self):
        # Get first observation id
        r = requests.get(f"{BASE}/api/observations/")
        obs_id = r.json()["results"][0]["id"]
        r2 = requests.get(f"{BASE}/api/observations/{obs_id}/")
        assert r2.status_code == 200
        assert "species_name" in r2.json()

    def test_delete_requires_auth(self):
        r = requests.get(f"{BASE}/api/observations/")
        obs_id = r.json()["results"][0]["id"]
        r2 = requests.delete(f"{BASE}/api/observations/{obs_id}/")
        assert r2.status_code == 401

    def test_pagination_structure(self):
        r = requests.get(f"{BASE}/api/observations/?page=1")
        data = r.json()
        assert "next" in data
        assert "previous" in data
        assert "count" in data
        assert "results" in data


# ── Stats endpoint ────────────────────────────────────────────────────────────

class TestStats:
    def test_stats_returns_200(self):
        r = requests.get(f"{BASE}/api/stats/")
        assert r.status_code == 200

    def test_stats_fields_present(self):
        data = requests.get(f"{BASE}/api/stats/").json()
        assert "total_observations" in data
        assert "unique_species" in data
        assert "observations_this_week" in data
        assert "ai_identifications_total" in data
        assert "observations_by_category" in data
        assert "most_common_species" in data

    def test_stats_total_gte_22(self):
        data = requests.get(f"{BASE}/api/stats/").json()
        assert data["total_observations"] >= 22

    def test_stats_this_week_lte_total(self):
        data = requests.get(f"{BASE}/api/stats/").json()
        assert data["observations_this_week"] <= data["total_observations"]

    def test_stats_this_week_is_5(self):
        data = requests.get(f"{BASE}/api/stats/").json()
        # Seeded with exactly 5 in last 7 days
        assert data["observations_this_week"] == 5

    def test_stats_category_breakdown(self):
        data = requests.get(f"{BASE}/api/stats/").json()
        cats = data["observations_by_category"]
        assert "bird" in cats
        assert "mammal" in cats
        assert "reptile" in cats
        assert "insect" in cats
        assert "plant" in cats

    def test_stats_unique_species_gte_22(self):
        data = requests.get(f"{BASE}/api/stats/").json()
        assert data["unique_species"] >= 22


# ── RAG Q&A endpoint ─────────────────────────────────────────────────────────

class TestRAG:
    def test_rag_endpoint_requires_auth(self):
        r = requests.post(f"{BASE}/api/species-qa/rag/", json={"question": "test"})
        assert r.status_code == 401

    def test_rag_snow_leopard(self):
        r = requests.post(f"{BASE}/api/species-qa/rag/",
            json={"question": "What do snow leopards eat?"},
            headers=auth_headers()
        )
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "sources" in data
        assert len(data["answer"]) > 20

    def test_rag_sources_returned(self):
        r = requests.post(f"{BASE}/api/species-qa/rag/",
            json={"question": "Tell me about venomous snakes in Pakistan"},
            headers=auth_headers()
        )
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data["sources"], list)
        assert len(data["sources"]) > 0

    def test_rag_missing_question(self):
        r = requests.post(f"{BASE}/api/species-qa/rag/",
            json={},
            headers=auth_headers()
        )
        assert r.status_code == 400
