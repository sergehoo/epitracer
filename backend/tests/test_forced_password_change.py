"""Parcours création → activation → login → changement obligatoire → dashboard.

Non-régression de la boucle « Changement de mot de passe obligatoire » : le
changement réussi doit lever durablement `must_change_password`, renvoyer une
session neuve et ne plus jamais renvoyer l'utilisateur vers le changement.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import RoleCode

LOGIN = "/api/v1/auth/login/"
ME = "/api/v1/auth/me/"
CHANGE = "/api/v1/auth/change-password/"
REFRESH = "/api/v1/auth/refresh/"
USERS = "/api/v1/auth/users/"
NEW_PASSWORD = "Nouveau-Mot2Passe!Solide"


@pytest.fixture(autouse=True)
def _no_outgoing_email(monkeypatch):
    """Les e-mails d'activation et de réinitialisation ne sont pas l'objet du test."""
    from apps.notifications import tasks_email

    monkeypatch.setattr(tasks_email.send_admin_account_created_email, "delay", lambda *a, **k: None)
    monkeypatch.setattr(tasks_email.send_password_reset_email, "delay", lambda *a, **k: None)


@pytest.fixture
def admin_api(superadmin):
    client = APIClient()
    client.force_authenticate(superadmin)
    return client


@pytest.fixture
def otp_codes(monkeypatch):
    """Capture les codes MFA envoyés par e-mail au lieu de les envoyer."""
    from apps.accounts.services import email_otp

    codes: list[str] = []

    def fake_send(user, *, request=None, sync=True):
        code, obj = email_otp.generate_otp_for_user(user, request=request)
        codes.append(code)
        return email_otp.OtpResult(ok=True, code_id=obj.id)

    monkeypatch.setattr(email_otp, "send_otp_email", fake_send)
    return codes


def _create_agent(admin_api, email="agent@example.ci", **extra) -> str:
    """Création par l'administrateur : mot de passe temporaire + changement imposé."""
    resp = admin_api.post(USERS, {
        "email": email, "first_name": "Awa", "last_name": "KONE",
        "role_codes": [RoleCode.NATIONAL_ADMIN], **extra,
    }, format="json")
    assert resp.status_code == 201, resp.data
    return resp.data["temporary_password"]


def _login(email, password, **extra):
    return APIClient().post(LOGIN, {"email": email, "password": password, **extra}, format="json")


