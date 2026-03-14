# backend/observations/models.py

from django.db import models

class Observation(models.Model):
    species_name   = models.CharField(max_length=100)
    latitude       = models.FloatField()
    longitude      = models.FloatField()
    date_observed  = models.DateTimeField(help_text="When the observation was made (date & time).")
    notes          = models.TextField(blank=True)
    image          = models.ImageField(upload_to='observations/')
    created_at     = models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was first created.")

    # AI result fields
    prediction_method   = models.CharField(max_length=50, blank=True)
    prediction_confidence = models.FloatField(default=0)
    species_details     = models.TextField(blank=True)

    def __str__(self):
        observed_str = self.date_observed.strftime("%Y-%m-%d %H:%M")
        return f"{self.species_name} @ ({self.latitude:.4f},{self.longitude:.4f}) on {observed_str}"
