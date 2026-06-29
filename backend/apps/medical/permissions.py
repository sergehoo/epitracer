"""Permissions DRF — module medical (Phase 9B).

Toutes les permissions s'appuient sur les rôles RBAC EpidemiTracker
(`apps.accounts.RoleCode`). Pour les agents terrain, la permission
exige que l'agent soit explicitement assigné au cas
(`QuarantineRecord.assigned_agent`).

Note : les permissions vérifient `has_permission` (au niveau de la vue) ET
`has_object_permission` quand un objet `QuarantineRecord` est résolu par
la vue avant l'action. Lorsque l'objet n'est pas encore accessible (POST
de création), le check d'assignation se fait dans la vue après résolution.
"""
from __future__ import annotations

import logging

from rest_framework.permissions import BasePermission

from apps.accounts.models import RoleCode
from apps.companion.models import DataAccessLog

logger = logging.getLogger("epidemitracker.medical")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_assigned_to(user, case) -> bool:
    """True si `user` est l'agent assigné au cas."""
    if user is None or case is None:
        return False
    if not getattr(user, "is_authenticated", False):
        return False
    return getattr(case, "assigned_agent_id", None) == getattr(user, "id", None)


def _has_any_role(user, *codes) -> bool:
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    try:
        return user.has_role(*codes)
    except Exception:  # pragma: no cover — défensif
        return False


# ---------------------------------------------------------------------------
# DataAccessLog helper — appelé par les vues sur lecture sensible.
# ---------------------------------------------------------------------------


def log_data_access(*, request, traveler, resource: str, reason: str = ""):
    """Persiste une entrée DataAccessLog. Retourne le log ou None en cas d'échec.

    Cette fonction NE DOIT JAMAIS lever d'exception qui interromprait le
    traitement de la requête (journalisation best-effort).
    """
    if traveler is None or request is None:
        return None
    user = getattr(request, "user", None)
    role_label = ""
    try:
        if user and getattr(user, "is_authenticated", False):
            first_role = user.role_assignments.select_related("role").first()
            if first_role and first_role.role:
                role_label = first_role.role.code
    except Exception:  # noqa: BLE001 — best effort
        role_label = ""

    fwd = request.META.get("HTTP_X_FORWARDED_FOR") if hasattr(request, "META") else None
    ip = (fwd.split(",")[0].strip() if fwd else
          request.META.get("REMOTE_ADDR") if hasattr(request, "META") else None)
    ua = request.META.get("HTTP_USER_AGENT", "") if hasattr(request, "META") else ""

    try:
        return DataAccessLog.objects.create(
            traveler=traveler,
            accessed_by=user if (user and getattr(user, "is_authenticated", False)) else None,
            accessed_by_role=role_label[:40],
            resource=resource,
            reason=(reason or "")[:200],
            ip_address=ip,
            user_agent=(ua or "")[:300],
        )
    except Exception:  # noqa: BLE001
        logger.exception("DataAccessLog persistence failed")
        return None


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------


class _BaseAuthPermission(BasePermission):
    """Base : exige user authentifié + actif."""

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active)


class CanViewFollowupDetail(_BaseAuthPermission):
    """NATIONAL_ADMIN, MINISTRY, INHP, DISTRICT, ENTRY_POINT, FIELD_AGENT(assigné)."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if _has_any_role(
            request.user,
            RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
            RoleCode.DISTRICT, RoleCode.ENTRY_POINT,
        ):
            return True
        # FIELD_AGENT — exige une assignation, validée dans la vue.
        return _has_any_role(request.user, RoleCode.FIELD_AGENT)

    def has_object_permission(self, request, view, obj):
        if _has_any_role(
            request.user,
            RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
            RoleCode.DISTRICT, RoleCode.ENTRY_POINT,
        ):
            return True
        if _has_any_role(request.user, RoleCode.FIELD_AGENT):
            return _user_assigned_to(request.user, obj)
        return False


class CanEditFollowup(_BaseAuthPermission):
    """NATIONAL_ADMIN, INHP, DISTRICT."""

    REQUIRED = (RoleCode.NATIONAL_ADMIN, RoleCode.INHP, RoleCode.DISTRICT)

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return _has_any_role(request.user, *self.REQUIRED)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class CanAddMedicalAction(_BaseAuthPermission):
    """NATIONAL_ADMIN, INHP, DISTRICT, FIELD_AGENT (assigné)."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return _has_any_role(
            request.user,
            RoleCode.NATIONAL_ADMIN, RoleCode.INHP, RoleCode.DISTRICT,
            RoleCode.FIELD_AGENT,
        )

    def has_object_permission(self, request, view, obj):
        if _has_any_role(
            request.user,
            RoleCode.NATIONAL_ADMIN, RoleCode.INHP, RoleCode.DISTRICT,
        ):
            return True
        if _has_any_role(request.user, RoleCode.FIELD_AGENT):
            return _user_assigned_to(request.user, obj)
        return False


