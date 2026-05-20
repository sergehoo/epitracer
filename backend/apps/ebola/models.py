"""Module Ebola — strictement aligné sur la fiche officielle INHP
"FICHE PASSAGER EBOLA RDC 2026 DEF".

Sections du formulaire officiel :
  1. Informations sur le voyage         → champs Traveler
  2. Identité et contacts du passager   → champs Traveler
  3. Historique des déplacements        → TravelHistoryEntry (rôle origin/transit/visited)
  4. Adresse de résidence et confinement→ champs Traveler
  5. Évaluation épidémiologique du risque (21 derniers jours)  → EbolaExposureAssessment
  6. État de santé (symptômes 48 dernières heures)             → EbolaSymptomReport
  7. Certification sur l'honneur + signature                   → EbolaDeclaration

Le module conserve la notion d'enquête (`EbolaInvestigation`) qui orchestre
ces sections + score + workflow (statut, surveillance, quarantaine).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from apps.core.models import BaseModel
from apps.core.utils import short_id


class EbolaStatus(models.TextChoices):
    NEW = "new", _("Nouvelle")
    IN_REVIEW = "in_review", _("En revue")
    CLEARED = "cleared", _("Autorisé")
    UNDER_SURVEILLANCE = "surveillance", _("Sous surveillance")
    QUARANTINE = "quarantine", _("Quarantaine")
    SUSPECT = "suspect", _("Cas suspect")
    PROBABLE = "probable", _("Cas probable")
    CONFIRMED = "confirmed", _("Cas confirmé")
    RECOVERED = "recovered", _("Rétabli")
    DECEASED = "deceased", _("Décédé")
    CLOSED = "closed", _("Clôturé")


class RiskLevel(models.TextChoices):
    LOW = "low", _("Faible")
    MODERATE = "moderate", _("Modéré")
    HIGH = "high", _("Élevé")
    CRITICAL = "critical", _("Critique")


class EbolaInvestigation(BaseModel):
    """Enquête Ebola pour un voyageur donné (orchestre les sections 5/6/7)."""

    case_number = models.CharField(max_length=24, unique=True, editable=False, db_index=True)
    traveler = models.ForeignKey(
        "travelers.Traveler", on_delete=models.CASCADE, related_name="ebola_investigations"
    )
    submission = models.OneToOneField(
        "forms.FormSubmission", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="ebola_investigation",
    )

    investigator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="ebola_investigations",
    )
    entry_point = models.ForeignKey(
        "geo.EntryPoint", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="ebola_investigations",
    )
    status = models.CharField(
        max_length=20, choices=EbolaStatus.choices, default=EbolaStatus.NEW, db_index=True
    )
    risk_level = models.CharField(
        max_length=20, choices=RiskLevel.choices, default=RiskLevel.LOW, db_index=True
    )
    risk_score = models.PositiveSmallIntegerField(default=0)

    surveillance_start = models.DateField(null=True, blank=True)
    surveillance_end = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Enquête Ebola")
        verbose_name_plural = _("Enquêtes Ebola")
        indexes = [
            models.Index(fields=["status", "risk_level"]),
            models.Index(fields=["entry_point", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.case_number:
            self.case_number = short_id("EBO", length=10)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.case_number} - {self.traveler.public_id}"


class EbolaExposureAssessment(BaseModel):
    """Section 5 du formulaire — Évaluation épidémiologique du risque (21 derniers jours).

    Quatre questions oui/non, strictement reprises du DOCX :
      Q1. Avez-vous séjourné ou transité par une zone touchée par l'épidémie d'Ebola ?
          → si oui, précisez la ville/région et le pays
      Q2. Avez-vous été en contact avec une personne malade ou suspectée d'avoir Ebola ?
      Q3. Avez-vous assisté à des funérailles ou touché une dépouille humaine ?
      Q4. Avez-vous fréquenté un établissement de soins traitant des patients Ebola ?
    """

    investigation = models.OneToOneField(
        EbolaInvestigation, on_delete=models.CASCADE, related_name="exposure"
    )

    # Q1
    visited_ebola_zone = models.BooleanField(
        _("Q1. Séjourné ou transité par une zone touchée par l'épidémie d'Ebola"),
        default=False,
    )
    visited_ebola_zone_details = models.CharField(
        _("Si oui, précisez la ville/région et le pays"),
        max_length=300, blank=True,
    )

    # Q2
    contact_with_case = models.BooleanField(
        _("Q2. Contact avec une personne malade ou suspectée d'Ebola"),
        default=False,
    )

    # Q3
    attended_funeral_or_touched_corpse = models.BooleanField(
        _("Q3. Funérailles ou contact avec une dépouille humaine"),
        default=False,
    )

    # Q4
    visited_ebola_healthcare_facility = models.BooleanField(
        _("Q4. Fréquenté un établissement de soins traitant des patients Ebola"),
        default=False,
    )

    raw_exposure_score = models.PositiveSmallIntegerField(default=0)

    class Meta(BaseModel.Meta):
        verbose_name = _("Évaluation d'exposition (Section 5)")
        verbose_name_plural = _("Évaluations d'exposition (Section 5)")

    @property
    def positive_answers_count(self) -> int:
        return sum([
            self.visited_ebola_zone,
            self.contact_with_case,
            self.attended_funeral_or_touched_corpse,
            self.visited_ebola_healthcare_facility,
        ])


class EbolaSymptomReport(BaseModel):
    """Section 6 du formulaire — État de santé (symptômes 48 dernières heures).

    Sept symptômes oui/non, strictement repris du DOCX :
      S1. Fièvre (≥ 38°C) ou sensation de forte chaleur
      S2. Fatigue intense, faiblesse généralisée inexpliquée
      S3. Douleurs musculaires, articulaires ou courbatures
      S4. Maux de tête intenses (Céphalées)
      S5. Maux de gorge ou douleurs abdominales (estomac)
      S6. Diarrhée, nausées ou vomissements fréquents
      S7. Saignements inexpliqués (nez, gencives, peau, urines, selles)
    """

    investigation = models.ForeignKey(
        EbolaInvestigation, on_delete=models.CASCADE, related_name="symptom_reports"
    )
    reported_at = models.DateTimeField()
    temperature_celsius = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    fever = models.BooleanField(_("S1. Fièvre (≥38°C) / sensation de forte chaleur"), default=False)
    intense_fatigue = models.BooleanField(_("S2. Fatigue intense / faiblesse généralisée"), default=False)
    muscle_joint_pain = models.BooleanField(_("S3. Douleurs musculaires, articulaires, courbatures"), default=False)
    severe_headache = models.BooleanField(_("S4. Maux de tête intenses (Céphalées)"), default=False)
    sore_throat_or_abdominal = models.BooleanField(
        _("S5. Maux de gorge ou douleurs abdominales (estomac)"), default=False
    )
    diarrhea_nausea_vomiting = models.BooleanField(
        _("S6. Diarrhée, nausées ou vomissements fréquents"), default=False
    )
    unexplained_bleeding = models.BooleanField(
        _("S7. Saignements inexpliqués (nez, gencives, peau, urines, selles)"), default=False
    )

    other_symptoms = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="ebola_symptom_reports",
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Rapport de symptômes Ebola (Section 6)")
        verbose_name_plural = _("Rapports de symptômes Ebola (Section 6)")
        ordering = ["-reported_at"]

    @property
    def has_red_flag(self) -> bool:
        return bool(self.unexplained_bleeding)

    @property
    def has_high_fever(self) -> bool:
        return bool(self.temperature_celsius and self.temperature_celsius >= 38.5)

    @property
    def positive_symptoms_count(self) -> int:
        return sum([
            self.fever, self.intense_fatigue, self.muscle_joint_pain, self.severe_headache,
            self.sore_throat_or_abdominal, self.diarrhea_nausea_vomiting, self.unexplained_bleeding,
        ])


class EbolaDeclaration(BaseModel):
    """Section 7 — Certification sur l'honneur + signature."""

    investigation = models.OneToOneField(
        EbolaInvestigation, on_delete=models.CASCADE, related_name="declaration"
    )
    declared_at = models.DateTimeField()
    declarant_full_name = models.CharField(max_length=240)
    signed_place = models.CharField(_("Fait à"), max_length=120, blank=True)
    truthful_declaration = models.BooleanField(
        _("Certification sur l'honneur de l'exactitude des renseignements"), default=False,
    )
    consent_data_processing = models.BooleanField(default=False)
    consent_health_followup = models.BooleanField(default=False)
    consent_quarantine_if_needed = models.BooleanField(default=False)
    signature = models.ImageField(upload_to="ebola/signatures/", null=True, blank=True)
    signature_hash = models.CharField(max_length=128, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Déclaration Ebola (Section 7)")
        verbose_name_plural = _("Déclarations Ebola (Section 7)")
