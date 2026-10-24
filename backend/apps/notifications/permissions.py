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


def _phone_key(value: str) -> str:
    """Forme de comparaison d'un numéro : indicatif + numéro national sans 0.

    « 0708090911 », « +2250708090911 » et « +225708090911 » désignent la même
    ligne ivoirienne (formats saisis différents) → même clé.
    """
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 10 and digits.startswith("0"):
        digits = "225" + digits
    if digits.startswith("225"):
        digits = "225" + digits[3:].lstrip("0")
    return digits if len(digits) >= 8 else ""


def is_admin_sender(user) -> bool:
    return bool(user and (user.is_superuser or _user_role_codes(user) & ADMIN_ROLES))


def recipient_allowed(user, traveler, channel: str, recipient: str) -> bool:
    """Anti SMS pumping par compte compromis : hors rôles d'administration,
    un agent ne peut écrire qu'aux coordonnées enregistrées du voyageur ciblé
    (jamais à un numéro arbitraire)."""
    if is_admin_sender(user):
        return True
    if traveler is None:
        return False
    recipient = (recipient or "").strip()
    if not recipient:
        return True  # le serveur choisira lui-même la coordonnée du voyageur
    if channel == "email":
        return recipient.lower() == (getattr(traveler, "email", "") or "").strip().lower()
    if channel in ("push", "telegram"):
        return recipient == (getattr(traveler, "public_id", "") or "")
    target = _phone_key(recipient)
    own = {
        _phone_key(getattr(traveler, attr, "") or "")
        for attr in ("phone_mobile", "whatsapp_phone", "emergency_phone_ci")
    }
    return bool(target) and target in own - {""}