class CanRequestSample(_BaseAuthPermission):
    """NATIONAL_ADMIN, INHP, DISTRICT, FIELD_AGENT (assigné)."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return _has_any_role(
            request.user,
            RoleCode.NATIONAL_ADMIN, RoleCode.INHP, RoleCode.DISTRICT,
            RoleCode.FIELD_AGENT,
        )

    def has_object_permission(self, request, view, obj):
        if _has_any_role(
            request.user,
            RoleCode.NATIONAL_ADMIN, RoleCode.INHP, RoleCode.DISTRICT,
        ):
            return True
        if _has_any_role(request.user, RoleCode.FIELD_AGENT):
            return _user_assigned_to(request.user, obj)
        return False


class CanAddLabResult(_BaseAuthPermission):
    """NATIONAL_ADMIN, INHP, LABORATORY."""

    REQUIRED = (RoleCode.NATIONAL_ADMIN, RoleCode.INHP, RoleCode.LABORATORY)

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return _has_any_role(request.user, *self.REQUIRED)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class CanClassifyCase(_BaseAuthPermission):
    """NATIONAL_ADMIN, INHP (MINISTRY lecture seulement)."""

    REQUIRED = (RoleCode.NATIONAL_ADMIN, RoleCode.INHP)

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return _has_any_role(request.user, *self.REQUIRED)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class CanCloseFollowup(_BaseAuthPermission):
    """NATIONAL_ADMIN, INHP, DISTRICT."""

    REQUIRED = (RoleCode.NATIONAL_ADMIN, RoleCode.INHP, RoleCode.DISTRICT)

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return _has_any_role(request.user, *self.REQUIRED)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class CanSendFollowupNotification(_BaseAuthPermission):
    """NATIONAL_ADMIN, INHP, DISTRICT, FIELD_AGENT (assigné)."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return _has_any_role(
            request.user,
            RoleCode.NATIONAL_ADMIN, RoleCode.INHP, RoleCode.DISTRICT,
            RoleCode.FIELD_AGENT,
        )

    def has_object_permission(self, request, view, obj):
        if _has_any_role(
            request.user,
            RoleCode.NATIONAL_ADMIN, RoleCode.INHP, RoleCode.DISTRICT,
        ):
            return True
        if _has_any_role(request.user, RoleCode.FIELD_AGENT):
            return _user_assigned_to(request.user, obj)
        return False


class CanViewSensitiveMedicalData(_BaseAuthPermission):
    """NATIONAL_ADMIN, INHP, LABORATORY, FIELD_AGENT (assigné)."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return _has_any_role(
            request.user,
            RoleCode.NATIONAL_ADMIN, RoleCode.INHP, RoleCode.LABORATORY,
            RoleCode.FIELD_AGENT,
        )

    def has_object_permission(self, request, view, obj):
        if _has_any_role(
            request.user,
            RoleCode.NATIONAL_ADMIN, RoleCode.INHP, RoleCode.LABORATORY,
        ):
            return True
        if _has_any_role(request.user, RoleCode.FIELD_AGENT):
            return _user_assigned_to(request.user, obj)
        return False


class CanViewLocationHistory(_BaseAuthPermission):
    """NATIONAL_ADMIN, INHP, DISTRICT, FIELD_AGENT (assigné)."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return _has_any_role(
            request.user,
            RoleCode.NATIONAL_ADMIN, RoleCode.INHP, RoleCode.DISTRICT,
            RoleCode.FIELD_AGENT,
        )

    def has_object_permission(self, request, view, obj):
        if _has_any_role(
            request.user,
            RoleCode.NATIONAL_ADMIN, RoleCode.INHP, RoleCode.DISTRICT,
        ):
            return True
        if _has_any_role(request.user, RoleCode.FIELD_AGENT):
            return _user_assigned_to(request.user, obj)
        return False
