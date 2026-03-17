"""
Serializers for the observations app.
"""

from rest_framework import serializers
from .models import Observation


class ObservationSerializer(serializers.ModelSerializer):
    """Serializer for the Observation model — exposes all fields."""

    class Meta:
        model = Observation
        fields = "__all__"
        read_only_fields = ("created_at",)
