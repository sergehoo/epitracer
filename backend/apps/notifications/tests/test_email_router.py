"""Tests du routeur email — séparation stricte PUBLIC / INTERNAL.

Vérifie notamment :
    - Le mapping EmailType → SenderProfile est figé et exhaustif
    - Tout EmailType inconnu lève ValueError (sécurité défensive)
    - send_email_by_type force toujours le bon expéditeur
    - Les types PUBLIC n'utilisent jamais l'expéditeur INTERNAL et vice-versa
"""
import pytest
from unittest.mock import patch

from apps.notifications.email_models import (
    EmailType, PUBLIC_EMAIL_TYPES, INTERNAL_EMAIL_TYPES,
    SenderProfileCode, get_sender_profile_code_for_type,
)


# ---------------------------------------------------------------------------
# Mapping figé — règles métier
# ---------------------------------------------------------------------------

class TestEmailTypeMapping:
    """Le mapping EmailType → SenderProfile est figé en code."""

    def test_all_public_types_route_to_public(self):
        for et in PUBLIC_EMAIL_TYPES:
            assert get_sender_profile_code_for_type(et) == SenderProfileCode.PUBLIC

    def test_all_internal_types_route_to_internal(self):
        for et in INTERNAL_EMAIL_TYPES:
            assert get_sender_profile_code_for_type(et) == SenderProfileCode.INTERNAL

    def test_unknown_type_raises_value_error(self):
        with pytest.raises(ValueError, match="rattaché à aucun SenderProfile"):
            get_sender_profile_code_for_type("type_qui_nexiste_pas")

    def test_no_overlap_between_public_and_internal(self):
        """Aucun type ne peut être à la fois PUBLIC et INTERNAL."""
        overlap = PUBLIC_EMAIL_TYPES & INTERNAL_EMAIL_TYPES
        assert overlap == set(), f"Types ambigus : {overlap}"

    def test_all_email_types_are_categorized(self):
        """Tout membre d'EmailType DOIT être dans PUBLIC ou INTERNAL."""
        all_types = set(et.value for et in EmailType)
        categorized = (
            {et.value for et in PUBLIC_EMAIL_TYPES} |
            {et.value for et in INTERNAL_EMAIL_TYPES}
        )
        missing = all_types - categorized
        assert missing == set(), f"Types non catégorisés : {missing}"

    def test_traveler_types_never_use_internal_sender(self):
        """Sécurité : aucun email voyageur ne doit partir de inhp@…"""
        traveler_keywords = ["traveler", "followup", "pass_", "public_", "health_"]
        for et in EmailType:
            if any(kw in et.value for kw in traveler_keywords):
                code = get_sender_profile_code_for_type(et)
                assert code == SenderProfileCode.PUBLIC, (
                    f"{et.value} (voyageur) ne doit JAMAIS utiliser l'expéditeur INTERNAL"
                )

    def test_admin_types_never_use_public_sender(self):
        """Sécurité : aucun email admin ne doit partir de infos@destinationci.com"""
        admin_keywords = ["admin_", "staff_", "internal_", "mfa_", "system_", "user_invitation"]
        for et in EmailType:
            if any(kw in et.value for kw in admin_keywords):
                code = get_sender_profile_code_for_type(et)
                assert code == SenderProfileCode.INTERNAL, (
                    f"{et.value} (admin) ne doit JAMAIS utiliser l'expéditeur PUBLIC"
                )


# ---------------------------------------------------------------------------
# Service send_email_by_type — comportement nominal et erreurs
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_celery(monkeypatch):
    """Bypass Celery — on n'enqueue rien réellement."""
    monkeypatch.setattr(
        "apps.notifications.tasks_email.send_email_task.delay",
        lambda *a, **kw: None,
    )


