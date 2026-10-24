"""Modèles géographiques (Country, EntryPoint, HealthZone) avec PostGIS."""

from __future__ import annotations

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

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


class CountryRiskLevel(models.TextChoices):
    """Niveau de risque sanitaire d'un pays (distinct de HealthZone.RiskLevel)."""

    NORMAL = "normal", _("Normal")
    MODERATE = "moderate", _("Modéré")
    HIGH = "high", _("Élevé")
    CRITICAL = "critical", _("Critique")


# Ordre de gravité, pour retenir le niveau le plus élevé entre plusieurs maladies.
COUNTRY_RISK_RANK = {
    CountryRiskLevel.NORMAL: 0,
    CountryRiskLevel.MODERATE: 1,
    CountryRiskLevel.HIGH: 2,
    CountryRiskLevel.CRITICAL: 3,
}


class Country(BaseModel):
    code = models.CharField(_("code ISO-2"), max_length=2, unique=True, db_index=True)
    code3 = models.CharField(_("code ISO-3"), max_length=3, blank=True, db_index=True)
    name = models.CharField(_("nom"), max_length=120, db_index=True)
    name_local = models.CharField(_("nom local"), max_length=120, blank=True)
    region = models.CharField(_("région"), max_length=80, blank=True)
    # « Pays surveillé » (inclus dans le dispositif de veille) est indépendant
    # du niveau de risque : un pays surveillé peut être au niveau normal.
    is_monitored = models.BooleanField(_("pays surveillé"), default=False, db_index=True)
    # Niveau global courant = le plus élevé des CountryRiskAssessment en vigueur.
    # Dénormalisé pour les filtres ; recalculé par apps.geo.services.refresh_country_risk.
    risk_level = models.CharField(
        max_length=20,
        choices=CountryRiskLevel.choices,
        default=CountryRiskLevel.NORMAL,
        db_index=True,
    )
    risk_for_diseases = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Codes maladie en vigueur au niveau modéré ou plus (recalculé)."),
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Pays")
        verbose_name_plural = _("Pays")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["code3"],
                condition=~Q(code3=""),
                name="uniq_country_code3_when_set",
            ),
        ]

    def save(self, *args, **kwargs):
        self.code = (self.code or "").strip().upper()
        self.code3 = (self.code3 or "").strip().upper()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class CountryRiskAssessment(BaseModel):
    """Niveau de risque d'un pays pour une maladie, sur une période de validité.

    Une nouvelle évaluation remplace les précédentes du même couple
    (pays, maladie) à partir de sa date d'effet : les anciennes restent en base
    comme historique. `disease` vide = toutes maladies confondues.
    """

    country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="risk_assessments")
    disease = models.ForeignKey(
        "diseases.Disease",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="country_risk_assessments",
        help_text=_("Vide = toutes maladies confondues."),
    )
    risk_level = models.CharField(
        _("niveau de risque"),
        max_length=20,
        choices=CountryRiskLevel.choices,
    )
    valid_from = models.DateField(_("en vigueur du"), default=timezone.localdate, db_index=True)
    valid_until = models.DateField(_("en vigueur jusqu'au"), null=True, blank=True)
    justification = models.TextField(_("justification"))
    source_alert = models.ForeignKey(
        "surveillance.HealthAlert",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="country_risk_assessments",
    )
    source_reference = models.CharField(
        _("référence de l'alerte validée"),
        max_length=255,
        blank=True,
        help_text=_("Ex : bulletin OMS, communiqué MSHPCMU, alerte INHP."),
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    superseded_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supersedes",
        help_text=_("Évaluation qui a remplacé celle-ci avant sa date d'effet."),
    )

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Évaluation du risque pays")
        verbose_name_plural = _("Évaluations du risque pays")
        ordering = ["-valid_from", "-created_at"]
        indexes = [models.Index(fields=["country", "disease", "valid_from"])]
        constraints = [
            models.CheckConstraint(
                check=Q(valid_until__isnull=True) | Q(valid_until__gte=models.F("valid_from")),
                name="country_risk_valid_period",
            ),
        ]

    def __str__(self) -> str:
        target = self.disease.code if self.disease_id else "toutes maladies"
        return f"{self.country.code} · {target} · {self.risk_level} ({self.valid_from})"


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
            ("country", _("National")),
            ("pres", _("Pôle Régional Sanitaire (PRES)")),
            ("region", _("Région Sanitaire")),
            ("district", _("District Sanitaire")),
            ("commune", _("Commune")),
            ("quartier", _("Quartier")),
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

    def __str__(self) -> str:
        # Préfixe par niveau pour les listes admin (PRES / RÉG / DIST / etc.)
        level_short = {
            "country": "🇨🇮",
            "pres": "PRES",
            "region": "Région",
            "district": "District",
            "commune": "Commune",
            "quartier": "Quartier",
            "custom": "Zone",
        }.get(self.level, self.level)
        return f"{level_short} · {self.name}"
