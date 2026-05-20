"""Moteur multi-maladies.

Une Disease décrit les méta-données épidémiologiques utilisées par tous les
autres modules : durées de surveillance/incubation, symptômes prédéfinis,
critères de risque, niveaux de gravité, couleur, statut.
"""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from apps.core.models import BaseModel


class DiseaseSeverity(models.TextChoices):
    LOW = "low", _("Faible")
    MODERATE = "moderate", _("Modérée")
    HIGH = "high", _("Élevée")
    CRITICAL = "critical", _("Critique")


class TransmissionMode(models.TextChoices):
    AIRBORNE = "airborne", _("Aérienne")
    DROPLET = "droplet", _("Gouttelettes")
    CONTACT = "contact", _("Contact direct/indirect")
    VECTOR = "vector", _("Vectorielle")
    SEXUAL = "sexual", _("Sexuelle")
    FECAL_ORAL = "fecal_oral", _("Féco-orale")
    BLOOD = "blood", _("Sanguine")
    OTHER = "other", _("Autre")


class Disease(BaseModel):
    """Maladie surveillée par la plateforme."""

    name = models.CharField(_("nom"), max_length=120, unique=True)
    code = models.SlugField(_("code"), max_length=40, unique=True)
    short_name = models.CharField(_("nom court"), max_length=40, blank=True)
    description = models.TextField(_("description"), blank=True)

    icd11_code = models.CharField(_("code CIM-11"), max_length=40, blank=True)
    severity = models.CharField(
        _("gravité"), max_length=20, choices=DiseaseSeverity.choices, default=DiseaseSeverity.MODERATE
    )
    color = models.CharField(_("couleur (hex)"), max_length=9, default="#dc2626")

    incubation_min_days = models.PositiveSmallIntegerField(_("incubation min (jours)"), default=1)
    incubation_max_days = models.PositiveSmallIntegerField(_("incubation max (jours)"), default=14)
    surveillance_days = models.PositiveSmallIntegerField(_("durée surveillance (jours)"), default=21)
    quarantine_days = models.PositiveSmallIntegerField(_("durée quarantaine (jours)"), default=21)

    transmission_modes = models.JSONField(_("modes de transmission"), default=list, blank=True)
    risk_countries = models.JSONField(
        _("pays à risque (ISO-2)"),
        default=list,
        blank=True,
        help_text=_("Liste de codes pays ISO-2 considérés à risque."),
    )

    # Protocoles
    case_definition = models.TextField(_("définition de cas"), blank=True)
    protocols = models.JSONField(_("protocoles"), default=dict, blank=True)
    notification_rules = models.JSONField(_("règles de notification"), default=dict, blank=True)

    is_active = models.BooleanField(_("actif"), default=True, db_index=True)
    requires_quarantine = models.BooleanField(_("requiert quarantaine"), default=True)
    requires_pass = models.BooleanField(_("requiert un pass sanitaire"), default=True)

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Maladie")
        verbose_name_plural = _("Maladies")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Symptom(BaseModel):
    """Symptômes prédéfinis associés à une maladie."""

    disease = models.ForeignKey(Disease, on_delete=models.CASCADE, related_name="symptoms")
    code = models.SlugField(max_length=60)
    label = models.CharField(max_length=160)
    weight = models.PositiveSmallIntegerField(
        default=1, help_text=_("Poids du symptôme dans le calcul du score de risque.")
    )
    is_red_flag = models.BooleanField(default=False, help_text=_("Symptôme alarmant (saignement, etc.)"))
    order = models.PositiveSmallIntegerField(default=0)

    class Meta(BaseModel.Meta):
        verbose_name = _("Symptôme")
        verbose_name_plural = _("Symptômes")
        constraints = [
            models.UniqueConstraint(fields=["disease", "code"], name="uniq_symptom_per_disease"),
        ]
        ordering = ["disease", "order", "label"]

    def __str__(self) -> str:
        return f"{self.disease.code}:{self.code}"


class RiskFactor(BaseModel):
    """Critère de risque (ex : contact funérailles, voyage zone rouge)."""

    disease = models.ForeignKey(Disease, on_delete=models.CASCADE, related_name="risk_factors")
    code = models.SlugField(max_length=60)
    label = models.CharField(max_length=200)
    weight = models.PositiveSmallIntegerField(default=1)
    description = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Facteur de risque")
        verbose_name_plural = _("Facteurs de risque")
        constraints = [
            models.UniqueConstraint(fields=["disease", "code"], name="uniq_risk_factor_per_disease"),
        ]

    def __str__(self) -> str:
        return f"{self.disease.code}:{self.code}"
