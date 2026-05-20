"""Permissions DRF transversales basées sur le RBAC EpidemiTracker."""
from __future__ import annotations

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthenticatedAndActive(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active)


class HasRole(BasePermission):
    """Autorise si l'utilisateur a au moins un rôle parmi ceux listés.

    Usage :
        permission_classes = [IsAuthenticated, HasRole]
        required_roles = ["NATIONAL_ADMIN", "MINISTRY", "INHP"]
    """

    def has_permission(self, request, view):
        required = set(getattr(view, "required_roles", []) or [])
        if not required:
            return True
        user_roles = set(request.user.role_codes()) if request.user.is_authenticated else set()
        return bool(required & user_roles)


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class HasModelPermission(BasePermission):
    """Permission Django classique mappée par action DRF.

    Configurer côté view :
        perms_map = {
            "list": ["app.view_model"],
            "retrieve": ["app.view_model"],
            "create": ["app.add_model"],
            "update": ["app.change_model"],
            "partial_update": ["app.change_model"],
            "destroy": ["app.delete_model"],
        }
    """

    def has_permission(self, request, view):
        perms = getattr(view, "perms_map", {}).get(getattr(view, "action", ""), [])
        if not perms:
            return True
        return all(request.user.has_perm(p) for p in perms)
