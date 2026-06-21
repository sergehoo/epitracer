"""Tests du job Celery `companion.send_daily_checkin_reminders`.

On vérifie surtout les **règles métier** :
  - un voyageur en suivi actif AVEC consentement push reçoit bien une notif ;
  - un voyageur dont la quarantaine est `COMPLETED` ne reçoit RIEN ;
  - un voyageur sans consentement est skip avec le bon motif ;
  - le payload mobile inclut bien `type=daily_checkin` + `traveler_id`.

Les canaux d'envoi (FCM, VAPID, SMS) sont entièrement mockés — on ne sort
pas du process Python ni du test DB.
"""
from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from apps.companion import tasks as companion_tasks
from apps.companion.models import ConsentScope
from apps.companion.services import record_consent


pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Fixtures locales
# ---------------------------------------------------------------------------


@pytest.fixture
def active_quarantine(db, traveler, ebola_disease):
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


@pytest.fixture
def closed_quarantine(db, traveler, ebola_disease):
    """Quarantaine TERMINÉE — voyageur dont le suivi est `COMPLETED`."""
    from apps.quarantine.models import QuarantineRecord, QuarantineStatus

    return QuarantineRecord.objects.create(
        traveler=traveler,
        disease=ebola_disease,
        started_on=date.today() - timedelta(days=25),
        expected_end_on=date.today() - timedelta(days=4),
        actual_end_on=date.today() - timedelta(days=4),
        status=QuarantineStatus.COMPLETED,
        address="Cocody",
    )


@pytest.fixture
def consent_push(db, traveler):
    """Le voyageur consent au scope `push`."""
    return record_consent(
        traveler=traveler, scope=ConsentScope.PUSH_NOTIFICATIONS, granted=True,
        version="v1.0",
    )


@pytest.fixture(autouse=True)
def _mute_external(monkeypatch):
    """Mocke tous les chemins de sortie réseau (FCM legacy, VAPID, SMS)."""
    # FCM legacy direct → no-op success
    monkeypatch.setattr(
        companion_tasks, "_send_fcm_with_data",
        lambda token, title, body, data: True,
    )
    # push_notify (VAPID + fallback SMS) → no-op stats
    monkeypatch.setattr(
        companion_tasks, "push_notify",
        MagicMock(return_value={"sent": 0, "failed": 0, "gone": 0,
                                "sms_sent": 0, "whatsapp_sent": 0}),
    )


# ---------------------------------------------------------------------------
# Cas nominal — voyageur actif + consentement → notification envoyée
# ---------------------------------------------------------------------------


def test_reminder_sent_to_active_traveler_with_consent(
    traveler, active_quarantine, consent_push,
):
    """Un voyageur en suivi actif avec consentement reçoit bien le rappel.

    On vérifie via le `push_notify` mock que :
      - il a été appelé exactement 1 fois ;
      - le titre commence par "Bonjour <Prénom>" ;
      - les `extra` data contiennent bien `type=daily_checkin` et le `day`
        attendu (3 dans cette fixture).
    """
    result = companion_tasks.send_daily_checkin_reminders.run()
    assert result["travelers"] == 1
    assert result["skipped_no_consent"] == 0

    # push_notify est notre principal point d'observation
    companion_tasks.push_notify.assert_called_once()
    kwargs = companion_tasks.push_notify.call_args.kwargs

    # Personnalisation du titre — prénom de la fixture conftest est "Aïcha"
    assert kwargs["title"].startswith("Bonjour")
    assert "Aïcha" in kwargs["title"] or "Aicha" in kwargs["title"]

    # Body parle bien de la surveillance Jour X/21
    assert "Jour 3" in kwargs["body"]
    assert "21" in kwargs["body"]
    assert "INHP" in kwargs["body"]

    # Payload mobile pour le deep-link Flutter
    extra = kwargs["extra"]
    assert extra["type"] == "daily_checkin"
    assert extra["traveler_id"] == traveler.public_id
    assert extra["day"] == 3
    assert extra["total"] == 21

    # URL web pour les abonnés VAPID PWA
    assert kwargs["url"] == f"/voyageur/suivi?id={traveler.public_id}"
    assert kwargs["notification_type"] == "daily_checkin"
    assert kwargs["tag"] == "daily-checkin"


