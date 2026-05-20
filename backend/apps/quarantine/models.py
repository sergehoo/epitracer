"""Quarantaine et suivi sanitaire (21 jours par défaut, configurable par maladie)."""
from __future__ import annotations

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class QuarantineStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    COMPLETED = "completed", _("Terminée")
    BROKEN = "broken", _("Rompue")
    EXTENDED = "extended", _("Prolongée")
    CANCELLED = "cancelled", _("Annulée")


class QuarantineRecord(BaseModel):
    traveler = models.ForeignKey(
        "travelers.Traveler", on_delete=models.CASCADE, related_name="quarantines"
    )
    disease = models.ForeignKey("diseases.Disease", on_delete=models.PROTECT, related_name="quarantines")
    investigation_ref = models.CharField(max_length=24, blank=True, db_index=True)
    started_on = models.DateField(db_index=True)
    expected_end_on = models.DateField(db_index=True)
    actual_end_on = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=QuarantineStatus.choices, default=QuarantineStatus.ACTIVE, db_index=True
    )
    address = models.CharField(max_length=300, blank=True)
    location = gis_models.PointField(srid=4326, null=True, blank=True, geography=True)
    notes = models.TextField(blank=True)
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="opened_quarantines",
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Quarantaine")
        verbose_name_plural = _("Quarantaines")
        indexes = [
            models.Index(fields=["status", "expected_end_on"]),
        ]

    def __str__(self) -> str:
        return f"Quarantaine {self.traveler.public_id} ({self.status})"


class DailyCheck(BaseModel):
    """Check quotidien : auto-déclaratif ou par agent terrain."""

    quarantine = models.ForeignKey(QuarantineRecord, on_delete=models.CASCADE, related_name="daily_checks")
    day_index = models.PositiveSmallIntegerField(help_text=_("Jour J0..J21 du suivi."))
    check_date = models.DateField(db_index=True)
    temperature_celsius = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    has_symptoms = models.BooleanField(default=False)
    symptoms_details = models.JSONField(default=dict, blank=True)
    reported_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="daily_checks",
    )
    is_self_reported = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    alert_raised = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        verbose_name = _("Suivi quotidien")
        verbose_name_plural = _("Suivis quotidiens")
        constraints = [
            models.UniqueConstraint(fields=["quarantine", "day_index"], name="uniq_check_per_day"),
        ]
        ordering = ["quarantine", "day_index"]


class FollowUpVisit(BaseModel):
    """Visite d'un agent terrain au domicile / lieu de confinement."""

    quarantine = models.ForeignKey(QuarantineRecord, on_delete=models.CASCADE, related_name="visits")
    visit_datetime = models.DateTimeField(db_index=True)
    agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="visits_done"
    )
    found_person = models.BooleanField(default=True)
    temperature_celsius = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    observations = models.TextField(blank=True)
    location = gis_models.PointField(srid=4326, null=True, blank=True, geography=True)
    photo = models.ImageField(upload_to="quarantine/visits/", null=True, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Visite de suivi")
        verbose_name_plural = _("Visites de suivi")
        ordering = ["-visit_datetime"]
