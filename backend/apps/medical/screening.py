"""Qualification sanitaire à l'enregistrement d'un voyageur (multimaladies).

Pour chaque maladie sous surveillance active (hors Ebola, qui garde son
scoring INHP), les règles du protocole décident :
  - FOLLOWUP : exposition déclarée ou séjour/transit dans un pays à risque ;
  - REVIEW   : symptômes sans exposition (seuil configurable) ou symptôme
               critique → un agent tranche (confirmer ou écarter) ;
  - ISOLATED_SYMPTOM : un symptôme isolé, sous le seuil → simple trace,
               aucun suivi ouvert automatiquement.
Un même voyageur peut avoir un suivi par maladie ; son identité n'est jamais
dupliquée.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.diseases.models import Disease
from apps.geo.models import COUNTRY_RISK_RANK, CountryRiskLevel
from apps.geo.services import current_assessments

from .models import (
    FollowUpAction,
    FollowUpActionType,
    HealthScreening,
    ScreeningDecision,
    ScreeningReviewStatus,
)

EBOLA_CODE = "EBOLA"  # parcours historique INHP (sections 5 et 6 dédiées)

DEFAULT_SCREENING_RULES: dict = {
    # Exposition déclarée → suivi ouvert (sinon : revue humaine).
    "followup_on_exposure": True,
    # Séjour/transit dans un pays évalué au moins à ce niveau → suivi ouvert.
    "followup_on_risk_itinerary": True,
    "risk_itinerary_min_level": CountryRiskLevel.MODERATE,
    # Sans exposition : revue humaine à partir de N symptômes de la maladie…
    "review_min_symptoms": 2,
    # … ou dès un symptôme critique (protocole ou Symptom.is_red_flag).
    "review_on_critical_symptom": True,
    # Questions d'exposition spécifiques : "always" ou "if_risk_itinerary".
    "ask_specific_exposures": "if_risk_itinerary",
}

# Tronc commun : champs de la section « Symptômes » du formulaire → codes Symptom.
# Un symptôme déjà demandé ici n'est jamais reposé maladie par maladie.
COMMON_SYMPTOM_FIELDS: dict[str, list[str]] = {
    "fever": ["fever", "high_fever"],
    "intense_fatigue": ["fatigue", "weakness"],
    "muscle_joint_pain": ["muscle_pain", "joint_pain"],
    "severe_headache": ["headache"],
    "sore_throat_or_abdominal": ["sore_throat", "abdominal_pain"],
    "diarrhea_nausea_vomiting": ["diarrhea", "watery_diarrhea", "vomiting"],
    "unexplained_bleeding": ["bleeding", "unexplained_bleeding"],
}
COMMON_SYMPTOM_CODES = {code for codes in COMMON_SYMPTOM_FIELDS.values() for code in codes}


def is_contact_exposure(code: str) -> bool:
    """Convention : une exposition dont le code commence par « contact » porte sur un malade.

    Ces questions sont regroupées dans le tronc commun du questionnaire.
    """
    return code.startswith("contact")


def screening_diseases():
    """Maladies sous surveillance active proposées dans le questionnaire voyageur."""
    return (
        Disease.objects.filter(is_active=True)
        .prefetch_related("symptoms", "risk_factors")
        .select_related("followup_protocol")
        .order_by("name")
    )


def screening_rules(disease: Disease) -> dict:
    protocol = getattr(disease, "followup_protocol", None)
    custom = protocol.screening_rules if protocol is not None and protocol.is_active else {}
    return {**DEFAULT_SCREENING_RULES, **(custom or {})}


def critical_symptom_codes(disease: Disease) -> set[str]:
    protocol = getattr(disease, "followup_protocol", None)
    codes = {s.code for s in disease.symptoms.all() if s.is_red_flag}
    if protocol is not None and protocol.is_active:
        codes |= set(protocol.critical_symptoms or [])
    return codes


def risk_country_codes(disease: Disease, min_level: str | None = None) -> list[str]:
    """Pays (ISO-2) où la maladie — ou toutes maladies — est évaluée au moins à `min_level`."""
    min_rank = COUNTRY_RISK_RANK[min_level or screening_rules(disease)["risk_itinerary_min_level"]]
    rows = (
        current_assessments()
        .filter(Q(disease=disease) | Q(disease__isnull=True))
        .values_list("country__code", "risk_level")
    )
    return sorted({code for code, level in rows if COUNTRY_RISK_RANK[level] >= min_rank})


def symptom_codes_from_common_section(symptoms_section: dict | None) -> set[str]:
    """Codes Symptom déduits des réponses « oui » de la section symptômes commune."""
    codes: set[str] = set()
    for fld, mapped in COMMON_SYMPTOM_FIELDS.items():
        if (symptoms_section or {}).get(fld):
            codes.update(mapped)
    return codes


@dataclass
class Qualification:
    decision: str | None  # ScreeningDecision ou None (rien à signaler)
    reasons: list[str] = field(default_factory=list)
    needs_review: bool = False
    severity: str = "medium"


def qualify(
    *,
    rules: dict,
    exposures: list[str],
    symptoms: list[str],
    critical: set[str],
    risk_countries: list[str],
) -> Qualification:
    """Décision pure (sans base) pour une maladie — appliquée telle quelle par apply_screenings."""
    reasons: list[str] = []
    if risk_countries:
        reasons.append(f"séjour/transit : {', '.join(risk_countries)}")
    if exposures:
        reasons.append(f"exposition déclarée : {', '.join(exposures)}")
    if symptoms:
        reasons.append(f"symptômes déclarés : {', '.join(symptoms)}")
    critical_found = sorted(set(symptoms) & critical)

    auto_followup = (exposures and rules["followup_on_exposure"]) or (
        risk_countries and rules["followup_on_risk_itinerary"]
    )
    if auto_followup:
        # Exposé ET symptomatique : le suivi s'ouvre et un agent est alerté.
        return Qualification(
            ScreeningDecision.FOLLOWUP,
            reasons,
            needs_review=bool(symptoms),
            severity="high" if symptoms else "medium",
        )
    if exposures:  # exposition déclarée mais ouverture automatique désactivée
        return Qualification(ScreeningDecision.REVIEW, reasons, needs_review=True)
    if critical_found and rules["review_on_critical_symptom"]:
        return Qualification(ScreeningDecision.REVIEW, reasons, needs_review=True, severity="high")
    if symptoms and len(symptoms) >= rules["review_min_symptoms"]:
        return Qualification(ScreeningDecision.REVIEW, reasons, needs_review=True)
    if symptoms:
        return Qualification(ScreeningDecision.ISOLATED_SYMPTOM, reasons)
    return Qualification(None, reasons)


@transaction.atomic
def apply_screenings(
    traveler,
    screenings: list[dict] | None = None,
    *,
    symptom_codes: list[str] | None = None,
    common_symptoms: dict | None = None,
) -> list[dict]:
    """Qualifie chaque maladie active pour ce voyageur et applique la décision.

    `screenings` : [{disease, exposures, symptoms?}] ; `symptom_codes` : codes
    cochés dans « autres symptômes » ; `common_symptoms` : section symptômes
    commune (champs booléens), convertie en codes.
    """
    from apps.quarantine.services import followup_duration_days, open_followup
    from apps.surveillance.services import trigger_alert

    answers = {str(s.get("disease", "")).upper(): s for s in screenings or []}
    declared_symptoms = set(symptom_codes or []) | symptom_codes_from_common_section(
        common_symptoms
    )
    for s in screenings or []:
        declared_symptoms |= set(s.get("symptoms") or [])
    visited = set(traveler.travel_history.values_list("country__code", flat=True))

    results: list[dict] = []
    for disease in screening_diseases().exclude(code=EBOLA_CODE):
        rules = screening_rules(disease)
        answer = answers.get(disease.code, {})
        allowed_exposures = {rf.code for rf in disease.risk_factors.all()}
        exposures = sorted({c for c in answer.get("exposures") or [] if c in allowed_exposures})
        symptoms = sorted(declared_symptoms & {s.code for s in disease.symptoms.all()})
        risk_countries = sorted(
            visited & set(risk_country_codes(disease, rules["risk_itinerary_min_level"]))
        )

        q = qualify(
            rules=rules,
            exposures=exposures,
            symptoms=symptoms,
            critical=critical_symptom_codes(disease),
            risk_countries=risk_countries,
        )
        if q.decision is None:
            continue

        screening = HealthScreening.objects.create(
            traveler=traveler,
            disease=disease,
            decision=q.decision,
            reasons=q.reasons,
            answers={
                "exposures": exposures,
                "symptoms": symptoms,
                "risk_countries": risk_countries,
            },
            review_status=(
                ScreeningReviewStatus.PENDING
                if q.needs_review
                else ScreeningReviewStatus.NOT_REQUIRED
            ),
        )
        duration = followup_duration_days(disease)
        if q.decision == ScreeningDecision.FOLLOWUP:
            case = open_followup(traveler, disease, reference="PORTAIL", duration_days=duration)
            screening.followup_case = case
            screening.save(update_fields=["followup_case", "updated_at"])
            _log_screening_action(case, disease, q.reasons, screening)
        if q.needs_review:
            trigger_alert(
                code="screening_review",
                title=f"Qualification sanitaire à revoir — {disease.name}",
                description=f"Voyageur {traveler.public_id} : {'; '.join(q.reasons)}.",
                severity=q.severity,
                disease=disease,
                entry_point=traveler.entry_point,
                target=screening,
                metadata={
                    "traveler_public_id": traveler.public_id,
                    "screening": str(screening.uuid),
                },
            )
        results.append(
            {
                "disease_code": disease.code,
                "disease_name": disease.name,
                "decision": q.decision,
                "review_pending": q.needs_review,
                "duration_days": duration if q.decision == ScreeningDecision.FOLLOWUP else None,
                "reasons": q.reasons,
            }
        )
    return results


def _log_screening_action(case, disease, reasons, screening, *, performed_by=None, title=None):
    FollowUpAction.objects.create(
        followup_case=case,
        action_type=FollowUpActionType.SCREENING,
        title=title or f"Questionnaire d'entrée — {disease.name}",
        description="; ".join(reasons),
        performed_by=performed_by,
        performed_at=timezone.now(),
        metadata={**screening.answers, "screening": str(screening.uuid)},
    )


@transaction.atomic
def confirm_screening(screening: HealthScreening, *, user, note: str = "") -> HealthScreening:
    """Revue humaine : l'agent confirme → un suivi est ouvert (ou conservé)."""
    from apps.quarantine.services import followup_duration_days, open_followup

    if screening.review_status != ScreeningReviewStatus.PENDING:
        raise ValidationError(
            {"review_status": "Cette qualification n'est pas en attente de revue."}
        )
    disease = screening.disease
    case = screening.followup_case or open_followup(
        screening.traveler,
        disease,
        reference="REVUE",
        duration_days=followup_duration_days(disease),
    )
    screening.followup_case = case
    screening.decision = ScreeningDecision.FOLLOWUP
    screening.review_status = ScreeningReviewStatus.CONFIRMED
    screening.reviewed_by, screening.reviewed_at = user, timezone.now()
    screening.review_note = note.strip()
    screening.save()
    _log_screening_action(
        case,
        disease,
        screening.reasons + ([note.strip()] if note.strip() else []),
        screening,
        performed_by=user,
        title=f"Suivi confirmé après revue — {disease.name}",
    )
    return screening


def dismiss_screening(screening: HealthScreening, *, user, note: str) -> HealthScreening:
    """Revue humaine : l'agent écarte la qualification (motif obligatoire)."""
    if screening.review_status != ScreeningReviewStatus.PENDING:
        raise ValidationError(
            {"review_status": "Cette qualification n'est pas en attente de revue."}
        )
    if not (note or "").strip():
        raise ValidationError({"note": "Le motif est obligatoire pour écarter une qualification."})
    screening.review_status = ScreeningReviewStatus.DISMISSED
    screening.reviewed_by, screening.reviewed_at = user, timezone.now()
    screening.review_note = note.strip()
    screening.save(
        update_fields=[
            "review_status",
            "reviewed_by",
            "reviewed_at",
            "review_note",
            "updated_at",
        ]
    )
    return screening
