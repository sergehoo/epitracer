"""Services API — orchestration métier du suivi sanitaire (Phase 9B).

Séparé de `services.py` (Phase 9A, géoloc + helpers) pour ne pas
mélanger les responsabilités. Toutes les opérations modifiant l'état
d'un cas passent par `transaction.atomic()` pour garantir l'intégrité.
"""
from __future__ import annotations

import logging
from datetime import date

from django.db import transaction
from django.http import Http404
from django.utils import timezone

from .models import (
    CaseClassification,
    FollowUpAction,
    FollowUpActionStatus,
    FollowUpActionType,
    MedicalSample,
)

logger = logging.getLogger("epidemitracker.medical")


# ---------------------------------------------------------------------------
# Génération de code de prélèvement — atomique (select_for_update)
# ---------------------------------------------------------------------------


def generate_sample_code(disease_code: str, *, year: int | None = None) -> str:
    """Génère un code prélèvement unique sous lock.

    Format : ``{DISEASE}-{YEAR}-{NNNN}`` (ex. ``EBOLA-2026-0001``).

    Sous `transaction.atomic()` + `select_for_update()` pour éviter les
    collisions en cas d'appels concurrents.
    """
    disease_code = (disease_code or "DISEASE").upper()
    year = year or date.today().year
    prefix = f"{disease_code}-{year}-"

    with transaction.atomic():
        # Le lock SELECT FOR UPDATE empêche un autre worker de lire le
        # même "dernier code" en parallèle. Sur SQLite (tests), le lock
        # est noop mais le test pytest est en single-thread donc OK.
        last = (
            MedicalSample.objects
            .select_for_update()
            .filter(sample_code__startswith=prefix)
            .order_by("-sample_code")
            .first()
        )
        if last is None:
            return f"{prefix}0001"
        try:
            n = int(last.sample_code.split("-")[-1])
        except (ValueError, IndexError):
            n = 0
        return f"{prefix}{n + 1:04d}"


# ---------------------------------------------------------------------------
# Classification — versionnée (toujours 1 seule ligne is_current=True)
# ---------------------------------------------------------------------------


def update_case_classification(*, case, classification: str, reason: str, classified_by):
    """Crée une nouvelle CaseClassification et désactive les précédentes.

    Le signal post_save sur CaseClassification se chargera ensuite de
    synchroniser `case.current_classification`.
    """
    with transaction.atomic():
        CaseClassification.objects.filter(
            followup_case=case, is_current=True,
        ).update(is_current=False)

        new_class = CaseClassification.objects.create(
            followup_case=case,
            classification=classification,
            reason=(reason or "")[:2000],
            classified_by=classified_by,
            is_current=True,
        )
    return new_class


# ---------------------------------------------------------------------------
# Clôture d'un cas
# ---------------------------------------------------------------------------


def close_followup(*, case, closure_reason: str, final_status: str,
                   notes: str, performed_by):
    """Clôture un cas de suivi (transactionnel).

    `final_status` accepte 'completed' ou 'cancelled' et est mappé vers
    le QuarantineStatus correspondant.
    """
    from apps.quarantine.models import QuarantineStatus

    if final_status == "cancelled":
        new_status = QuarantineStatus.CANCELLED
    else:
        new_status = QuarantineStatus.COMPLETED

    with transaction.atomic():
        case.status = new_status
        case.closure_reason = (closure_reason or "")[:80]
        case.actual_end_on = date.today()
        update_fields = ["status", "closure_reason", "actual_end_on", "updated_at"]
        case.save(update_fields=update_fields)

        action = FollowUpAction.objects.create(
            followup_case=case,
            action_type=FollowUpActionType.FOLLOWUP_CLOSED,
            title=f"Suivi clôturé ({closure_reason})",
            description=(notes or "")[:2000],
            performed_by=performed_by,
            status=FollowUpActionStatus.COMPLETED,
            metadata={
                "closure_reason": closure_reason,
                "final_status": final_status,
                "notes": notes or "",
            },
        )
    return action


# ---------------------------------------------------------------------------
# Assignation — agent / district / équipe
# ---------------------------------------------------------------------------


def assign_followup(*, case, assigned_agent_id=None, assigned_district_id=None,
                    assigned_team: str = "", performed_by=None):
    """Met à jour les assignations (agent / district / équipe) sur le cas."""
    from apps.accounts.models import User
    from apps.geo.models import HealthZone

    update_fields = []
    metadata = {}
    if assigned_agent_id is not None:
        if assigned_agent_id == 0:
            case.assigned_agent = None
        else:
            try:
                case.assigned_agent = User.objects.get(pk=assigned_agent_id)
            except User.DoesNotExist:
                case.assigned_agent = None
        update_fields.append("assigned_agent")
        metadata["assigned_agent_id"] = assigned_agent_id

    if assigned_district_id is not None:
        if assigned_district_id == 0:
            case.assigned_district = None
        else:
            try:
                case.assigned_district = HealthZone.objects.get(pk=assigned_district_id)
            except HealthZone.DoesNotExist:
                case.assigned_district = None
        update_fields.append("assigned_district")
        metadata["assigned_district_id"] = assigned_district_id

    if assigned_team is not None and assigned_team != "":
        case.assigned_team = assigned_team[:120]
        update_fields.append("assigned_team")
        metadata["assigned_team"] = assigned_team

    if update_fields:
        update_fields.append("updated_at")
        with transaction.atomic():
            case.save(update_fields=update_fields)
            FollowUpAction.objects.create(
                followup_case=case,
                action_type=FollowUpActionType.CONTACTED,
                title="Assignation mise à jour",
                performed_by=performed_by,
                status=FollowUpActionStatus.COMPLETED,
                metadata=metadata,
            )
    return case


# ---------------------------------------------------------------------------
# Résolution traveler + cas (public_id ou id)
# ---------------------------------------------------------------------------


def get_traveler_followup(traveler_id_or_public_id):
    """Renvoie (traveler, case) — case = QuarantineRecord active si possible.

    Raises Http404 si traveler introuvable OU pas de QuarantineRecord.
    """
    from apps.travelers.models import Traveler
    from apps.quarantine.models import QuarantineRecord, QuarantineStatus

    raw = traveler_id_or_public_id
    traveler = None
    if isinstance(raw, int) or (isinstance(raw, str) and raw.isdigit()):
        try:
            traveler = Traveler.objects.get(pk=int(raw))
        except Traveler.DoesNotExist:
            traveler = None
    if traveler is None:
        try:
            traveler = Traveler.objects.get(public_id=str(raw))
        except Traveler.DoesNotExist:
            raise Http404("Voyageur introuvable.")

    case = (
        traveler.quarantines
        .filter(status__in=[QuarantineStatus.ACTIVE, QuarantineStatus.EXTENDED])
        .order_by("-started_on")
        .first()
    )
    if case is None:
        case = traveler.quarantines.order_by("-started_on").first()
    if case is None:
        raise Http404("Aucun cas de suivi pour ce voyageur.")
    return traveler, case