@pytest.mark.django_db
class TestSendEmailByType:
    """Tests d'intégration : DB + dispatcher (sans envoi SMTP réel)."""

    def test_public_email_uses_public_sender(self, mock_celery):
        from apps.notifications.services.email_router import send_email_by_type
        from apps.notifications.email_models import EmailLog

        result = send_email_by_type(
            email_type=EmailType.TRAVELER_INFO,
            recipient="voyageur@example.com",
            subject="Test",
            body_html="<p>Test</p>",
        )
        assert result.ok is True
        log = EmailLog.objects.get(pk=result.log_id)
        assert log.sender_address == "infos@destinationci.com"

    def test_internal_email_uses_internal_sender(self, mock_celery):
        from apps.notifications.services.email_router import send_email_by_type
        from apps.notifications.email_models import EmailLog

        result = send_email_by_type(
            email_type=EmailType.ADMIN_ACCOUNT_CREATED,
            recipient="admin@example.com",
            subject="Test",
            body_html="<p>Test</p>",
        )
        assert result.ok is True
        log = EmailLog.objects.get(pk=result.log_id)
        assert log.sender_address == "inhp@veillesanitaire.com"

    def test_invalid_recipient_rejected(self, mock_celery):
        from apps.notifications.services.email_router import send_email_by_type
        result = send_email_by_type(
            email_type=EmailType.TRAVELER_INFO,
            recipient="pas-un-email",
            subject="x",
            body_html="<p>x</p>",
        )
        assert result.ok is False
        assert "invalide" in result.error.lower()

    def test_unknown_email_type_rejected(self, mock_celery):
        from apps.notifications.services.email_router import send_email_by_type
        result = send_email_by_type(
            email_type="le_type_inconnu",
            recipient="user@example.com",
            subject="x",
            body_html="<p>x</p>",
        )
        assert result.ok is False
        assert "inconnu" in result.error.lower()

    def test_missing_subject_and_body_rejected(self, mock_celery):
        from apps.notifications.services.email_router import send_email_by_type
        result = send_email_by_type(
            email_type=EmailType.TRAVELER_INFO,
            recipient="user@example.com",
        )
        assert result.ok is False

    def test_log_created_with_status_queued(self, mock_celery):
        from apps.notifications.services.email_router import send_email_by_type
        from apps.notifications.email_models import EmailLog, EmailStatus

        result = send_email_by_type(
            email_type=EmailType.HEALTH_NOTIFICATION,
            recipient="user@example.com",
            subject="Notif",
            body_html="<p>Body</p>",
        )
        log = EmailLog.objects.get(pk=result.log_id)
        assert log.status == EmailStatus.QUEUED
        assert log.email_type == "health_notification"
        assert log.recipient == "user@example.com"

    def test_masked_recipient_format(self, mock_celery):
        from apps.notifications.services.email_router import send_email_by_type
        from apps.notifications.email_models import EmailLog

        result = send_email_by_type(
            email_type=EmailType.PASS_CONFIRMATION,
            recipient="serge.ogah@kaydangroupe.com",
            subject="x",
            body_html="<p>x</p>",
        )
        log = EmailLog.objects.get(pk=result.log_id)
        masked = log.masked_recipient
        # Local part masquée : premier + étoiles + dernier, puis @ + domaine
        assert "*" in masked
        assert masked.endswith("@kaydangroupe.com")
        assert "serge.ogah" not in masked


# ---------------------------------------------------------------------------
# Template rendering avec SafeDict
# ---------------------------------------------------------------------------

class TestTemplateRendering:
    def test_render_substitutes_known_vars(self):
        from apps.notifications.services.email_router import _render
        result = _render("Bonjour {name}", {"name": "Aïssa"})
        assert result == "Bonjour Aïssa"

    def test_render_keeps_missing_vars_as_is(self):
        """Variable manquante → reste {var} brut, pas de crash."""
        from apps.notifications.services.email_router import _render
        result = _render("Bonjour {name}, ID {id}", {"name": "Aïssa"})
        assert result == "Bonjour Aïssa, ID {id}"

    def test_render_empty_template_returns_empty(self):
        from apps.notifications.services.email_router import _render
        assert _render("", {"x": 1}) == ""

    def test_render_no_placeholders_returns_unchanged(self):
        from apps.notifications.services.email_router import _render
        result = _render("Texte sans variable", {"x": "y"})
        assert result == "Texte sans variable"
