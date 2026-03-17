"""
URL configuration for the observations app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .ai_views import identify_and_save, species_qa, species_qa_rag
from .auth_views import login_view, me_view, refresh_view, register_view
from .views import ObservationViewSet, stats_view

router = DefaultRouter()
router.register(r"observations", ObservationViewSet, basename="observation")

urlpatterns = [
    # Observations CRUD + search
    path("", include(router.urls)),

    # Stats
    path("stats/", stats_view, name="stats"),

    # AI endpoints
    path("identify/", identify_and_save, name="identify"),
    path("species-qa/", species_qa, name="species_qa"),
    path("species-qa/rag/", species_qa_rag, name="species_qa_rag"),

    # Auth endpoints
    path("auth/register/", register_view, name="auth_register"),
    path("auth/login/", login_view, name="auth_login"),
    path("auth/refresh/", refresh_view, name="auth_refresh"),
    path("auth/me/", me_view, name="auth_me"),
]
