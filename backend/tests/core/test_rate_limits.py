"""Tests rate limit — chantier #213-3.

Vérifie que les scopes de throttle critiques sont configurés.
Ne couvre pas la trajectoire complète (request → 429) car en mode test
on désactive globalement les throttle classes (cf. settings/test.py) ;
on s'assure ici que les valeurs sont cohérentes côté settings, et que
les views portent bien le bon scope.
"""
from __future__ import annotations

from django.conf import settings


def test_throttle_scopes_present():
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    for scope in (
        "public_registration",
        "public_pass_consult",
        "mobile_otp_request",
        "mobile_login",
        "login",
        "password_reset",
        "mfa_resend",
    ):
        assert scope in rates, f"missing throttle scope: {scope}"


def test_public_registration_is_tight():
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    # Doit être 5/min ou plus strict
    assert rates["public_registration"].endswith("/min")
    value = int(rates["public_registration"].split("/")[0])
    assert value <= 10, "public_registration should be ≤10/min"


def test_mobile_otp_request_is_tight():
    rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
    assert rates["mobile_otp_request"].endswith("/min")
    value = int(rates["mobile_otp_request"].split("/")[0])
    assert value <= 5, "mobile_otp_request should be ≤5/min"


def test_public_register_view_uses_correct_scope():
    """La view publique enregistrement DOIT porter scope public_registration."""
    from apps.ebola.public_views import PublicTravelerRegisterView
    assert PublicTravelerRegisterView.throttle_scope == "public_registration"


def test_public_passport_upload_view_uses_correct_scope():
    from apps.ebola.public_views import PublicPassportUploadView
    assert PublicPassportUploadView.throttle_scope == "public_registration"


def test_voyageur_otp_request_uses_correct_scope():
    from apps.mobile_api.voyageur_auth import VoyageurRequestOtpView
    assert VoyageurRequestOtpView.throttle_scope == "mobile_otp_request"


def test_voyageur_otp_verify_uses_correct_scope():
    from apps.mobile_api.voyageur_auth import VoyageurVerifyOtpView
    assert VoyageurVerifyOtpView.throttle_scope == "mobile_login"
