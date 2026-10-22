"""Gestion du niveau de risque sanitaire des pays (par maladie, daté, historisé)."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from .models import COUNTRY_RISK_RANK, Country, CountryRiskAssessment, CountryRiskLevel

logger = logging.getLogger(__name__)

# Seuil à partir duquel l'arrivée d'un voyageur déclenche une alerte sanitaire.
ARRIVAL_ALERT_MIN_LEVEL = CountryRiskLevel.HIGH


def resolve_country(code: str | None) -> Country | None:
    """Retrouve un pays par code ISO-2 ou ISO-3, insensible à la casse."""
    code = (code or "").strip()
    if len(code) == 2:
        return Country.objects.filter(code__iexact=code).first()
    if len(code) == 3:
        return Country.objects.filter(code3__iexact=code).first()
    return None


def current_assessments(on: date | None = None) -> QuerySet[CountryRiskAssessment]:
    """Évaluations en vigueur à la date `on` (aujourd'hui par défaut)."""
    on = on or timezone.localdate()
    return CountryRiskAssessment.objects.filter(
        superseded_by__isnull=True,
        valid_from__lte=on,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=on))


def refresh_country_risk(country: Country, on: date | None = None) -> Country:
    """Recalcule le niveau global et la liste des maladies à risque d'un pays."""
    active = list(current_assessments(on).filter(country=country).select_related("disease"))
    level = CountryRiskLevel.NORMAL
    diseases: set[str] = set()
    for a in active:
        if COUNTRY_RISK_RANK[a.risk_level] > COUNTRY_RISK_RANK[level]:
            level = a.risk_level
        if (
            a.disease_id
            and COUNTRY_RISK_RANK[a.risk_level] >= COUNTRY_RISK_RANK[CountryRiskLevel.MODERATE]
        ):
            diseases.add(a.disease.code)
    new_diseases = sorted(diseases)
    if country.risk_level != level or list(country.risk_for_diseases or []) != new_diseases:
        country.risk_level = level
        country.risk_for_diseases = new_diseases
        country.save(update_fields=["risk_level", "risk_for_diseases", "updated_at"])
    return country


def refresh_all_country_risks(on: date | None = None) -> int:
    """Recalcule tous les pays ayant au moins une évaluation (fin de validité, etc.)."""
    countries = Country.objects.filter(risk_assessments__isnull=False).distinct()
    n = 0
    for country in countries:
        refresh_country_risk(country, on)
        n += 1
    return n


def validate_assessment(
    *,
    risk_level: str,
    justification: str,
    valid_from: date,
    valid_until: date | None,
    source_alert,
    source_reference: str,
) -> None:
    """Règles métier d'une évaluation ; lève ValidationError (dict par champ)."""
    errors: dict[str, str] = {}
    if risk_level not in CountryRiskLevel.values:
        errors["risk_level"] = "Niveau inconnu (normal, moderate, high, critical)."
    if not (justification or "").strip():
        errors["justification"] = "La justification est obligatoire."
    if valid_until and valid_from and valid_until < valid_from:
        errors["valid_until"] = "La fin de validité précède la date d'effet."
    if (
        risk_level != CountryRiskLevel.NORMAL
        and source_alert is None
        and not (source_reference or "").strip()
    ):
        errors["source_reference"] = (
            "Un niveau supérieur à « normal » doit s'appuyer sur une alerte sanitaire validée "
            "(alerte de la plateforme ou référence externe)."
        )
    if source_alert is not None and source_alert.status == "dismissed":
        errors["source_alert"] = (
            "Cette alerte a été rejetée : elle ne peut pas justifier un niveau de risque."
        )
    if errors:
        raise ValidationError(errors)


def record_risk_assessment(
    *,
    country: Country,
    risk_level: str,
    justification: str,
    disease=None,
    valid_from: date | None = None,
    valid_until: date | None = None,
    source_alert=None,
    source_reference: str = "",
    decided_by=None,
) -> CountryRiskAssessment:
    """Enregistre un nouveau niveau pour (pays, maladie) et remplace les précédents."""
    return save_new_assessment(
        CountryRiskAssessment(
            country=country,
            disease=disease,
            risk_level=risk_level,
            valid_from=valid_from or timezone.localdate(),
            valid_until=valid_until,
            justification=justification or "",
            source_alert=source_alert,
            source_reference=source_reference or "",
            decided_by=decided_by,
        )
    )


