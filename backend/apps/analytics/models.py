"""Modèles d'analytique de visites.

Conçus pour rester légers (peu d'index) afin de soutenir de grandes
volumétries avec partitionnement futur par mois si besoin.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimestampedModel


class Portal(models.TextChoices):
    PUBLIC = "public", _("Portail public")
    ADMIN = "admin", _("Portail admin")
    API = "api", _("API")


class PageVisit(TimestampedModel):
    """Une visite = un page-view (envoyée par le front à chaque navigation)."""

    session_id = models.CharField(max_length=64, db_index=True)
    portal = models.CharField(
        max_length=10, choices=Portal.choices, default=Portal.PUBLIC, db_index=True
    )
    host = models.CharField(max_length=120, blank=True, db_index=True)
    path = models.CharField(max_length=400, db_index=True)
    referrer = models.CharField(max_length=500, blank=True)
    user_agent = models.CharField(max_length=400, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    country_code = models.CharField(max_length=2, blank=True, db_index=True)
    country_name = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=120, blank=True)
    language = models.CharField(max_length=12, blank=True)
    timezone = models.CharField(max_length=64, blank=True)

    is_bot = models.BooleanField(default=False, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="page_visits",
    )

    class Meta:
        verbose_name = _("Visite de page")
        verbose_name_plural = _("Visites de page")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["portal", "created_at"]),
            models.Index(fields=["country_code", "created_at"]),
        ]
