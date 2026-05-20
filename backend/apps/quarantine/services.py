"""Ouverture & gestion des quarantaines."""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from .models import QuarantineRecord, QuarantineStatus


def open_quarantine_for_investigation(investigation, disease) -> QuarantineRecord:
    """Ouvre une quarantaine si aucune n'est déjà active pour ce voyageur+maladie."""
    existing = QuarantineRecord.objects.filter(
        traveler=investigation.traveler, disease=disease, status=QuarantineStatus.ACTIVE,
    ).first()
    if existing:
        return existing

    today = timezone.now().date()
    days = disease.quarantine_days or 21
    qr = QuarantineRecord.objects.create(
        traveler=investigation.traveler,
        disease=disease,
        investigation_ref=getattr(investigation, "case_number", ""),
        started_on=today,
        expected_end_on=today + timedelta(days=days),
        address=investigation.traveler.confinement_address,
        location=investigation.traveler.confinement_location,
        status=QuarantineStatus.ACTIVE,
    )
    return qr


def close_quarantine(qr: QuarantineRecord, status: str = QuarantineStatus.COMPLETED) -> QuarantineRecord:
    qr.status = status
    qr.actual_end_on = timezone.now().date()
    qr.save(update_fields=["status", "actual_end_on"])
    return qr
