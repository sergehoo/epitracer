"""Permissions RBAC granulaires pour les rapports automatisés.

6 permissions distinctes (au lieu d'un unique "admin peut tout") pour
respecter le principe de moindre privilège. Chacune est mappée en
combinaison d'un rôle Django + d'une permission modèle.

Matrice d'autorisation cible :

  Permission                    | NATIONAL_ADMIN | MINISTRY | INHP | DISTRICT | OBSERVER
  ------------------------------|----------------|----------|------|----------|----------
  view_weekly_reports           |       ✓        |    ✓     |  ✓   |    ✓     |    ✓
  generate_weekly_reports       |       ✓        |    ✓     |  ✓   |    –     |    –
  send_weekly_reports           |       ✓        |    –     |  ✓   |    –     |    –
  manage_report_recipients      |       ✓        |    –     |  ✓   |    –     |    –
  manage_report_schedule        |       ✓        |    –     |  –   |    –     |    –
  download_sensitive_reports    |       ✓        |    ✓     |  ✓   |    –     |    –
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission


# ---------------------------------------------------------------------------
# Base : utilisateur actif + rôle CI parmi la whitelist
# ---------------------------------------------------------------------------
class _BaseReportsPermission(BasePermission):
    """Base commune : vérifie l'utilisateur actif + rôle dans allowed_roles."""

    allowed_roles: set[str] = set()

    def has_permission(self, request, view) -> bool:
        u = request.user
        if not (u and u.is_authenticated and u.is_active):
            return False
        try:
            user_roles = set(u.role_codes())
        except Exception:  # noqa: BLE001
            return False
        return bool(self.allowed_roles & user_roles)


# ---------------------------------------------------------------------------
# 1. view_weekly_reports — voir la liste + le détail (large accès lecture)
# ---------------------------------------------------------------------------
class CanViewWeeklyReports(_BaseReportsPermission):
    """Lecture des rapports générés — tous les rôles opérationnels."""
    message = "Vous n'avez pas la permission de consulter les rapports."
    allowed_roles = {
        "NATIONAL_ADMIN", "MINISTRY", "INHP", "DISTRICT", "OBSERVER",
        "ENTRY_POINT",
    }


# ---------------------------------------------------------------------------
# 2. generate_weekly_reports — déclencher une génération manuelle
# ---------------------------------------------------------------------------
class CanGenerateWeeklyReports(_BaseReportsPermission):
    """Déclencher `generate_weekly_report` hors du cron Beat."""
    message = "Vous n'avez pas la permission de générer un rapport."
    allowed_roles = {"NATIONAL_ADMIN", "MINISTRY", "INHP"}


# ---------------------------------------------------------------------------
# 3. send_weekly_reports — envoyer manuellement (attention coût SMS)
# ---------------------------------------------------------------------------
class CanSendWeeklyReports(_BaseReportsPermission):
    """Déclencher un envoi de rapport (email + SMS) hors Beat.

    Restrictif car coût potentiellement massif si mal configuré.
    """
    message = "Vous n'avez pas la permission d'envoyer un rapport."
    allowed_roles = {"NATIONAL_ADMIN", "INHP"}


# ---------------------------------------------------------------------------
# 4. manage_report_recipients — CRUD destinataires
# ---------------------------------------------------------------------------
class CanManageReportRecipients(_BaseReportsPermission):
    """Ajouter/modifier/désactiver/supprimer les destinataires."""
    message = "Gestion des destinataires réservée à l'administration nationale."
    allowed_roles = {"NATIONAL_ADMIN", "INHP"}


# ---------------------------------------------------------------------------
# 5. manage_report_schedule — modifier la planification Beat
# ---------------------------------------------------------------------------
class CanManageReportSchedule(_BaseReportsPermission):
    """Modifier la fréquence / heure / activation du cron."""
    message = "Modification de la planification réservée au Super Admin."
    allowed_roles = {"NATIONAL_ADMIN"}


# ---------------------------------------------------------------------------
# 6. download_sensitive_reports — télécharger PDF/Excel (contient PII agrégée)
# ---------------------------------------------------------------------------
class CanDownloadReports(_BaseReportsPermission):
    """Télécharger les fichiers PDF/Excel des rapports.

    Le rapport contient des agrégats sensibles (cas confirmés par district,
    évolution épidémiologique) qui ne doivent pas fuiter. Accès trace par
    audit log + IP + user-agent (Phase 6).
    """
    message = "Téléchargement réservé aux acteurs sanitaires nationaux."
    allowed_roles = {"NATIONAL_ADMIN", "MINISTRY", "INHP"}
