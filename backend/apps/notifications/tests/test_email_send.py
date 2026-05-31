"""Tests d'envoi email avec mock SMTP — vérifie status, retry, log update."""
import pytest
from unittest.mock import patch, MagicMock

from apps.notifications.email_models import (
    EmailLog, EmailStatus, EmailType,
)


@pytest.fixture
def mock_celery(monkeypatch):
    monkeypatch.setattr(
        "apps.notifications.tasks_email.send_email_task.delay",
        lambda *a, **kw: None,
    )


@pytest.mark.django_db
class TestExecuteEmailSend:
    """Tests du _execute_email_send (l'étape SMTP réelle)."""

    def _create_queued_log(self, email_type=EmailType.HEALTH_NOTIFICATION):
        """Helper : crée un EmailLog en attente sans déclencher Celery."""
        from apps.notifications.email_models import SenderProfile
        # Le sender_address est récupéré du profil PUBLIC (seedé par migration)
        sender_addr = SenderProfile.objects.get(code="public").from_address
        return EmailLog.objects.create(
            recipient="user@example.com",
            email_type=email_type,
            sender_address=sender_addr,
            subject="Test",
            body_html="<p>Hello</p>",
            body_text="Hello",
            status=EmailStatus.QUEUED,
        )

    @patch("apps.notifications.services.email_router._build_connection")
    def test_successful_send_updates_status_to_sent(self, mock_connection):
        from apps.notifications.services.email_router import _execute_email_send

        # Mock : EmailMultiAlternatives.send() renvoie 1 (succès)
        mock_msg_send = MagicMock(return_value=1)
        with patch(
            "apps.notifications.services.email_router.EmailMultiAlternatives"
        ) as MockEmail:
            instance = MockEmail.return_value
            instance.send = mock_msg_send

            log = self._create_queued_log()
            ok = _execute_email_send(log)

        assert ok is True
        log.refresh_from_db()
        assert log.status == EmailStatus.SENT
        assert log.sent_at is not None
        assert log.error_message == ""
        assert log.retry_count == 1

    @patch("apps.notifications.services.email_router._build_connection")
    def test_smtp_error_sets_status_failed(self, mock_connection):
        from apps.notifications.services.email_router import _execute_email_send

        with patch(
            "apps.notifications.services.email_router.EmailMultiAlternatives"
        ) as MockEmail:
            instance = MockEmail.return_value
            instance.send.side_effect = Exception("SMTP timeout")

            log = self._create_queued_log()
            ok = _execute_email_send(log)

        assert ok is False
        log.refresh_from_db()
        assert log.status == EmailStatus.FAILED
        assert "SMTP timeout" in log.error_message
        assert log.failed_at is not None
        assert log.retry_count == 1

    @patch("apps.notifications.services.email_router._build_connection")
    def test_send_returns_zero_sets_failed(self, mock_connection):
        """send() renvoie 0 → considéré comme échec."""
        from apps.notifications.services.email_router import _execute_email_send

        with patch(
            "apps.notifications.services.email_router.EmailMultiAlternatives"
        ) as MockEmail:
            instance = MockEmail.return_value
            instance.send.return_value = 0

            log = self._create_queued_log()
            ok = _execute_email_send(log)

        assert ok is False
        log.refresh_from_db()
        assert log.status == EmailStatus.FAILED

    @patch("apps.notifications.services.email_router._build_connection")
    def test_internal_email_uses_internal_profile(self, mock_connection):
        """Vérifie qu'un email INTERNAL provoque un build_connection('internal')."""
        from apps.notifications.services.email_router import _execute_email_send
        from apps.notifications.email_models import SenderProfile

        sender_addr = SenderProfile.objects.get(code="internal").from_address
        log = EmailLog.objects.create(
            recipient="admin@example.com",
            email_type=EmailType.ADMIN_ACCOUNT_CREATED,
            sender_address=sender_addr,
            subject="Test",
            body_html="<p>x</p>",
            body_text="x",
            status=EmailStatus.QUEUED,
        )

        with patch(
            "apps.notifications.services.email_router.EmailMultiAlternatives"
        ) as MockEmail:
            MockEmail.return_value.send = MagicMock(return_value=1)
            _execute_email_send(log)

        # Vérification : _build_connection appelé avec 'internal'
        mock_connection.assert_called_once_with("internal")


@pytest.mark.django_db
class TestBulkRetry:
    @patch("apps.notifications.tasks_email.send_email_task.delay")
    def test_retry_failed_emails_requeues_eligible(self, mock_delay):
        from apps.notifications.tasks_email import retry_failed_emails
        from apps.notifications.email_models import SenderProfile
        from django.utils import timezone

        sender_addr = SenderProfile.objects.get(code="public").from_address
        # 2 FAILED retry-able, 1 FAILED épuisé (retry_count = max_retries)
        for _ in range(2):
            EmailLog.objects.create(
                recipient="u@ex.com", email_type="health_notification",
                sender_address=sender_addr, subject="s", body_html="<p>x</p>",
                body_text="x", status=EmailStatus.FAILED,
                failed_at=timezone.now(), retry_count=0, max_retries=3,
            )
        EmailLog.objects.create(
            recipient="u@ex.com", email_type="health_notification",
            sender_address=sender_addr, subject="s", body_html="<p>x</p>",
            body_text="x", status=EmailStatus.FAILED,
            failed_at=timezone.now(), retry_count=3, max_retries=3,
        )

        result = retry_failed_emails()
        assert result["requeued"] == 2
        assert mock_delay.call_count == 2
