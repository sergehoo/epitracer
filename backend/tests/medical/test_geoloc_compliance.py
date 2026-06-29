"""Tests `check_geolocation_compliance` — Option 3 RGPD-safe.

Scénarios couverts :
  1. Pas de protocole / `require_geolocation=False` → toujours conforme.
  2. Quarantaine non-active → conforme (rien à évaluer).
  3. Pas de consentement → alerte créée + FollowUpAction loggué.
  4. Consentement OK + ping récent → conforme.
  5. Consentement OK + dernier ping > seuil → alerte.
  6. Anti-spam : 2e appel < 24h plus tard ne re-alerte pas.
"""
from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.gis.geos import Point
from django.utils import timezone

from apps.companion.models import (
    ConsentScope,
    LocationEventType,
    LocationSource,
    TravelerLocationPing,
)
from apps.companion.services import record_consent
from apps.medical.models import FollowUpAction, FollowUpActionType
from apps.medical.services import check_geolocation_compliance
from apps.quarantine.models import QuarantineStatus
from apps.surveillance.models import HealthAlert


pytestmark = pytest.mark.django_db


def _make_ping(traveler, *, when):
    return TravelerLocationPing.objects.create(
        traveler=traveler,
        latitude=5.34,
        longitude=-4.0,
        point=Point(-4.0, 5.34, srid=4326),
        accuracy_m=10.0,
        event_type=LocationEventType.DAILY_CHECKIN,
        source=LocationSource.PWA,
        captured_at=when,
        consent_version="v1",
    )


@pytest.fixture(autouse=True)
def _silence_channels(monkeypatch):
    # `trigger_alert` appelle broadcast_alert qui touche channels — on désactive.
    from apps.surveillance import services as surv_services
    monkeypatch.setattr(surv_services, "broadcast_alert", lambda *a, **k: None)


def test_compliance_no_protocol_is_ok(active_case):
    """Sans DiseaseFollowupProtocol → toujours True (rien à exiger)."""
    assert check_geolocation_compliance(active_case) is True


def test_compliance_inactive_case_is_ok(active_case, ebola_protocol):
    active_case.status = QuarantineStatus.COMPLETED
    active_case.save()
    assert check_geolocation_compliance(active_case) is True


def test_compliance_no_consent_triggers_alert(active_case, ebola_protocol):
    # Pas de consentement → alerte
    ok = check_geolocation_compliance(active_case)
    assert ok is False

    alerts = HealthAlert.objects.filter(code="followup_geolocation_missing")
    assert alerts.count() == 1
    assert alerts.first().metadata["reason"] == "consent_revoked"

    actions = FollowUpAction.objects.filter(
        followup_case=active_case,
        action_type=FollowUpActionType.ALERT_CREATED,
    )
    assert actions.count() == 1
    # Anti-spam : marqué
    active_case.refresh_from_db()
    assert active_case.geolocation_alert_raised_at is not None


def test_compliance_with_recent_ping_is_ok(active_case, ebola_protocol, traveler):
    record_consent(
        traveler=traveler, scope=ConsentScope.GEOLOCATION, granted=True, version="v1",
    )
    _make_ping(traveler, when=timezone.now() - timedelta(hours=2))

    ok = check_geolocation_compliance(active_case)
    assert ok is True
    assert HealthAlert.objects.filter(code="followup_geolocation_missing").count() == 0


def test_compliance_stale_ping_triggers_alert(active_case, ebola_protocol, traveler):
    record_consent(
        traveler=traveler, scope=ConsentScope.GEOLOCATION, granted=True, version="v1",
    )
    # ping trop ancien (48h, seuil=24h)
    _make_ping(traveler, when=timezone.now() - timedelta(hours=48))

    ok = check_geolocation_compliance(active_case)
    assert ok is False

    alerts = HealthAlert.objects.filter(code="followup_geolocation_missing")
    assert alerts.count() == 1
    assert alerts.first().metadata["reason"] == "no_recent_ping"


def test_compliance_antispam_one_per_24h(active_case, ebola_protocol):
    # Premier appel — alerte créée
    check_geolocation_compliance(active_case)
    assert HealthAlert.objects.filter(code="followup_geolocation_missing").count() == 1

    # Deuxième appel immédiat — pas de nouvelle alerte (anti-spam)
    check_geolocation_compliance(active_case)
    assert HealthAlert.objects.filter(code="followup_geolocation_missing").count() == 1

    # On simule le passage de 25h (au-delà de la fenêtre anti-spam)
    active_case.refresh_from_db()
    active_case.geolocation_alert_raised_at = timezone.now() - timedelta(hours=25)
    active_case.save(update_fields=["geolocation_alert_raised_at"])

    check_geolocation_compliance(active_case)
    assert HealthAlert.objects.filter(code="followup_geolocation_missing").count() == 2
