"""Tests des tokens de reset password — hash SHA-256, expiration, usage unique."""
import hashlib
import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone


User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="agent.test", email="agent.test@example.com",
        password="initial_pwd_123",
    )


@pytest.mark.django_db
class TestPasswordResetToken:
    """Vérifie sécurité : hash, expiration, usage unique, IP/UA tracé."""

    def test_token_generation_returns_raw_and_hash_differ(self, user):
        from apps.notifications.services.email_router import generate_password_reset_token

        raw, obj = generate_password_reset_token(user)
        assert raw != obj.token_hash, "Le token clair ne doit JAMAIS être stocké"
        assert len(raw) >= 32, "Token doit être suffisamment long (>=256 bits d'entropie)"
        # Vérifie que c'est bien un SHA-256 du raw
        expected_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        assert obj.token_hash == expected_hash

    def test_token_is_valid_immediately(self, user):
        from apps.notifications.services.email_router import generate_password_reset_token

        _, obj = generate_password_reset_token(user)
        assert obj.is_valid is True
        assert obj.used_at is None

    def test_consume_returns_user_and_marks_used(self, user):
        from apps.notifications.services.email_router import (
            generate_password_reset_token, consume_password_reset_token,
        )

        raw, obj = generate_password_reset_token(user)
        consumed_user = consume_password_reset_token(raw)
        assert consumed_user == user
        obj.refresh_from_db()
        assert obj.used_at is not None
        assert obj.is_valid is False, "Token utilisé doit devenir invalide"

    def test_consume_twice_fails_second_time(self, user):
        """Token à usage unique."""
        from apps.notifications.services.email_router import (
            generate_password_reset_token, consume_password_reset_token,
        )

        raw, _ = generate_password_reset_token(user)
        first = consume_password_reset_token(raw)
        second = consume_password_reset_token(raw)
        assert first == user
        assert second is None, "Deuxième usage doit échouer"

    def test_expired_token_is_invalid(self, user):
        from apps.notifications.email_models import PasswordResetToken

        # Force expiration en passé
        obj = PasswordResetToken.objects.create(
            user=user,
            token_hash="fake_hash_for_test",
            expires_at=timezone.now() - timedelta(hours=1),
        )
        assert obj.is_valid is False

    def test_consume_unknown_token_returns_none(self, user):
        from apps.notifications.services.email_router import consume_password_reset_token
        assert consume_password_reset_token("token-qui-nexiste-pas") is None

    def test_used_token_cannot_be_consumed(self, user):
        from apps.notifications.services.email_router import (
            generate_password_reset_token, consume_password_reset_token,
        )

        raw, obj = generate_password_reset_token(user)
        obj.used_at = timezone.now()
        obj.save()
        assert consume_password_reset_token(raw) is None

    def test_token_records_request_metadata(self, user):
        """IP + User-Agent sont tracés pour audit."""
        from apps.notifications.services.email_router import generate_password_reset_token

        class FakeRequest:
            META = {
                "REMOTE_ADDR": "192.168.1.42",
                "HTTP_USER_AGENT": "Mozilla/5.0 TestSuite",
            }

        _, obj = generate_password_reset_token(user, request=FakeRequest())
        assert obj.ip_address == "192.168.1.42"
        assert "TestSuite" in obj.user_agent

    def test_xff_header_extracted_correctly(self, user):
        """Si X-Forwarded-For, prend le premier IP (client réel derrière proxy)."""
        from apps.notifications.services.email_router import generate_password_reset_token

        class FakeRequest:
            META = {
                "HTTP_X_FORWARDED_FOR": "203.0.113.5, 10.0.0.1",
                "REMOTE_ADDR": "10.0.0.1",
                "HTTP_USER_AGENT": "ua",
            }

        _, obj = generate_password_reset_token(user, request=FakeRequest())
        assert obj.ip_address == "203.0.113.5"
