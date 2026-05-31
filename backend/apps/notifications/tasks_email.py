"""Tâches Celery pour le système email multi-expéditeur EpiTrace.

Routées automatiquement vers la queue `notifications` via
CELERY_TASK_ROUTES["notifications.*"] (cf. settings/base.py).
"""
from __future__ import annotations

import logging
from typing import Optional

from celery import shared_task
from django.utils import timezone

from .email_models import EmailLog, EmailStatus, EmailType
from .services.email_router import _execute_email_send, send_email_by_type

logger = logging.getLogger("epidemitracker.tasks.email")


# ---------------------------------------------------------------------------
# Tâche principale : envoyer un email déjà enregistré en QUEUED
# ---------------------------------------------------------------------------
@shared_task(
    name="notifications.send_email_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def send_email_task(self, log_id: int) -> dict:
    """Envoie l'email identifié par EmailLog.id.

    Stratégie :
      - 3 retries max avec backoff 30s/60s/120s
      - FINAL status FAILED après épuisement
    """
    try:
        log = EmailLog.objects.get(pk=log_id)
    except EmailLog.DoesNotExist:
        logger.error("send_email_task: EmailLog %s introuvable", log_id)
        return {"ok": False, "error": "EmailLog not found"}

    if log.status in (EmailStatus.SENT, EmailStatus.DELIVERED, EmailStatus.CANCELLED):
        return {"ok": True, "skipped": True, "status": log.status}

    if log.retry_count >= log.max_retries:
        log.status = EmailStatus.FAILED
        log.failed_at = timezone.now()
        log.save(update_fields=["status", "failed_at"])
        return {"ok": False, "error": "Max retries exhausted"}

    ok = _execute_email_send(log)
    if not ok and log.retry_count < log.max_retries:
        raise RuntimeError(
            f"Email envoi échoué (retry {log.retry_count}/{log.max_retries}) : "
            f"{log.error_message}"
        )
    return {
        "ok": ok,
        "log_id": log.id,
        "status": log.status,
        "error": log.error_message,
    }


# ---------------------------------------------------------------------------
# Retry périodique des FAILED récents (Celery Beat — toutes les 15 min)
# ---------------------------------------------------------------------------
@shared_task(name="notifications.retry_failed_emails")
def retry_failed_emails(max_age_hours: int = 24, batch: int = 100) -> dict:
    """Relance les emails FAILED des dernières heures avec retry_count < max."""
    from datetime import timedelta
    from django.db.models import F

    cutoff = timezone.now() - timedelta(hours=max_age_hours)
    qs = (
        EmailLog.objects
        .filter(status=EmailStatus.FAILED, failed_at__gte=cutoff)
        .filter(retry_count__lt=F("max_retries"))
        .order_by("failed_at")[:batch]
    )
    n = 0
    for log in qs:
        log.status = EmailStatus.QUEUED
        log.save(update_fields=["status", "updated_at"])
        send_email_task.delay(log.id)
        n += 1
    return {"requeued": n}


# ---------------------------------------------------------------------------
# Helpers métier — création compte / reset password / campagne
# ---------------------------------------------------------------------------
@shared_task(name="notifications.send_admin_account_created_email")
def send_admin_account_created_email(
    user_id: int,
    temporary_password: str,
    *,
    admin_login_url: Optional[str] = None,
) -> dict:
    """Envoie l'email de bienvenue admin/agent depuis inhp@veillesanitaire.com.

    Tâche dédiée pour pouvoir être appelée depuis le signal post_save de
    User sans bloquer la requête HTTP. Le mot de passe temporaire transite
    via Redis (broker Celery interne) — ne sort jamais du périmètre serveur.
    """
    from django.conf import settings
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return {"ok": False, "error": "User not found"}

    full_name = (
        f"{user.first_name} {user.last_name}".strip()
        or user.get_username() or user.email
    )
    roles = ", ".join(
        a.role.name for a in user.role_assignments.select_related("role").filter(is_active=True)
    ) or "—"

    ctx = {
        "full_name": full_name,
        "username": user.get_username(),
        "email": user.email,
        "temporary_password": temporary_password,
        "roles": roles,
        "admin_login_url": admin_login_url or getattr(
            settings, "ADMIN_LOGIN_URL", "https://admin.veillesanitaire.com/login",
        ),
    }

    # ── Tentative 1 : template DB (admin a pu l'éditer) ──
    result = send_email_by_type(
        email_type=EmailType.ADMIN_ACCOUNT_CREATED,
        recipient=user.email,
        context=ctx,
        template_code="admin_account_created",
        related_user=user,
    )
    if result.ok:
        return {"ok": True, "log_id": result.log_id, "via": "db_template"}

    # ── Tentative 2 : fallback HTML inline depuis le code (premier
    # déploiement, ou si le template DB a été désactivé par erreur).
    subject = "Création de votre compte — Console INHP Veille Sanitaire"
    body_html = """
<p>Bonjour <strong>{full_name}</strong>,</p>
<p>Votre compte a été créé sur la <strong>console INHP Veille Sanitaire</strong>
(plateforme EpiTrace).</p>
<table style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px">
  <tr><td style="padding:6px 12px;background:#f4f4f4">Identifiant</td>
      <td style="padding:6px 12px"><code>{username}</code></td></tr>
  <tr><td style="padding:6px 12px;background:#f4f4f4">Rôle(s)</td>
      <td style="padding:6px 12px">{roles}</td></tr>
  <tr><td style="padding:6px 12px;background:#f4f4f4">Mot de passe temporaire</td>
      <td style="padding:6px 12px"><code>{temporary_password}</code></td></tr>
  <tr><td style="padding:6px 12px;background:#f4f4f4">Lien de connexion</td>
      <td style="padding:6px 12px"><a href="{admin_login_url}">{admin_login_url}</a></td></tr>
</table>
<p style="color:#b91c1c"><strong>Important :</strong> pour des raisons de sécurité,
vous devrez modifier ce mot de passe lors de votre première connexion.
Le mot de passe temporaire expire dans 24 heures.</p>
<p>Si vous n'êtes pas à l'origine de cette demande ou si vous avez besoin
d'assistance, contactez immédiatement l'administrateur de la plateforme.</p>
<p>Cordialement,<br/><strong>INHP — Veille Sanitaire</strong></p>
""".strip()

    result = send_email_by_type(
        email_type=EmailType.ADMIN_ACCOUNT_CREATED,
        recipient=user.email,
        context=ctx,
        subject=subject,
        body_html=body_html,
        related_user=user,
    )
    return {"ok": result.ok, "log_id": result.log_id, "error": result.error, "via": "fallback"}


@shared_task(name="notifications.send_password_reset_email")
def send_password_reset_email(user_id: int, raw_token: str) -> dict:
    """Envoie l'email de reset password (lien tokenisé)."""
    from django.conf import settings
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return {"ok": False, "error": "User not found"}

    base = getattr(settings, "ADMIN_LOGIN_URL", "https://admin.veillesanitaire.com/login")
    reset_url = base.rstrip("/login").rstrip("/") + f"/reset-password?token={raw_token}"
    ttl_h = getattr(settings, "PASSWORD_RESET_TOKEN_TTL_HOURS", 24)

    full_name = (
        f"{user.first_name} {user.last_name}".strip()
        or user.get_username() or user.email
    )

    ctx = {"full_name": full_name, "reset_url": reset_url, "ttl_hours": ttl_h}

    # Tentative 1 : template DB
    result = send_email_by_type(
        email_type=EmailType.ADMIN_PASSWORD_RESET,
        recipient=user.email,
        context=ctx,
        template_code="admin_password_reset",
        related_user=user,
    )
    if result.ok:
        return {"ok": True, "log_id": result.log_id, "via": "db_template"}

    # Tentative 2 : fallback HTML inline
    subject = "Réinitialisation de votre mot de passe — INHP Veille Sanitaire"
    body_html = f"""
<p>Bonjour <strong>{full_name}</strong>,</p>
<p>Une demande de réinitialisation de votre mot de passe a été effectuée sur
la console INHP Veille Sanitaire.</p>
<p>Pour définir un nouveau mot de passe, cliquez sur le lien ci-dessous :</p>
<p><a href="{reset_url}"
   style="display:inline-block;padding:10px 18px;background:#F77F00;color:white;
          border-radius:6px;text-decoration:none;font-weight:bold">
  Réinitialiser mon mot de passe
</a></p>
<p style="color:#64748b;font-size:12px">Ou copiez ce lien dans votre navigateur :
<br/><code style="word-break:break-all">{reset_url}</code></p>
<p style="color:#b91c1c"><strong>Important :</strong> ce lien est valable
<strong>{ttl_h} heures</strong> et ne peut être utilisé qu'une seule fois.</p>
<p>Si vous n'êtes pas à l'origine de cette demande, ignorez cet email et
vérifiez la sécurité de votre compte.</p>
<p>Cordialement,<br/><strong>INHP — Veille Sanitaire</strong></p>
""".strip()

    result = send_email_by_type(
        email_type=EmailType.ADMIN_PASSWORD_RESET,
        recipient=user.email,
        context=ctx,
        subject=subject,
        body_html=body_html,
        related_user=user,
    )
    return {"ok": result.ok, "log_id": result.log_id, "error": result.error, "via": "fallback"}


@shared_task(name="notifications.send_campaign_email_batch")
def send_campaign_email_batch(
    template_code: str,
    recipients: list[str],
    context: Optional[dict] = None,
    email_type: str = EmailType.TRAVELER_CAMPAIGN,
) -> dict:
    """Envoi en lot d'une campagne email — un EmailLog par destinataire."""
    sent = 0
    failed = 0
    for recipient in recipients[:5000]:  # cap de sécurité
        result = send_email_by_type(
            email_type=email_type,
            recipient=recipient,
            template_code=template_code,
            context=context or {},
        )
        if result.ok:
            sent += 1
        else:
            failed += 1
    return {"sent": sent, "failed": failed, "total": sent + failed}
