"""
Tests for BioScout observations app.

Covers: models, REST API (CRUD, filters, search, stats),
        auth endpoints, RAG retrieval, and hybrid search.
"""

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Observation
from .rag.bm25_search import SpeciesBM25
from .rag.hybrid_retriever import HybridRetriever
from .rag.knowledge_base import get_all_documents
from .rag.vector_store import SpeciesVectorStore


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_observation(**kwargs) -> Observation:
    """Create a test observation with sensible defaults."""
    defaults = {
        "species_name": "Test Sparrow",
        "category": "bird",
        "latitude": 33.72,
        "longitude": 73.04,
        "date_observed": timezone.now(),
        "notes": "Test observation notes",
        "prediction_confidence": 0.85,
        "ai_identified": True,
    }
    defaults.update(kwargs)
    return Observation.objects.create(**defaults)


def get_jwt_client(user: User) -> APIClient:
    """Return an APIClient authenticated with a JWT token for the given user."""
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(refresh.access_token)}")
    return client


# ── Model Tests ───────────────────────────────────────────────────────────────

class ObservationModelTest(TestCase):
    def test_str_representation(self):
        obs = make_observation(species_name="House Sparrow")
        self.assertIn("House Sparrow", str(obs))

    def test_default_category_is_other(self):
        obs = Observation.objects.create(
            species_name="Unknown",
            latitude=0.0,
            longitude=0.0,
            date_observed=timezone.now(),
        )
        self.assertEqual(obs.category, "other")

    def test_ai_identified_default_false(self):
        obs = Observation.objects.create(
            species_name="Manual Entry",
            latitude=0.0,
            longitude=0.0,
            date_observed=timezone.now(),
        )
        self.assertFalse(obs.ai_identified)

    def test_category_choices(self):
        valid_categories = [c[0] for c in Observation.CATEGORY_CHOICES]
        self.assertIn("bird", valid_categories)
        self.assertIn("mammal", valid_categories)
        self.assertIn("reptile", valid_categories)
        self.assertIn("insect", valid_categories)
        self.assertIn("plant", valid_categories)
        self.assertIn("other", valid_categories)


# ── Observation API Tests ─────────────────────────────────────────────────────

class ObservationAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.auth_client = get_jwt_client(self.user)

        # Create 3 test observations
        self.obs1 = make_observation(species_name="House Sparrow", category="bird")
        self.obs2 = make_observation(species_name="Snow Leopard", category="mammal")
        self.obs3 = make_observation(species_name="Indian Cobra", category="reptile")

    def test_list_observations_public(self):
        """Unauthenticated users can list observations."""
        resp = self.client.get("/api/observations/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("results", resp.json())
        self.assertEqual(resp.json()["count"], 3)

    def test_filter_by_category(self):
        resp = self.client.get("/api/observations/?category=bird")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["species_name"], "House Sparrow")

    def test_filter_by_species(self):
        resp = self.client.get("/api/observations/?species=leopard")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.json()["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["species_name"], "Snow Leopard")

    def test_search_endpoint(self):
        resp = self.client.get("/api/observations/search/?q=cobra")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.json()["results"]
        self.assertTrue(any("Cobra" in r["species_name"] for r in results))

    def test_search_requires_q_param(self):
        resp = self.client.get("/api/observations/search/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_observation_requires_auth(self):
        """Unauthenticated POST should return 401."""
        resp = self.client.post(
            "/api/observations/",
            {"species_name": "Eagle", "latitude": 33.0, "longitude": 73.0,
             "date_observed": "2025-01-01T00:00:00Z"},
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_observation_authenticated(self):
        payload = {
            "species_name": "Golden Eagle",
            "category": "bird",
            "latitude": 35.0,
            "longitude": 74.0,
            "date_observed": "2025-06-01T10:00:00Z",
            "notes": "Spotted near Gilgit",
        }
        resp = self.auth_client.post("/api/observations/", payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.json()["species_name"], "Golden Eagle")

    def test_retrieve_single_observation(self):
        resp = self.client.get(f"/api/observations/{self.obs1.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["species_name"], "House Sparrow")

    def test_delete_requires_auth(self):
        resp = self.client.delete(f"/api/observations/{self.obs1.id}/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_authenticated(self):
        resp = self.auth_client.delete(f"/api/observations/{self.obs1.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Observation.objects.filter(id=self.obs1.id).exists())


# ── Stats API Tests ───────────────────────────────────────────────────────────

class StatsAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        make_observation(species_name="House Sparrow", category="bird", ai_identified=True)
        make_observation(species_name="Snow Leopard", category="mammal", ai_identified=True)
        make_observation(species_name="House Sparrow", category="bird", ai_identified=False)

    def test_stats_endpoint(self):
        resp = self.client.get("/api/stats/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertEqual(data["total_observations"], 3)
        self.assertEqual(data["unique_species"], 2)
        self.assertEqual(data["ai_identifications_total"], 2)
        self.assertIn("observations_by_category", data)
        self.assertEqual(data["observations_by_category"]["bird"], 2)
        self.assertEqual(data["observations_by_category"]["mammal"], 1)

    def test_stats_most_common_species(self):
        resp = self.client.get("/api/stats/")
        data = resp.json()
        self.assertEqual(data["most_common_species"], "House Sparrow")


# ── Auth Tests ────────────────────────────────────────────────────────────────

class AuthAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_new_user(self):
        resp = self.client.post(
            "/api/auth/register/",
            {"username": "newuser", "email": "new@example.com", "password": "securepass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", resp.json())

    def test_register_duplicate_username(self):
        User.objects.create_user(username="existing", password="pass")
        resp = self.client.post(
            "/api/auth/register/",
            {"username": "existing", "email": "e@example.com", "password": "pass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_valid_credentials(self):
        User.objects.create_user(username="loginuser", password="testpass123")
        resp = self.client.post(
            "/api/auth/login/",
            {"username": "loginuser", "password": "testpass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.json()
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertIn("user", data)

    def test_login_invalid_credentials(self):
        resp = self.client.post(
            "/api/auth/login/",
            {"username": "nobody", "password": "wrongpass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint_requires_auth(self):
        resp = self.client.get("/api/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint_authenticated(self):
        user = User.objects.create_user(username="meuser", password="pass123")
        auth_client = get_jwt_client(user)
        resp = auth_client.get("/api/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["username"], "meuser")


# ── RAG System Tests ──────────────────────────────────────────────────────────

class KnowledgeBaseTest(TestCase):
    def test_knowledge_base_has_50_documents(self):
        docs = get_all_documents()
        self.assertEqual(len(docs), 52)

    def test_all_documents_have_required_fields(self):
        required = ["species_name", "category", "description", "conservation_status"]
        for doc in get_all_documents():
            for field in required:
                self.assertIn(field, doc, f"Missing '{field}' in {doc.get('species_name')}")

    def test_categories_are_valid(self):
        valid = {"bird", "mammal", "reptile", "insect", "plant"}
        for doc in get_all_documents():
            self.assertIn(doc["category"], valid, f"Invalid category in {doc['species_name']}")

    def test_pakistan_species_present(self):
        docs = get_all_documents()
        pakistan_docs = [d for d in docs if d.get("found_in_pakistan")]
        self.assertGreater(len(pakistan_docs), 40)


class BM25SearchTest(TestCase):
    def setUp(self):
        self.documents = get_all_documents()
        self.bm25 = SpeciesBM25(self.documents)

    def test_snow_leopard_query(self):
        results = self.bm25.search_bm25("snow leopard", top_k=3)
        names = [r["species_name"] for r in results]
        self.assertIn("Snow Leopard", names)

    def test_returns_top_k_results(self):
        results = self.bm25.search_bm25("bird Pakistan", top_k=5)
        self.assertLessEqual(len(results), 5)

    def test_scores_normalised_0_to_1(self):
        results = self.bm25.search_bm25("cobra venomous", top_k=3)
        for r in results:
            self.assertGreaterEqual(r["bm25_score"], 0.0)
            self.assertLessEqual(r["bm25_score"], 1.0)

    def test_empty_query_returns_empty(self):
        results = self.bm25.search_bm25("", top_k=3)
        self.assertEqual(results, [])

    def test_result_has_required_fields(self):
        results = self.bm25.search_bm25("eagle", top_k=1)
        if results:
            r = results[0]
            self.assertIn("species_name", r)
            self.assertIn("bm25_score", r)
            self.assertIn("description", r)


class VectorStoreTest(TestCase):
    def setUp(self):
        self.vs = SpeciesVectorStore()

    def test_vector_store_has_documents(self):
        stats = self.vs.get_stats()
        self.assertGreater(stats["total_documents"], 0)

    def test_vector_search_returns_results(self):
        results = self.vs.search_vector("endangered big cat mountains", top_k=3)
        self.assertGreater(len(results), 0)

    def test_vector_scores_in_range(self):
        results = self.vs.search_vector("bird Pakistan", top_k=3)
        for r in results:
            self.assertGreaterEqual(r["vector_score"], 0.0)
            self.assertLessEqual(r["vector_score"], 1.0)


class HybridRetrieverTest(TestCase):
    def setUp(self):
        self.retriever = HybridRetriever()

    def test_hybrid_search_returns_results(self):
        results = self.retriever.hybrid_search("snow leopard Pakistan", top_k=3)
        self.assertGreater(len(results), 0)

    def test_hybrid_search_finds_snow_leopard(self):
        results = self.retriever.hybrid_search("What do snow leopards eat?", top_k=3)
        names = [r["species_name"] for r in results]
        self.assertIn("Snow Leopard", names)

    def test_hybrid_search_finds_lahore_birds(self):
        results = self.retriever.hybrid_search("birds common in Lahore", top_k=3)
        names = [r["species_name"] for r in results]
        self.assertTrue(
            any(n in names for n in ["House Sparrow", "Common Myna", "Black Kite"])
        )

    def test_combined_score_present(self):
        results = self.retriever.hybrid_search("venomous snake", top_k=3)
        for r in results:
            self.assertIn("combined_score", r)
            self.assertGreater(r["combined_score"], 0)

    def test_format_context_not_empty(self):
        results = self.retriever.hybrid_search("peacock India", top_k=2)
        context = self.retriever.format_context(results)
        self.assertIn("Source", context)
        self.assertGreater(len(context), 50)

    def test_format_context_empty_docs(self):
        context = self.retriever.format_context([])
        self.assertIn("No relevant", context)
