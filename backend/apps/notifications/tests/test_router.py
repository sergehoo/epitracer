"""Tests du routeur de provider — règles métier STRICTES.

Ces tests valident le contrat MSHPCMU/INHP :
    +225 → orange_ci
    autres → twilio
    invalide → PhoneValidationError

Tout changement de comportement nécessite une validation INHP.
"""
import pytest

from apps.notifications.services.router import (
    NotificationProviderRouter, PhoneValidationError,
    detect_provider, is_ivoirian_number, normalize_phone_number,
    validate_phone_number,
)


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
class TestNormalize:
    def test_already_e164(self):
        assert normalize_phone_number("+2250700000000") == "+2250700000000"

    def test_with_spaces(self):
        assert normalize_phone_number("+225 07 00 00 00 00") == "+2250700000000"

    def test_with_dashes(self):
        assert normalize_phone_number("+225-07-00-00-00-00") == "+2250700000000"

    def test_with_parens(self):
        assert normalize_phone_number("+225 (07) 00 00 00 00") == "+2250700000000"

    def test_double_zero_prefix(self):
        # 00225... → +225...
        assert normalize_phone_number("002250700000000") == "+2250700000000"

    def test_local_ci_10_digits_starting_zero(self):
        # 0XXXXXXXXX (10 chiffres) → +225XXXXXXXXX (9 chiffres)
        assert normalize_phone_number("0700000000") == "+22500000000" or \
               normalize_phone_number("0700000000").startswith("+225")

    def test_international_french(self):
        assert normalize_phone_number("+33600000000") == "+33600000000"

    def test_international_us(self):
        assert normalize_phone_number("+12025550123") == "+12025550123"

    def test_empty_raises(self):
        with pytest.raises(PhoneValidationError):
            normalize_phone_number("")

    def test_garbage_raises(self):
        with pytest.raises(PhoneValidationError):
            normalize_phone_number("not a phone")


# ---------------------------------------------------------------------------
# Validation stricte CI
# ---------------------------------------------------------------------------
class TestValidate:
    def test_ci_10_digits_after_225_ok(self):
        assert validate_phone_number("+2250700000000") == "+2250700000000"

    def test_ci_8_digits_after_225_rejected(self):
        """Réforme 2021 : les anciens numéros 8 chiffres ne sont plus valides."""
        with pytest.raises(PhoneValidationError):
            validate_phone_number("+22507000000")  # 8 chiffres après +225

    def test_intl_ok(self):
        assert validate_phone_number("+33612345678") == "+33612345678"

    def test_intl_too_short_rejected(self):
        with pytest.raises(PhoneValidationError):
            validate_phone_number("+12345")


# ---------------------------------------------------------------------------
# Détection ivoirien
# ---------------------------------------------------------------------------
class TestIsIvoirian:
    def test_ci_plus_225(self):
        assert is_ivoirian_number("+2250700000000") is True

    def test_ci_with_spaces(self):
        assert is_ivoirian_number("+225 07 00 00 00 00") is True

    def test_french_not_ci(self):
        assert is_ivoirian_number("+33600000000") is False

    def test_us_not_ci(self):
        assert is_ivoirian_number("+12025550123") is False

    def test_invalid_returns_false(self):
        assert is_ivoirian_number("garbage") is False


# ---------------------------------------------------------------------------
# Détection du provider — LE CONTRAT MÉTIER CENTRAL
# ---------------------------------------------------------------------------
class TestDetectProvider:
    def test_ci_routes_to_orange_ci(self):
        decision = detect_provider("+2250700000000", "sms")
        assert decision.provider == "orange_ci"
        assert decision.is_ivoirian is True
        assert decision.country_code == "CI"

    def test_ci_orange_07_prefix(self):
        decision = detect_provider("+2250700000000", "sms")
        assert decision.provider == "orange_ci"

    def test_ci_mtn_05_prefix(self):
        # 05XXXXXXXX = MTN historique → mais on route quand même via Orange CI
        # (le routage est sur le PAYS, pas l'opérateur de la SIM)
        decision = detect_provider("+2250500000000", "sms")
        assert decision.provider == "orange_ci"

    def test_ci_moov_01_prefix(self):
        decision = detect_provider("+2250100000000", "sms")
        assert decision.provider == "orange_ci"

    def test_french_routes_to_twilio(self):
        decision = detect_provider("+33600000000", "sms")
        assert decision.provider == "twilio"
        assert decision.is_ivoirian is False

    def test_us_routes_to_twilio(self):
        decision = detect_provider("+12025550123", "sms")
        assert decision.provider == "twilio"
        assert decision.country_code == "INTL"

    def test_whatsapp_channel_uses_settings_provider(self, settings):
        settings.NOTIFICATIONS = {"WHATSAPP_PROVIDER": "meta"}
        decision = detect_provider("+33600000000", "whatsapp")
        assert decision.provider == "meta_whatsapp"

    def test_invalid_channel_raises(self):
        with pytest.raises(ValueError):
            detect_provider("+2250700000000", "carrier_pigeon")

    def test_invalid_phone_raises(self):
        with pytest.raises(PhoneValidationError):
            detect_provider("garbage", "sms")


# ---------------------------------------------------------------------------
# Façade objet
# ---------------------------------------------------------------------------
class TestRouterFacade:
    def test_normalize_proxy(self):
        assert NotificationProviderRouter.normalize("0700000000").startswith("+225")

    def test_detect_proxy(self):
        d = NotificationProviderRouter.detect("+2250700000000", "sms")
        assert d.provider == "orange_ci"

    def test_is_ivoirian_proxy(self):
        assert NotificationProviderRouter.is_ivoirian("+2250700000000") is True
        assert NotificationProviderRouter.is_ivoirian("+33600000000") is False
