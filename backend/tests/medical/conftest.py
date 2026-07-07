"""Fixtures locales pour les tests `medical`."""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from apps.medical.models import DiseaseFollowupProtocol


@pytest.fixture
def ebola_protocol(db, ebola_disease) -> DiseaseFollowupProtocol:
    return DiseaseFollowupProtocol.objects.create(
        disease=ebola_disease,
        duration_days=21,
        daily_checkin_required=True,
        critical_symptoms=["fever", "unexplained_bleeding"],
        monitored_symptoms=["fever", "fatigue", "headache"],
        escalation_rules={"missed_checkins": 2, "critical_symptom": True},
        closure_rules={"days_completed": 21, "no_critical_symptom": True},
        notification_schedule={"daily_reminder_hour": 8},
        field_visit_rules={"trigger_after_missed_checkins": 3},
        require_geolocation=True,
        geolocation_alert_after_hours=24,
        is_active=True,
    )


@pytest.fixture
def active_case(db, traveler, ebola_disease):
    """Quarantaine ACTIVE — voyageur à J3 d'un suivi de 21 jours."""
    from apps.quarantine.models import QuarantineRecord, QuarantineStatus

    return QuarantineRecord.objects.create(
        traveler=traveler,
        disease=ebola_disease,
        started_on=date.today() - timedelta(days=3),
        expected_end_on=date.today() + timedelta(days=18),
        status=QuarantineStatus.ACTIVE,
        address="Cocody",
    )
