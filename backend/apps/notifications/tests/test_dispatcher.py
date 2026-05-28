"""Tests du dispatcher — orchestration + sécurité métier.

Vérifie notamment :
    - Création de la Notification avec les bons champs
    - Routage automatique correct (+225 → orange_ci)
    - REFUS de force_provider="twilio" sur un numéro CI (politique nationale)
    - Anti-spam : message vide ou trop long rejeté
"""
import pytest
from unittest.mock import patch

from apps.notifications.models import (
    Channel, MessageType, Notification, NotificationStatus, Provider,
)
from apps.notifications.services.dispatcher import (
    enqueue_notification, send_manual_message,
)


@pytest.fixture
def mock_celery(monkeypatch):
    """Empêche Celery de tenter un vrai enqueue (utilise eager fallback)."""
    monkeypatch.setattr(
        "apps.notifications.tasks.send_notification_task.delay",
        lambda *a, **kw: None,
    )


@pytest.mark.django_db
class TestEnqueueNotification:
    def test_ci_number_routes_to_orange_ci(self, mock_celery):
        result = enqueue_notification(
            channel="sms",
            recipient="+2250700000000",
            body="Test message",
        )
        assert result.ok is True
        assert result.provider == Provider.ORANGE_CI
        notif = Notification.objects.get(pk=result.notification_id)
        assert notif.provider == Provider.ORANGE_CI
        assert notif.normalized_phone == "+2250700000000"

    def test_intl_number_routes_to_twilio(self, mock_celery):
        result = enqueue_notification(
            channel="sms",
            recipient="+33600000000",
            body="Test",
        )
        assert result.ok is True
        assert result.provider == Provider.TWILIO

    def test_invalid_phone_rejected(self, mock_celery):
        result = enqueue_notification(
            channel="sms",
            recipient="garbage",
            body="Test",
        )
        assert result.ok is False
        assert "Format" in result.error or "vide" in result.error.lower()

    def test_empty_body_rejected(self, mock_celery):
        result = enqueue_notification(
            channel="sms",
            recipient="+2250700000000",
            body="",
        )
        assert result.ok is False
        assert "vide" in result.error.lower()

    def test_body_too_long_rejected(self, mock_celery):
        long_body = "a" * 2000
        result = enqueue_notification(
            channel="sms",
            recipient="+2250700000000",
            body=long_body,
        )
        assert result.ok is False
        assert "trop long" in result.error.lower()

    def test_force_twilio_on_ci_number_refused(self, mock_celery):
        """POLITIQUE NATIONALE : impossible d'envoyer un SMS CI via Twilio."""
        result = enqueue_notification(
            channel="sms",
            recipient="+2250700000000",
            body="Test",
            force_provider="twilio",
        )
        assert result.ok is False
        assert "ivoirien" in result.error.lower() or "Twilio refusé" in result.error

    def test_force_provider_intl_ok(self, mock_celery):
        """OK de forcer un provider compatible pour un n° international."""
        # +33... ne peut PAS aller chez orange_ci mais peut aller chez meta_whatsapp
        result = enqueue_notification(
            channel="sms",
            recipient="+33600000000",
            body="Test",
            force_provider="twilio",  # déjà le défaut, no-op
        )
        assert result.ok is True
        assert result.provider == "twilio"

    def test_invalid_channel_rejected(self, mock_celery):
        result = enqueue_notification(
            channel="carrier_pigeon",
            recipient="+2250700000000",
            body="Test",
        )
        assert result.ok is False
        assert "non support" in result.error.lower()

    def test_notification_persisted_with_metadata(self, mock_celery):
        result = enqueue_notification(
            channel="sms",
            recipient="+2250700000000",
            body="Test",
        )
        notif = Notification.objects.get(pk=result.notification_id)
        assert notif.metadata["routing"]["country_code"] == "CI"
        assert notif.metadata["routing"]["is_ivoirian"] is True
        assert notif.status == NotificationStatus.QUEUED

    def test_masked_recipient_property(self, mock_celery):
        result = enqueue_notification(
            channel="sms",
            recipient="+2250700000000",
            body="Test",
        )
        notif = Notification.objects.get(pk=result.notification_id)
        masked = notif.masked_recipient
        assert "****" in masked
        assert masked.startswith("+22507")
        assert masked.endswith("0000")


@pytest.mark.django_db
class TestSendManualMessage:
    def test_requires_authenticated_user(self, mock_celery):
        from django.contrib.auth.models import AnonymousUser
        result = send_manual_message(
            traveler=None,
            recipient="+2250700000000",
            body="Test",
            sent_by=AnonymousUser(),
        )
        assert result.ok is False
        assert "authentifié" in result.error.lower()

    def test_message_type_is_manual(self, mock_celery, django_user_model):
        user = django_user_model.objects.create_user(
            username="agent1", email="agent1@example.com", password="x",
        )
        result = send_manual_message(
            traveler=None,
            recipient="+2250700000000",
            body="Hello",
            sent_by=user,
        )
        assert result.ok is True
        notif = Notification.objects.get(pk=result.notification_id)
        assert notif.message_type == MessageType.MANUAL_MESSAGE
        assert notif.sent_by_id == user.id