def _bearer(access: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


def _change(access, current, new=NEW_PASSWORD):
    return _bearer(access).post(
        CHANGE, {"current_password": current, "new_password": new}, format="json",
    )


def _user(email):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.get(email=email)


@pytest.mark.django_db
class TestForcedPasswordChange:
    def test_first_login_with_temporary_password_requires_change(self, admin_api):
        temporary = _create_agent(admin_api)

        resp = _login("agent@example.ci", temporary)

        assert resp.status_code == 200, resp.data
        assert resp.data["must_change_password"] is True
        assert _bearer(resp.data["access"]).get(ME).data["must_change_password"] is True

    def test_successful_change_lifts_obligation_and_opens_dashboard(self, admin_api):
        temporary = _create_agent(admin_api)
        access = _login("agent@example.ci", temporary).data["access"]

        resp = _change(access, temporary)

        assert resp.status_code == 200, resp.data
        assert resp.data["must_change_password"] is False
        # Session renouvelée : le client va directement au dashboard.
        me = _bearer(resp.data["access"]).get(ME)
        assert me.status_code == 200
        assert me.data["must_change_password"] is False
        user = _user("agent@example.ci")
        assert user.must_change_password is False
        assert user.last_password_change is not None
        assert user.check_password(NEW_PASSWORD)

    def test_page_refresh_after_change_does_not_loop(self, admin_api):
        """F5 après changement : nouvelle session stable ; l'ancien jeton est révoqué (401)."""
        temporary = _create_agent(admin_api)
        old_access = _login("agent@example.ci", temporary).data["access"]
        new_access = _change(old_access, temporary).data["access"]

        for _ in range(3):
            assert _bearer(new_access).get(ME).data["must_change_password"] is False
        assert _bearer(old_access).get(ME).status_code == 401

    def test_logout_then_login_with_new_password_reaches_dashboard(self, admin_api):
        temporary = _create_agent(admin_api)
        _change(_login("agent@example.ci", temporary).data["access"], temporary)

        again = _login("agent@example.ci", NEW_PASSWORD)

        assert again.status_code == 200, again.data
        assert again.data["must_change_password"] is False

    def test_old_password_is_refused(self, admin_api):
        temporary = _create_agent(admin_api)
        _change(_login("agent@example.ci", temporary).data["access"], temporary)

        resp = _login("agent@example.ci", temporary)

        assert resp.status_code in (400, 401)
        assert "access" not in resp.data

    def test_previous_sessions_are_revoked(self, admin_api):
        temporary = _create_agent(admin_api)
        first = _login("agent@example.ci", temporary).data
        changed = _change(first["access"], temporary).data

        def refresh(token):
            return APIClient().post(REFRESH, {"refresh": token}, format="json").status_code

        assert refresh(first["refresh"]) == 401
        assert refresh(changed["refresh"]) == 200


@pytest.mark.django_db
class TestInvalidOrInterruptedChange:
    @pytest.mark.parametrize("current, new", [
        ("mauvais-mot-de-passe", NEW_PASSWORD),   # mot de passe actuel faux
        (None, "1234"),                            # nouveau mot de passe refusé par la politique
        (None, None),                              # nouveau = actuel (temporaire réutilisé)
    ])
    def test_rejected_change_keeps_obligation(self, admin_api, current, new):
        temporary = _create_agent(admin_api)
        access = _login("agent@example.ci", temporary).data["access"]

        resp = _change(access, current or temporary, new or temporary)

        assert resp.status_code == 400, resp.data
        user = _user("agent@example.ci")
        assert user.must_change_password is True
        assert user.check_password(temporary)
        assert _login("agent@example.ci", temporary).data["must_change_password"] is True

    def test_failure_during_save_rolls_back(self, admin_api, monkeypatch):
        from apps.accounts import views

        temporary = _create_agent(admin_api)
        access = _login("agent@example.ci", temporary).data["access"]

        def boom(user):
            raise RuntimeError("coupure en cours d'écriture")

        monkeypatch.setattr(views, "_revoke_refresh_tokens", boom)
        resp = _change(access, temporary)

        assert resp.status_code == 500
        user = _user("agent@example.ci")
        assert user.must_change_password is True
        assert user.check_password(temporary)

    def test_abandoned_change_is_required_again_at_next_login(self, admin_api):
        temporary = _create_agent(admin_api)
        _login("agent@example.ci", temporary)  # puis « Annuler et se déconnecter »

        assert _login("agent@example.ci", temporary).data["must_change_password"] is True

    def test_change_requires_authentication(self):
        resp = APIClient().post(
            CHANGE, {"current_password": "x", "new_password": NEW_PASSWORD}, format="json",
        )
        assert resp.status_code == 401


@pytest.mark.django_db
def test_admin_reset_imposes_a_new_change(admin_api):
    temporary = _create_agent(admin_api)
    _change(_login("agent@example.ci", temporary).data["access"], temporary)
    user = _user("agent@example.ci")

    reset = admin_api.post(f"{USERS}{user.pk}/reset_password/")
    assert reset.status_code == 200, reset.data
    first = _login("agent@example.ci", reset.data["temporary_password"])
    assert first.data["must_change_password"] is True

    other = "Encore-Un2Autre!Secret"
    changed = _change(first.data["access"], reset.data["temporary_password"], other)
    assert changed.status_code == 200, changed.data
    assert _login("agent@example.ci", other).data["must_change_password"] is False


@pytest.mark.django_db
def test_mfa_activation_then_forced_change_keeps_mfa(admin_api, otp_codes):
    temporary = _create_agent(admin_api, mfa_enforced=True)

    step1 = _login("agent@example.ci", temporary)
    assert step1.status_code == 400
    assert "access" not in step1.data
    step2 = _login("agent@example.ci", temporary, mfa_code=otp_codes[-1])
    assert step2.status_code == 200, step2.data
    assert step2.data["must_change_password"] is True

    changed = _change(step2.data["access"], temporary)
    assert changed.status_code == 200, changed.data
    assert _bearer(changed.data["access"]).get(ME).data["must_change_password"] is False

    # Reconnexion : la MFA reste exigée, puis accès direct au dashboard.
    assert "access" not in _login("agent@example.ci", NEW_PASSWORD).data
    final = _login("agent@example.ci", NEW_PASSWORD, mfa_code=otp_codes[-1])
    assert final.status_code == 200, final.data
    assert final.data["must_change_password"] is False
    assert _user("agent@example.ci").mfa_enabled is True


# ===========================================================================
# Contrôle serveur : API bloquées tant que le changement est imposé,
# anciens JWT révoqués après changement (version de session).
# ===========================================================================
PROTECTED = USERS  # API d'administration autorisée par le rôle de l'agent (RBAC)
PUBLIC = "/api/v1/ebola/public/pass/INEXISTANT/"


def _code(resp) -> str:
    import json

    return json.dumps(resp.data, ensure_ascii=False)


@pytest.mark.django_db
class TestServerSideEnforcement:
    def test_protected_api_blocked_before_change(self, admin_api):
        temporary = _create_agent(admin_api)
        access = _login("agent@example.ci", temporary).data["access"]

        resp = _bearer(access).get(PROTECTED)

        assert resp.status_code == 403
        assert "password_change_required" in _code(resp)

    def test_session_mfa_and_public_endpoints_stay_available(self, admin_api):
        temporary = _create_agent(admin_api)
        api = _bearer(_login("agent@example.ci", temporary).data["access"])

        assert api.get(ME).status_code == 200
        assert api.post("/api/v1/auth/mfa/setup/").status_code == 200
        assert api.get(PUBLIC).status_code == 404  # API publique : pas de blocage

    def test_access_granted_after_change(self, admin_api):
        temporary = _create_agent(admin_api)
        changed = _change(_login("agent@example.ci", temporary).data["access"], temporary)

        assert _bearer(changed.data["access"]).get(PROTECTED).status_code == 200

    def test_old_jwt_refused_new_session_valid(self, admin_api):
        temporary = _create_agent(admin_api)
        first = _login("agent@example.ci", temporary).data
        changed = _change(first["access"], temporary).data

        assert _bearer(first["access"]).get(ME).status_code == 401
        assert _bearer(first["access"]).post(
            CHANGE, {"current_password": NEW_PASSWORD, "new_password": "Autre-Essai3!Secret"},
            format="json",
        ).status_code == 401
        assert _bearer(changed["access"]).get(PROTECTED).status_code == 200
        renewed = APIClient().post(REFRESH, {"refresh": changed["refresh"]}, format="json")
        assert _bearer(renewed.data["access"]).get(PROTECTED).status_code == 200

    def test_admin_reset_revokes_existing_jwt(self, admin_api):
        temporary = _create_agent(admin_api)
        session = _change(_login("agent@example.ci", temporary).data["access"], temporary).data
        user = _user("agent@example.ci")

        assert admin_api.post(f"{USERS}{user.pk}/reset_password/").status_code == 200

        assert _bearer(session["access"]).get(ME).status_code == 401

    def test_rbac_still_applies_after_change(self, admin_api):
        temporary = _create_agent(admin_api, role_codes=[])
        changed = _change(_login("agent@example.ci", temporary).data["access"], temporary)

        resp = _bearer(changed.data["access"]).get(PROTECTED)
        assert resp.status_code == 403
        assert "password_change_required" not in _code(resp)

    def test_tokens_without_version_follow_last_password_change(self, superadmin):
        """Jetons sans `sv` (app voyageurs, sessions antérieures) : valides sauf
        s'ils précèdent le dernier changement de mot de passe."""
        from datetime import timedelta

        from django.utils import timezone
        from rest_framework_simplejwt.tokens import RefreshToken

        legacy = str(RefreshToken.for_user(superadmin).access_token)
        assert _bearer(legacy).get(ME).status_code == 200

        superadmin.last_password_change = timezone.now() + timedelta(seconds=5)
        superadmin.save(update_fields=["last_password_change"])
        assert _bearer(legacy).get(ME).status_code == 401