def test_reminder_skipped_without_consent(traveler, active_quarantine):
    """Sans consentement push, AUCUNE notification n'est envoyée."""
    result = companion_tasks.send_daily_checkin_reminders.run()
    assert result["travelers"] == 1
    assert result["skipped_no_consent"] == 1
    assert result["fcm_sent"] == 0
    companion_tasks.push_notify.assert_not_called()


def test_no_reminder_for_completed_followup(
    traveler, closed_quarantine, consent_push,
):
    """Un voyageur dont la quarantaine est `COMPLETED` ne doit RIEN recevoir.

    Le job filtre par `status in [ACTIVE, EXTENDED]` — `COMPLETED` est
    donc exclu d'office (avant même la vérif de consentement).
    """
    result = companion_tasks.send_daily_checkin_reminders.run()
    assert result["travelers"] == 0
    assert result["skipped_no_consent"] == 0
    companion_tasks.push_notify.assert_not_called()


def test_reminder_skipped_when_day_overflow(
    traveler, ebola_disease, consent_push,
):
    """Si on est au-delà du jour 21, on n'envoie plus de rappel.

    Cas limite : un voyageur dont la quarantaine est encore "active" en DB
    (n'a pas été clôturée par le job 18:00 ce jour-là) mais qui est déjà
    sorti de la fenêtre 21j. Le job doit le détecter et passer son tour.
    """
    from apps.quarantine.models import QuarantineRecord, QuarantineStatus

    QuarantineRecord.objects.create(
        traveler=traveler,
        disease=ebola_disease,
        started_on=date.today() - timedelta(days=25),
        expected_end_on=date.today() - timedelta(days=4),
        status=QuarantineStatus.ACTIVE,  # pas encore basculé en COMPLETED
        address="Cocody",
    )
    result = companion_tasks.send_daily_checkin_reminders.run()
    assert result["travelers"] == 1
    assert result["skipped_day_overflow"] == 1
    companion_tasks.push_notify.assert_not_called()


# ---------------------------------------------------------------------------
# Sécurité — pas de PII dans les logs
# ---------------------------------------------------------------------------


def test_phone_is_masked_in_logs():
    """`_mask_phone` doit masquer les chiffres centraux du numéro."""
    masked = companion_tasks._mask_phone("+2250708090911")
    assert "0708" not in masked
    assert "0911" not in masked  # même 4 derniers chiffres masqués
    assert masked.startswith("+2250")
    assert "*" in masked
    # Cas null / vide
    assert companion_tasks._mask_phone(None) == ""
    assert companion_tasks._mask_phone("") == ""


# ---------------------------------------------------------------------------
# FCM mobile — délégation vers MobileDevice
# ---------------------------------------------------------------------------


def test_fcm_sent_when_mobile_device_registered(
    db, traveler, active_quarantine, consent_push, django_user_model,
):
    """Si le voyageur a un User app mobile + MobileDevice actif, FCM est
    appelé. On vérifie ici que `_send_fcm_with_data` est invoqué avec le
    bon payload `data` (deep-link).
    """
    from apps.mobile_api.models import MobileDevice

    # User app mobile lié au voyageur par email (convention actuelle)
    user = django_user_model.objects.create_user(
        email=traveler.email, username=traveler.email,
        password="X3rT9!aBcD",
    )
    MobileDevice.objects.create(
        user=user, fcm_token="fake_fcm_token_xyz",
        platform="android", is_active=True,
    )

    called = {}

    def fake_send(token, title, body, data):
        called["token"] = token
        called["title"] = title
        called["data"] = data
        return True

    with patch.object(companion_tasks, "_send_fcm_with_data", side_effect=fake_send):
        result = companion_tasks.send_daily_checkin_reminders.run()

    assert result["fcm_sent"] == 1
    assert called["token"] == "fake_fcm_token_xyz"
    assert called["data"]["type"] == "daily_checkin"
    assert called["data"]["traveler_id"] == traveler.public_id
    assert called["data"]["day"] == "3"  # FCM exige des strings
