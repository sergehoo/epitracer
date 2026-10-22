"""Portail public : publication des contenus et parcours voyageur multimaladies."""

from __future__ import annotations

import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.utils import timezone

from apps.diseases.models import Disease
from apps.geo.models import CountryRiskLevel
from apps.geo.services import current_assessments

from .models import PUBLISHER_ROLES, NoticeStatus, PublicNotice

logger = logging.getLogger(__name__)

EBOLA_CODE = "EBOLA"  # parcours historique INHP (sections 5 et 6 dédiées)


# --------------------------------------------------------------------------- publication


def can_publish(user) -> bool:
    if not user or not user.is_authenticated or not user.is_active:
        return False
    return bool(user.is_superuser or user.has_role(*PUBLISHER_ROLES))


def _require_publisher(user) -> None:
    if not can_publish(user):
        raise PermissionDenied("Publication réservée aux administrateurs habilités.")


def publish_disease(disease: Disease, user) -> Disease:
    _require_publisher(user)
    missing = [f for f in ("slug", "description") if not getattr(disease, f)]
    if missing:
        raise ValidationError({f: "Champ requis avant publication." for f in missing})
    disease.is_published = True
    disease.published_at = timezone.now()
    disease.published_by = user
    disease._change_reason = "Publication sur le portail"
    disease.save(update_fields=["is_published", "published_at", "published_by", "updated_at"])
    return disease


def unpublish_disease(disease: Disease, user) -> Disease:
    _require_publisher(user)
    disease.is_published = False
    disease._change_reason = "Retrait du portail"
    disease.save(update_fields=["is_published", "updated_at"])
    return disease


def publish_notice(notice: PublicNotice, user) -> PublicNotice:
    _require_publisher(user)
    if not notice.title.strip() or not (notice.summary.strip() or notice.body.strip()):
        raise ValidationError({"body": "Titre et contenu requis avant publication."})
    notice.status = NoticeStatus.PUBLISHED
    notice.published_at = timezone.now()
    notice.published_by = user
    notice.save(update_fields=["status", "published_at", "published_by", "updated_at"])
    return notice


def archive_notice(notice: PublicNotice, user) -> PublicNotice:
    _require_publisher(user)
    notice.status = NoticeStatus.ARCHIVED
    notice.save(update_fields=["status", "updated_at"])
    return notice


# ---------------------------------------------------------------------- traductions


def localized(obj, field: str, lang: str | None, translations_attr: str):
    """Valeur traduite si disponible pour `lang`, sinon la valeur française."""
    if lang and not lang.startswith("fr"):
        tr = (getattr(obj, translations_attr, None) or {}).get(lang[:2], {})
        if isinstance(tr, dict) and tr.get(field):
            return tr[field]
    return getattr(obj, field)


def split_lines(text: str) -> list[str]:
    return [line.strip(" •-\t") for line in (text or "").splitlines() if line.strip(" •-\t")]


# ------------------------------------------------------------ formulaire voyageur


def screening_diseases():
    """Maladies sous surveillance active proposées dans le formulaire voyageur."""
    return (
        Disease.objects.filter(is_active=True)
        .prefetch_related("symptoms", "risk_factors")
        .select_related("followup_protocol")
        .order_by("name")
    )


def apply_screenings(traveler, screenings: list[dict]) -> list[dict]:
    """Ouvre un suivi par maladie active concernée, pour le même voyageur.

    Une maladie est retenue si le voyageur déclare une exposition ou un
    symptôme de son protocole, ou s'il a séjourné dans un pays où elle est
    évaluée au moins « modérée ». Ebola garde son parcours dédié.
    """
    from apps.medical.models import FollowUpAction, FollowUpActionType
    from apps.quarantine.services import followup_duration_days, open_followup

    answers = {str(s.get("disease", "")).upper(): s for s in screenings or []}
    country_ids = list(traveler.travel_history.values_list("country_id", flat=True))
    opened: list[dict] = []

    for disease in screening_diseases().exclude(code=EBOLA_CODE):
        answer = answers.get(disease.code, {})
        allowed_exposures = {rf.code for rf in disease.risk_factors.all()}
        allowed_symptoms = {s.code for s in disease.symptoms.all()}
        exposures = [c for c in answer.get("exposures") or [] if c in allowed_exposures]
        symptoms = [c for c in answer.get("symptoms") or [] if c in allowed_symptoms]
        risk_countries = sorted(
            set(
                current_assessments()
                .filter(country_id__in=country_ids)
                .filter(Q(disease=disease) | Q(disease__isnull=True))
                .exclude(risk_level=CountryRiskLevel.NORMAL)
                .values_list("country__code", flat=True)
            )
        )
        if not (exposures or symptoms or risk_countries):
            continue

        duration = followup_duration_days(disease)
        case = open_followup(traveler, disease, reference="PORTAIL", duration_days=duration)
        reasons = []
        if risk_countries:
            reasons.append(f"séjour/transit : {', '.join(risk_countries)}")
        if exposures:
            reasons.append(f"exposition déclarée : {', '.join(exposures)}")
        if symptoms:
            reasons.append(f"symptômes déclarés : {', '.join(symptoms)}")
        FollowUpAction.objects.create(
            followup_case=case,
            action_type=FollowUpActionType.SCREENING,
            title=f"Questionnaire d'entrée — {disease.name}",
            description="; ".join(reasons),
            performed_at=timezone.now(),
            metadata={
                "exposures": exposures,
                "symptoms": symptoms,
                "risk_countries": risk_countries,
            },
        )
        opened.append(
            {
                "disease_code": disease.code,
                "disease_name": disease.name,
                "duration_days": duration,
                "reasons": reasons,
            }
        )
    return opened
