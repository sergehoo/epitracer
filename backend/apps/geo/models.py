"""Modèles géographiques (Country, EntryPoint, HealthZone) avec PostGIS."""
from __future__ import annotations

from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class EntryPointType(models.TextChoices):
    AIRPORT = "airport", _("Aéroport")
    SEAPORT = "seaport", _("Port maritime")
    LAND = "land", _("Frontière terrestre")
    RIVER = "river", _("Point fluvial")
    OTHER = "other", _("Autre")


class RiskLevel(models.TextChoices):
    LOW = "low", _("Faible")
    MODERATE = "moderate", _("Modéré")
    HIGH = "high", _("Élevé")
    RED = "red", _("Zone rouge")


class Country(BaseModel):
    code = models.CharField(_("code ISO-2"), max_length=2, unique=True, db_index=True)
    code3 = models.CharField(_("code ISO-3"), max_length=3, blank=True, db_index=True)
    name = models.CharField(_("nom"), max_length=120, db_index=True)
    name_local = models.CharField(_("nom local"), max_length=120, blank=True)
    region = models.CharField(_("région"), max_length=80, blank=True)
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.LOW)
    risk_for_diseases = models.JSONField(
        default=list, blank=True,
        help_text=_("Liste de codes maladie pour lesquelles ce pays est à risque."),
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Pays")
        verbose_name_plural = _("Pays")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class EntryPoint(BaseModel):
    """Point d'entrée sanitaire (aéroport, port, frontière terrestre)."""

    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=160, db_index=True)
    type = models.CharField(max_length=20, choices=EntryPointType.choices, db_index=True)
    iata_code = models.CharField(max_length=10, blank=True, db_index=True)
    icao_code = models.CharField(max_length=10, blank=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="entry_points")
    region = models.CharField(max_length=80, blank=True)
    city = models.CharField(max_length=120, blank=True)
    address = models.CharField(max_length=255, blank=True)
    location = gis_models.PointField(srid=4326, null=True, blank=True, geography=True)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Point d'entrée")
        verbose_name_plural = _("Points d'entrée")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["type", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.type})"


class HealthZone(BaseModel):
    """Zone sanitaire (district, sous-zone, zone rouge épidémiologique)."""

    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=160, db_index=True)
    level = models.CharField(
        max_length=20,
        choices=(
            ("country", _("Pays")),
            ("region", _("Région")),
            ("district", _("District")),
            ("commune", _("Commune")),
            ("custom", _("Zone personnalisée")),
        ),
        default="district",
    )
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children"
    )
    risk_level = models.CharField(max_length=20, choices=RiskLevel.choices, default=RiskLevel.LOW)
    geometry = gis_models.MultiPolygonField(srid=4326, null=True, blank=True, geography=True)
    population = models.PositiveIntegerField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Zone sanitaire")
        verbose_name_plural = _("Zones sanitaires")
        ordering = ["level", "name"]
