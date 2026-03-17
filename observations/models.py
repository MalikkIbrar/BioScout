"""
Observation model for BioScout wildlife tracking platform.
"""

from django.db import models


class Observation(models.Model):
    """
    Represents a single wildlife observation submitted by a user.
    Stores location, species info, image, and AI prediction results.
    """

    CATEGORY_CHOICES = [
        ("bird", "Bird"),
        ("mammal", "Mammal"),
        ("reptile", "Reptile"),
        ("insect", "Insect"),
        ("plant", "Plant"),
        ("other", "Other"),
    ]

    species_name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="other"
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    date_observed = models.DateTimeField(
        help_text="When the observation was made (date & time)."
    )
    notes = models.TextField(blank=True)
    image = models.ImageField(upload_to="observations/", blank=True, null=True)
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this record was first created.",
    )

    # AI result fields
    prediction_method = models.CharField(max_length=50, blank=True)
    prediction_confidence = models.FloatField(default=0.0)
    species_details = models.TextField(blank=True)
    ai_identified = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date_observed"]

    def __str__(self) -> str:
        observed_str = self.date_observed.strftime("%Y-%m-%d %H:%M")
        return (
            f"{self.species_name} @ "
            f"({self.latitude:.4f},{self.longitude:.4f}) on {observed_str}"
        )
