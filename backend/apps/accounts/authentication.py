"""Authentification JWT de l'API : version de session et changement de mot de passe imposé.

Contrôle centralisé (DEFAULT_AUTHENTICATION_CLASSES), sans toucher aux vues :

1. Révocation. Les jetons émis au login portent `sv`, empreinte de la version
   de session dérivée du hash du mot de passe (comme les sessions Django).
   Changer de mot de passe change la version : les jetons antérieurs sont
   refusés, la session émise après le changement reste valide. Jetons sans
   `sv` (app voyageurs, jetons émis avant ce contrôle) : refusés s'ils
   précèdent le dernier changement de mot de passe.
2. Changement imposé. Tant que `must_change_password` est vrai, seules les API
   indispensables (état de session, changement de mot de passe, enrôlement
   MFA) et les API publiques répondent ; les autres renvoient 403
   `password_change_required`.
"""
from __future__ import annotations

import hashlib
import hmac

from rest_framework import exceptions
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication

SESSION_VERSION_CLAIM = "sv"


def session_version(user) -> str:
    return hashlib.sha256(user.get_session_auth_hash().encode()).hexdigest()[:16]


class PasswordChangeRequiredError(exceptions.PermissionDenied):
    default_detail = "Changement de mot de passe obligatoire avant d'accéder à la console."
    default_code = "password_change_required"


class EpiJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if (
            result is not None
            and getattr(result[0], "must_change_password", False)
            and not _allowed_while_change_pending(request)
        ):
            raise PasswordChangeRequiredError()
        return result

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not _session_is_current(user, validated_token):
            raise exceptions.AuthenticationFailed(
                "Session expirée : le mot de passe a été modifié. Reconnectez-vous.",
                code="session_revoked",
            )
        return user


def _session_is_current(user, token) -> bool:
    version = token.get(SESSION_VERSION_CLAIM)
    if version is not None:
        return hmac.compare_digest(str(version), session_version(user))
    changed = getattr(user, "last_password_change", None)
    return changed is None or int(token.get("iat", 0)) >= int(changed.timestamp())


def _allowed_while_change_pending(request) -> bool:
    from apps.accounts import views

    view = (getattr(request, "parser_context", None) or {}).get("view")
    allowed = (
        views.MeView | views.ChangePasswordView
        | views.MFASetupView | views.MFAVerifyView | views.MfaEmailEnableView
    )
    if isinstance(view, allowed):
        return True
    # API publique : l'identité n'y est pas exigée, le compte n'y donne aucun droit.
    permissions = getattr(view, "permission_classes", ())
    return all(isinstance(p, type) and issubclass(p, AllowAny) for p in permissions)
