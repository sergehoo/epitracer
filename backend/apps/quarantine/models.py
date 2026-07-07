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

    # ----- Phase 9A : suivi médical complet (apps.medical) ----------------
    assigned_district = models.ForeignKey(
        "geo.HealthZone", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="assigned_quarantines",
        verbose_name=_("District sanitaire assigné"),
    )
    assigned_team = models.CharField(
        _("Équipe assignée"), max_length=120, blank=True,
    )
    assigned_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="quarantines_assigned",
        verbose_name=_("Agent assigné"),
    )
    # Cache de la classification active courante (CaseClassification.is_current).
    # Permet d'afficher la classification dans une liste sans JOIN supplémentaire.
    # Synchronisé par signals.py côté apps.medical.
    current_classification = models.CharField(
        _("Classification courante"), max_length=30, blank=True, db_index=True,
    )
    closure_reason = models.CharField(
        _("Motif de clôture"), max_length=80, blank=True,
        help_text=_("auto_completed / escalated / manual_close / lost_to_followup."),
    )
    # Anti-spam alerte géoloc (Option 3, RGPD-safe).
    geolocation_alert_raised_at = models.DateTimeField(
        _("Dernière alerte géoloc levée"), null=True, blank=True,
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Quarantaine")
        verbose_name_plural = _("Quarantaines")
        indexes = [
            models.Index(fields=["status", "expected_end_on"]),
            models.Index(fields=["assigned_agent", "status"]),
            models.Index(fields=["current_classification", "status"]),
        ]

    def __str__(self) -> str:
        return f"Quarantaine {self.traveler.public_id} ({self.status})"


class DailyCheckStatus(models.TextChoices):
    """Statut élargi d'une journée de suivi (Phase 9A).

    Le statut historique était implicite (pending vs done via has_symptoms +
    presence du record). On l'explicite ici pour pouvoir piloter le workflow
    journalier (visite programmée, prélèvement demandé, escalade…).
    """

    PLANNED = "planned", _("Planifié")
    PENDING = "pending", _("En attente")
    COMPLETED = "completed", _("Effectué")
    MISSED = "missed", _("Manqué")
    ALERT = "alert", _("Alerte")
    VISIT_SCHEDULED = "visit_scheduled", _("Visite programmée")
    SAMPLE_REQUESTED = "sample_requested", _("Prélèvement demandé")
    ANALYSIS_IN_PROGRESS = "analysis_in_progress", _("Analyse en cours")
    ESCALATED = "escalated", _("Escaladé")
    CLOSED = "closed", _("Clôturé")


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

    # ----- Phase 9A : suivi médical complet (apps.medical) ----------------
    agent_responsible = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="daily_checks_managed",
        verbose_name=_("Agent responsable"),
    )
    decision = models.CharField(
        _("Décision du jour"), max_length=200, blank=True,
    )
    status = models.CharField(
        _("Statut journée"), max_length=24,
        choices=DailyCheckStatus.choices,
        default=DailyCheckStatus.PENDING,
        db_index=True,
    )
    # Snapshot : voyageur a-t-il partagé sa position ce jour-là ?
    # Pas un consentement (cf. apps.companion.PrivacyConsent) — juste un
    # snapshot opérationnel pour la timeline.
    location_shared = models.BooleanField(
        _("Position partagée"), default=False,
    )
    notification_sent = models.BooleanField(
        _("Notification envoyée"), default=False,
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Suivi quotidien")
        verbose_name_plural = _("Suivis quotidiens")
        constraints = [
            models.UniqueConstraint(fields=["quarantine", "day_index"], name="uniq_check_per_day"),
        ]
        ordering = ["quarantine", "day_index"]

    def __str__(self) -> str:
        tag = "⚠" if self.has_symptoms else "✓"
        return f"{tag} J{self.day_index} {self.check_date} — {self.quarantine.traveler.public_id if self.quarantine_id else '?'}"


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

    def __str__(self) -> str:
        return f"Visite {self.visit_datetime:%d/%m/%Y %H:%M} — {self.quarantine.traveler.public_id if self.quarantine_id else '?'}"
