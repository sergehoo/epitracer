"""Permissions custom du module notifications.

Politique :
    - Voir l'historique : tout agent authentifié + actif
    - Envoyer SMS / WhatsApp : NATIONAL_ADMIN, MINISTRY, INHP, DISTRICT,
      BORDER_AGENT, FIELD_AGENT, ENTRY_POINT
    - Retry / cancel : NATIONAL_ADMIN, MINISTRY, INHP
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.accounts.models import RoleCode


SEND_ROLES = {
    RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
    RoleCode.DISTRICT, RoleCode.BORDER_AGENT, RoleCode.FIELD_AGENT,
    RoleCode.ENTRY_POINT,
}

ADMIN_ROLES = {
    RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
}


def _user_role_codes(user):
    if not user or not user.is_authenticated:
        return set()
    return set(user.role_codes())


class CanViewNotifications(BasePermission):
    """Tout agent authentifié + actif (rôle quelconque). Lecture seule."""

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active)


class CanSendNotification(BasePermission):
    """Peut envoyer un message manuel (cf. SEND_ROLES)."""

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated and u.is_active):
            return False
        return bool(_user_role_codes(u) & SEND_ROLES)


class CanRetryNotification(BasePermission):
    """Peut relancer / annuler (cf. ADMIN_ROLES)."""

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated and u.is_active):
            return False
        return bool(_user_role_codes(u) & ADMIN_ROLES)
