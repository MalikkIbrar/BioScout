"""
Core REST API views for the BioScout observations app.
"""

import logging
from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import Observation
from .serializers import ObservationSerializer

logger = logging.getLogger("bioscout")


class ObservationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for wildlife observations.

    list:   GET  /api/observations/          — public, paginated, filterable
    create: POST /api/observations/          — requires JWT auth
    retrieve/update/destroy: standard DRF   — requires JWT auth for write ops
    search: GET  /api/observations/search/  — full-text search
    """

    serializer_class = ObservationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """
        Return filtered queryset based on query parameters.

        Supported filters:
            ?species=eagle       — case-insensitive species name contains
            ?category=bird       — exact category match
            ?date_from=YYYY-MM-DD — observations on or after this date
            ?date_to=YYYY-MM-DD  — observations on or before this date
        """
        qs = Observation.objects.all().order_by("-date_observed")

        species = self.request.query_params.get("species")
        category = self.request.query_params.get("category")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if species:
            qs = qs.filter(species_name__icontains=species)
        if category:
            qs = qs.filter(category__iexact=category)
        if date_from:
            qs = qs.filter(date_observed__date__gte=date_from)
        if date_to:
            qs = qs.filter(date_observed__date__lte=date_to)

        return qs

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="q",
                description="Search term — matches species name or notes",
                required=True,
                type=str,
            )
        ],
        responses={200: ObservationSerializer(many=True)},
        summary="Full-text search across observations",
    )
    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def search(self, request):
        """
        Full-text search across species_name and notes fields.

        GET /api/observations/search/?q=eagle
        """
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response(
                {"error": "Query parameter 'q' is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = Observation.objects.filter(
            Q(species_name__icontains=query) | Q(notes__icontains=query)
        ).order_by("-date_observed")

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


@extend_schema(
    responses={200: None},
    summary="Platform-wide statistics",
)
@api_view(["GET"])
@permission_classes([AllowAny])
def stats_view(request):
    """
    Return aggregated platform statistics.

    GET /api/stats/

    Response includes total observations, unique species, weekly count,
    category breakdown, AI identification count, and top 5 species.
    """
    total = Observation.objects.count()
    unique_species = Observation.objects.values("species_name").distinct().count()

    week_ago = timezone.now() - timedelta(days=7)
    this_week = Observation.objects.filter(date_observed__gte=week_ago).count()

    ai_total = Observation.objects.filter(ai_identified=True).count()

    # Most common species
    top_species_qs = (
        Observation.objects.values("species_name")
        .annotate(count=Count("species_name"))
        .order_by("-count")
    )
    most_common = top_species_qs.first()
    most_common_name = most_common["species_name"] if most_common else "N/A"
    top_5 = list(top_species_qs[:5])

    # Category breakdown
    category_counts = {
        cat: Observation.objects.filter(category=cat).count()
        for cat, _ in Observation.CATEGORY_CHOICES
    }

    return Response(
        {
            "total_observations": total,
            "unique_species": unique_species,
            "most_common_species": most_common_name,
            "observations_this_week": this_week,
            "observations_by_category": category_counts,
            "ai_identifications_total": ai_total,
            "top_5_species": top_5,
        },
        status=status.HTTP_200_OK,
    )
