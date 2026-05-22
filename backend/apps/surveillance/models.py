"""Alertes sanitaires + indicateurs de surveillance globale."""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class AlertSeverity(models.TextChoices):
    INFO = "info", _("Information")
    LOW = "low", _("Faible")
    MEDIUM = "medium", _("Moyenne")
    HIGH = "high", _("Élevée")
    CRITICAL = "critical", _("Critique")


class AlertStatus(models.TextChoices):
    OPEN = "open", _("Ouverte")
    ACK = "ack", _("Reconnue")
    INVESTIGATING = "investigating", _("En investigation")
    RESOLVED = "resolved", _("Résolue")
    DISMISSED = "dismissed", _("Rejetée")


class HealthAlert(BaseModel):
    """Alerte sanitaire générée automatiquement ou créée manuellement."""

    code = models.SlugField(max_length=60, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=AlertSeverity.choices, default=AlertSeverity.INFO, db_index=True)
    status = models.CharField(max_length=20, choices=AlertStatus.choices, default=AlertStatus.OPEN, db_index=True)

    disease = models.ForeignKey(
        "diseases.Disease", null=True, blank=True, on_delete=models.SET_NULL, related_name="alerts"
    )
    entry_point = models.ForeignKey(
        "geo.EntryPoint", null=True, blank=True, on_delete=models.SET_NULL, related_name="alerts"
    )
    zone = models.ForeignKey(
        "geo.HealthZone", null=True, blank=True, on_delete=models.SET_NULL, related_name="alerts"
    )

    # Lien polymorphe vers la source (enquête, voyageur, quarantaine, etc.)
    target_ct = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    target_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    target = GenericForeignKey("target_ct", "target_id")

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="triggered_alerts",
    )
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="ack_alerts",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Alerte sanitaire")
        verbose_name_plural = _("Alertes sanitaires")
        indexes = [
            models.Index(fields=["severity", "status"]),
            models.Index(fields=["disease", "created_at"]),
        ]