@transaction.atomic
def save_new_assessment(assessment: CountryRiskAssessment) -> CountryRiskAssessment:
    """Valide et enregistre une évaluation non sauvegardée, puis remplace les précédentes.

    Les évaluations du même couple (pays, maladie) encore actives à la date
    d'effet sont closes la veille ; celles qui n'avaient pas encore pris effet
    sont marquées remplacées. Rien n'est supprimé : l'ensemble forme l'historique.
    """
    assessment.valid_from = assessment.valid_from or timezone.localdate()
    assessment.justification = (assessment.justification or "").strip()
    assessment.source_reference = (assessment.source_reference or "").strip()
    validate_assessment(
        risk_level=assessment.risk_level,
        justification=assessment.justification,
        valid_from=assessment.valid_from,
        valid_until=assessment.valid_until,
        source_alert=assessment.source_alert,
        source_reference=assessment.source_reference,
    )
    valid_from = assessment.valid_from

    previous = (
        CountryRiskAssessment.objects.select_for_update()
        .filter(country=assessment.country, disease=assessment.disease, superseded_by__isnull=True)
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=valid_from))
    )
    to_close = list(previous.filter(valid_from__lt=valid_from))
    to_supersede = list(previous.filter(valid_from__gte=valid_from))

    assessment.save()
    for old in to_close:
        old.valid_until = valid_from - timedelta(days=1)
        old._change_reason = f"Remplacée par l'évaluation {assessment.uuid}"
        old.save(update_fields=["valid_until", "updated_at"])
    for old in to_supersede:
        old.superseded_by = assessment
        old._change_reason = f"Remplacée avant prise d'effet par {assessment.uuid}"
        old.save(update_fields=["superseded_by", "updated_at"])

    refresh_country_risk(assessment.country)
    return assessment


@transaction.atomic
def close_risk_assessment(
    assessment: CountryRiskAssessment,
    *,
    valid_until: date | None = None,
    reason: str,
) -> CountryRiskAssessment:
    """Met fin à une évaluation (retour implicite au niveau normal pour ce couple)."""
    if not (reason or "").strip():
        raise ValidationError({"reason": "La justification de clôture est obligatoire."})
    if assessment.superseded_by_id:
        raise ValidationError({"detail": "Cette évaluation a déjà été remplacée."})
    valid_until = valid_until or timezone.localdate()
    if valid_until < assessment.valid_from:
        raise ValidationError({"valid_until": "La fin de validité précède la date d'effet."})
    if assessment.valid_until and assessment.valid_until < valid_until:
        raise ValidationError({"valid_until": "L'évaluation est déjà close à une date antérieure."})
    assessment.valid_until = valid_until
    assessment._change_reason = reason.strip()
    assessment.save(update_fields=["valid_until", "updated_at"])
    refresh_country_risk(assessment.country)
    return assessment


def travel_risk_for_traveler(traveler, on: date | None = None) -> list[dict]:
    """Pays de l'historique de voyage ayant un niveau en vigueur supérieur à normal."""
    on = on or traveler.arrival_date or timezone.localdate()
    country_ids = list(traveler.travel_history.values_list("country_id", flat=True).distinct())
    if not country_ids:
        return []
    rows = (
        current_assessments(on)
        .filter(country_id__in=country_ids)
        .exclude(risk_level=CountryRiskLevel.NORMAL)
        .select_related("country", "disease")
    )
    out = [
        {
            "country_code": a.country.code,
            "country_name": a.country.name,
            "disease_code": a.disease.code if a.disease_id else None,
            "risk_level": a.risk_level,
            "assessment": str(a.uuid),
        }
        for a in rows
    ]
    out.sort(key=lambda r: COUNTRY_RISK_RANK[r["risk_level"]], reverse=True)
    return out


def alert_on_arrival_from_risk_country(traveler):
    """Règle de surveillance : alerte si le voyageur vient d'un pays à risque élevé ou critique.

    Retourne l'alerte créée, ou None. N'échoue jamais l'appelant (enregistrement public).
    """
    try:
        risks = [
            r
            for r in travel_risk_for_traveler(traveler)
            if COUNTRY_RISK_RANK[r["risk_level"]] >= COUNTRY_RISK_RANK[ARRIVAL_ALERT_MIN_LEVEL]
        ]
        if not risks:
            return None
        from apps.diseases.models import Disease
        from apps.surveillance.services import trigger_alert

        top = risks[0]
        countries = sorted({r["country_name"] for r in risks})
        disease = (
            Disease.objects.filter(code=top["disease_code"]).first()
            if top["disease_code"]
            else None
        )
        return trigger_alert(
            code="arrival_from_risk_country",
            title=f"Arrivée depuis un pays à risque {top['risk_level']} : {', '.join(countries)}",
            description=(
                f"Voyageur {traveler.public_id} : séjour ou transit déclaré dans "
                f"{', '.join(countries)} (niveau {top['risk_level']})."
            ),
            severity=top["risk_level"],
            disease=disease,
            entry_point=traveler.entry_point,
            target=traveler,
            metadata={"traveler_public_id": traveler.public_id, "risks": risks},
        )
    except Exception:  # noqa: BLE001 - une alerte ne doit pas bloquer l'enregistrement
        logger.exception(
            "Alerte pays à risque non créée pour %s", getattr(traveler, "public_id", "?")
        )
        return None
