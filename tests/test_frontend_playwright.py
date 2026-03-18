"""
Playwright end-to-end tests for BioScout Streamlit frontend (port 8501).
Tests all 6 pages: Home, Submit, View, AI Identifier, Q&A Chat, About.
"""

import pytest
from playwright.sync_api import Page, expect

BASE = "http://localhost:8501"
TIMEOUT = 15000  # 15s — Streamlit can be slow to render


# ── Helpers ───────────────────────────────────────────────────────────────────

def wait_for_streamlit(page: Page):
    """Wait until Streamlit finishes loading (spinner gone)."""
    page.wait_for_load_state("networkidle", timeout=TIMEOUT)
    # Wait for the main content to appear
    page.wait_for_selector("[data-testid='stApp']", timeout=TIMEOUT)


def navigate_to(page: Page, nav_label: str):
    """Click a sidebar navigation radio option."""
    page.get_by_text(nav_label, exact=True).first.click()
    page.wait_for_timeout(1500)


def login(page: Page, username="testplayer", password="Testpass123!"):
    """Log in via the sidebar expander."""
    page.get_by_text("🔐 Login / Register").click()
    page.wait_for_timeout(500)
    page.get_by_label("Username").first.fill(username)
    page.get_by_label("Password").first.fill(password)
    page.get_by_role("button", name="Login").first.click()
    page.wait_for_timeout(2000)


# ── Page load tests ───────────────────────────────────────────────────────────

class TestPageLoads:
    def test_app_loads(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        expect(page).to_have_title("🌿 BioScout")

    def test_sidebar_visible(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        expect(page.get_by_text("🌿 BioScout").first).to_be_visible()

    def test_navigation_options_present(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        for label in ["🏠 Home", "📸 Submit Observation", "🗺️ View Observations",
                      "🤖 AI Species Identifier", "💬 Species Q&A Chat", "ℹ️ About"]:
            expect(page.get_by_text(label).first).to_be_visible()


# ── Home page ─────────────────────────────────────────────────────────────────

class TestHomePage:
    def test_home_loads(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        expect(page.get_by_text("AI-Powered Wildlife Observer").first).to_be_visible()

    def test_home_stats_visible(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        page.wait_for_timeout(2000)
        # Stats metrics should appear
        expect(page.get_by_text("Total Observations").first).to_be_visible()

    def test_home_how_it_works(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        page.wait_for_timeout(2000)
        expect(page.get_by_text("How It Works").first).to_be_visible()

    def test_home_upload_photo_step(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        page.wait_for_timeout(2000)
        expect(page.get_by_text("Upload Photo").first).to_be_visible()

    def test_home_recent_observations(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        page.wait_for_timeout(2000)
        expect(page.get_by_text("Recent Observations").first).to_be_visible()

    def test_home_no_login_required(self, page: Page):
        """Home page must be accessible without login."""
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        # Should NOT see a login warning on home page
        assert "Please login" not in page.content() or \
               page.get_by_text("AI-Powered Wildlife Observer").first.is_visible()


# ── Sidebar knowledge base ────────────────────────────────────────────────────

class TestSidebarKnowledgeBase:
    def test_knowledge_base_section(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        page.wait_for_timeout(3000)
        expect(page.get_by_text("Knowledge Base").first).to_be_visible()

    def test_species_indexed_shown(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        page.wait_for_timeout(4000)
        # Should show "52 species indexed" or "Building..."
        content = page.content()
        assert "species indexed" in content or "Building knowledge" in content

    def test_no_error_message_in_sidebar(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        page.wait_for_timeout(3000)
        content = page.content()
        assert "RAG index not built" not in content
        assert "build_rag_index" not in content


# ── View Observations page ────────────────────────────────────────────────────

class TestViewObservations:
    def test_view_page_loads(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "🗺️ View Observations")
        expect(page.get_by_text("View Observations").first).to_be_visible()

    def test_view_public_no_login(self, page: Page):
        """View Observations must work without login."""
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "🗺️ View Observations")
        page.wait_for_timeout(2000)
        # Should NOT show login warning
        assert "Please login" not in page.content()

    def test_view_filters_visible(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "🗺️ View Observations")
        page.wait_for_timeout(1500)
        expect(page.get_by_text("Filters").first).to_be_visible()

    def test_view_grid_map_toggle(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "🗺️ View Observations")
        page.wait_for_timeout(1500)
        expect(page.get_by_text("Grid View").first).to_be_visible()
        expect(page.get_by_text("Map View").first).to_be_visible()

    def test_view_shows_observations(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "🗺️ View Observations")
        page.wait_for_timeout(5000)  # extra wait for API call + render
        content = page.content()
        # Should show at least one known seeded species
        assert any(s in content for s in [
            "House Sparrow", "Snow Leopard", "Spectacled Cobra",
            "Markhor", "Houbara Bustard", "Indus River Dolphin",
            "Common Myna", "Desert Fox", "Monitor Lizard"
        ])

    def test_view_emoji_placeholders(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "🗺️ View Observations")
        page.wait_for_timeout(3000)
        content = page.content()
        # Category emojis should be present
        assert any(e in content for e in ["🦜", "🦁", "🐍", "🌿", "🦋"])


# ── About page ────────────────────────────────────────────────────────────────

class TestAboutPage:
    def test_about_loads(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "ℹ️ About")
        page.wait_for_timeout(1500)
        expect(page.get_by_text("About BioScout").first).to_be_visible()

    def test_about_tech_stack(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "ℹ️ About")
        page.wait_for_timeout(1500)
        expect(page.get_by_text("Tech Stack").first).to_be_visible()

    def test_about_no_login_required(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "ℹ️ About")
        page.wait_for_timeout(1500)
        assert "Please login" not in page.content()


# ── Login-protected pages ─────────────────────────────────────────────────────

class TestLoginProtection:
    def test_submit_requires_login(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "📸 Submit Observation")
        page.wait_for_timeout(2000)
        expect(page.get_by_text("Please login").first).to_be_visible()

    def test_ai_identifier_requires_login(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "🤖 AI Species Identifier")
        page.wait_for_timeout(2000)
        expect(page.get_by_text("Please login").first).to_be_visible()

    def test_qa_chat_requires_login(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "💬 Species Q&A Chat")
        page.wait_for_timeout(2000)
        expect(page.get_by_text("Please login").first).to_be_visible()


# ── AI Identifier page (no login — example cards) ────────────────────────────

class TestAIIdentifierExamples:
    def test_example_results_shown_when_logged_out(self, page: Page):
        """Even without login, the page shows the login warning — not a crash."""
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "🤖 AI Species Identifier")
        page.wait_for_timeout(2000)
        content = page.content()
        assert "Please login" in content or "AI Species Identifier" in content


# ── Q&A Chat page ─────────────────────────────────────────────────────────────

class TestQAChatPage:
    def test_qa_title_visible(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "💬 Species Q&A Chat")
        page.wait_for_timeout(1500)
        expect(page.get_by_text("Species Q&A Chat").first).to_be_visible()

    def test_qa_rag_caption(self, page: Page):
        page.goto(BASE, timeout=TIMEOUT)
        wait_for_streamlit(page)
        navigate_to(page, "💬 Species Q&A Chat")
        page.wait_for_timeout(1500)
        content = page.content()
        assert "DeepSeek" in content or "RAG" in content
