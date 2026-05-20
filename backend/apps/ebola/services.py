"""Scoring Ebola — basé strictement sur les sections 5 et 6 du formulaire INHP."""
from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

from apps.diseases.models import Disease

if TYPE_CHECKING:
    from .models import EbolaInvestigation


EBOLA_CODE = "EBOLA"


def _get_disease() -> Disease | None:
    return Disease.objects.filter(code=EBOLA_CODE).first()


def compute_ebola_risk_score(investigation: "EbolaInvestigation") -> tuple[int, str]:
    """Calcule un score de risque Ebola à partir des sections 5 et 6 du formulaire INHP.

    SECTION 5 — Évaluation épidémiologique (21 jours)
      Q1. Séjour/transit en zone Ebola                         : +25
      Q2. Contact avec cas malade/suspect                      : +35
      Q3. Funérailles / contact dépouille                      : +20
      Q4. Établissement de soins Ebola                         : +15

    SECTION 6 — Symptômes (48h)
      S1. Fièvre                                               : +10
      Température mesurée ≥ 38.5°C                             : +10 (en plus de S1)
      S2. Fatigue intense                                      : +3
      S3. Douleurs musculaires/articulaires                    : +3
      S4. Céphalées intenses                                   : +3
      S5. Maux de gorge / douleurs abdominales                 : +3
      S6. Diarrhée / nausées / vomissements                    : +5
      S7. Saignements inexpliqués (red-flag)                   : +30

    Plafonné à 100. Mapping niveau :
       0..14   -> low
       15..34  -> moderate
       35..59  -> high
       60..100 -> critical
    """
    score = 0
    exposure = getattr(investigation, "exposure", None)
    if exposure is not None:
        if exposure.visited_ebola_zone:
            score += 25
        if exposure.contact_with_case:
            score += 35
        if exposure.attended_funeral_or_touched_corpse:
            score += 20
        if exposure.visited_ebola_healthcare_facility:
            score += 15

    last = investigation.symptom_reports.order_by("-reported_at").first()
    if last is not None:
        if last.fever:
            score += 10
        if last.has_high_fever:
            score += 10
        if last.intense_fatigue:
            score += 3
        if last.muscle_joint_pain:
            score += 3
        if last.severe_headache:
            score += 3
        if last.sore_throat_or_abdominal:
            score += 3
        if last.diarrhea_nausea_vomiting:
            score += 5
        if last.unexplained_bleeding:
            score += 30

    score = max(0, min(score, 100))
    if score < 15:
        level = "low"
    elif score < 35:
        level = "moderate"
    elif score < 60:
        level = "high"
    else:
        level = "critical"
    return score, level


def apply_risk_outcome(investigation: "EbolaInvestigation") -> "EbolaInvestigation":
    """Recalcule le score, met à jour le statut et déclenche les workflows attendus."""
    from apps.quarantine.services import open_quarantine_for_investigation  # cycle protection

    score, level = compute_ebola_risk_score(investigation)
    investigation.risk_score = score
    investigation.risk_level = level

    disease = _get_disease()
    surveillance_days = disease.surveillance_days if disease else 21

    today = timezone.now().date()
    if investigation.surveillance_start is None:
        investigation.surveillance_start = today
    investigation.surveillance_end = investigation.surveillance_start + timedelta(days=surveillance_days)

    if level == "critical":
        investigation.status = "suspect"
    elif level == "high":
        investigation.status = "quarantine"
    elif level == "moderate":
        investigation.status = "surveillance"
    else:
        if investigation.status == "new":
            investigation.status = "cleared"

    investigation.save(update_fields=[
        "risk_score", "risk_level", "status", "surveillance_start", "surveillance_end",
    ])

    if level in {"high", "critical"} and disease and disease.requires_quarantine:
        open_quarantine_for_investigation(investigation, disease)

    traveler = investigation.traveler
    if level == "critical":
        traveler.current_health_status = "suspect"
    elif level == "high":
        traveler.current_health_status = "quarantine"
    elif level == "moderate":
        traveler.current_health_status = "monitoring"
    else:
        traveler.current_health_status = "cleared"
    traveler.save(update_fields=["current_health_status"])

    return investigation
