"""Ouverture & gestion des quarantaines."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from .models import QuarantineRecord, QuarantineStatus


def open_quarantine_for_investigation(investigation, disease) -> QuarantineRecord:
    """Ouvre une quarantaine si aucune n'est déjà active pour ce voyageur+maladie."""
    return open_followup(
        investigation.traveler,
        disease,
        reference=getattr(investigation, "case_number", ""),
        duration_days=disease.quarantine_days or 21,
    )


def followup_duration_days(disease) -> int:
    """Durée de suivi : protocole actif de la maladie, sinon durée de surveillance."""
    protocol = getattr(disease, "followup_protocol", None)
    if protocol is not None and protocol.is_active and protocol.duration_days:
        return protocol.duration_days
    return disease.surveillance_days or disease.quarantine_days or 21


def open_followup(traveler, disease, *, reference: str = "", duration_days: int | None = None):
    """Ouvre un dossier de suivi (voyageur, maladie) s'il n'en existe pas déjà un actif.

    Un même voyageur peut avoir un dossier par maladie : son identité n'est
    jamais dupliquée, seul le dossier de suivi est propre à chaque maladie.
    """
    existing = QuarantineRecord.objects.filter(
        traveler=traveler,
        disease=disease,
        status=QuarantineStatus.ACTIVE,
    ).first()
    if existing:
        return existing

    today = timezone.now().date()
    days = duration_days or followup_duration_days(disease)
    return QuarantineRecord.objects.create(
        traveler=traveler,
        disease=disease,
        investigation_ref=reference[:24],
        started_on=today,
        expected_end_on=today + timedelta(days=days),
        address=traveler.confinement_address,
        location=traveler.confinement_location,
        status=QuarantineStatus.ACTIVE,
    )


def close_quarantine(
    qr: QuarantineRecord, status: str = QuarantineStatus.COMPLETED
) -> QuarantineRecord:
    qr.status = status
    qr.actual_end_on = timezone.now().date()
    qr.save(update_fields=["status", "actual_end_on"])
    return qr
