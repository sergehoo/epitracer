"""Tâches Celery d'envoi de notifications (SMS, WhatsApp, Email, Push).

Architecture :
    - send_notification_task(notification_id) : envoie une notification déjà
      créée en DB (via dispatcher.enqueue_notification)
    - retry_failed_notifications : balaye les FAILED récentes pour retry
    - send_notification (legacy, compat) : crée + envoie en une seule tâche

Stratégie de retry :
    - autoretry_for=(Exception,)
    - max_retries=3
    - backoff exponentiel : 30s, 60s, 120s
    - statut FINAL = "failed" après épuisement
"""
from __future__ import annotations

import logging
from typing import Tuple

from celery import shared_task
from django.utils import timezone

from .models import (
    Channel, MessageType, Notification, NotificationStatus,
    NotificationTemplate, Provider,
)
from .services.audit import Actions, log_action

logger = logging.getLogger("epidemitracker.notifications.tasks")


# ---------------------------------------------------------------------------
# Implementation centrale d'envoi (utilisable en sync ou async)
# ---------------------------------------------------------------------------
def _execute_send(notif: Notification) -> Tuple[bool, str, str]:
    """Exécute l'envoi via le bon provider et met à jour la Notification.

    Retourne (ok, provider_message_id, error_message).
    """
    notif.retry_count += 1

    try:
        if notif.channel == Channel.SMS:
            if notif.provider == Provider.ORANGE_CI:
                from .services.sms_orange_ci import send_sms as send_orange
                # callback_data = notif.id → permet au webhook Orange CI de
                # mapper le delivery report sur la bonne notification.
                res = send_orange(
                    notif.normalized_phone,
                    notif.body,
                    callback_data=str(notif.id),
                )
                ok, msg_id, err = res.ok, res.provider_message_id, res.error
            elif notif.provider == Provider.TWILIO:
                from .services.sms_twilio import send_sms as send_tw
                res = send_tw(notif.normalized_phone, notif.body)
                ok, msg_id, err = res.ok, res.provider_message_id, res.error
            else:
                # Fallback / stub
                from .providers import send_sms as send_legacy
                res = send_legacy(notif.normalized_phone, notif.body)
                ok, msg_id, err = res.ok, res.provider_id, res.error

        elif notif.channel == Channel.WHATSAPP:
            # Phase C : provider WhatsApp pluggable (Twilio ou Meta).
            from .services.whatsapp_base import get_active_provider
            wp = get_active_provider()

            # Si la notif référence un template, on tente d'abord le template.
            # Sinon (ou si pas de template_code) on envoie en texte libre.
            # Le NotificationTemplate peut contenir une metadata mapping le
            # `code` métier vers les identifiants fournisseurs :
            #   {"twilio_content_sid": "HX...", "meta_template_name": "..."}
            # On utilise l'identifiant adapté selon le provider actif.
            template_code = ""
            if notif.template_id and notif.template:
                meta = getattr(notif.template, "metadata", {}) or {}
                # Note : NotificationTemplate n'a pas (encore) de champ metadata
                # → on lit aussi variables_schema en fallback s'il sert de map.
                if wp.name == "twilio":
                    template_code = (
                        meta.get("twilio_content_sid")
                        or notif.template.code
                    )
                elif wp.name == "meta_whatsapp":
                    template_code = (
                        meta.get("meta_template_name")
                        or notif.template.code.lower().replace("-", "_")
                    )
                else:
                    template_code = notif.template.code
            # Variables ordonnées pour les templates (les valeurs sont
            # extraites de notif.context selon l'ordre de variables_schema)
            variables = []
            if notif.template_id and notif.template and notif.context:
                schema = notif.template.variables_schema or {}
                ordered_keys = list(schema.keys()) if schema else list(notif.context.keys())
                variables = [
                    str(notif.context.get(k, "")) for k in ordered_keys
                ]

            # Stratégie :
            # 1) Si on a un template_code → tenter d'abord send_template
            # 2) Si pas de template OU échec template → tenter send_text
            res = None
            if template_code:
                res = wp.send_template(
                    notif.normalized_phone, template_code, variables,
                    language=(notif.context or {}).get("_lang", "fr"),
                )
                if not res.ok and "session" not in (res.error or "").lower():
                    # Template KO pour autre raison qu'une fenêtre 24h : on
                    # retourne l'erreur sans fallback (sinon on pourrait
                    # spammer le destinataire). Le retry Celery se chargera.
                    pass
            if res is None or not res.ok:
                # Tentative texte libre (session de 24h)
                fallback = wp.send_text(notif.normalized_phone, notif.body)
                if fallback.ok:
                    res = fallback

            ok = bool(res and res.ok)
            msg_id = res.provider_message_id if res else ""
            err = res.error if res else "WhatsApp : provider inactif"

        elif notif.channel == Channel.EMAIL:
            from .providers import send_email as send_em
            res = send_em(notif.recipient, notif.subject, notif.body)
            ok, msg_id, err = res.ok, res.provider_id, res.error

        elif notif.channel == Channel.PUSH:
            from .providers import send_push as send_pu
            res = send_pu(notif.recipient, notif.subject, notif.body)
            ok, msg_id, err = res.ok, res.provider_id, res.error

        else:
            ok, msg_id, err = False, "", f"Canal non supporté : {notif.channel}"

    except Exception as exc:  # noqa: BLE001
        logger.exception("send notification crash (id=%s)", notif.id)
        ok, msg_id, err = False, "", str(exc)

    # Mise à jour finale
    if ok:
        notif.status = NotificationStatus.SENT
        notif.sent_at = timezone.now()
        notif.error_message = ""
        notif.provider_message_id = msg_id[:200] if msg_id else ""
    else:
        notif.status = NotificationStatus.FAILED
        notif.error_message = err[:1000] if err else ""
        notif.failed_at = timezone.now()

    notif.save(update_fields=[
        "status", "sent_at", "failed_at", "error_message",
        "provider_message_id", "retry_count", "updated_at",
    ])

    log_action(
        notification=notif,
        action=Actions.SEND if ok else Actions.FAILED,
        metadata={"retry_count": notif.retry_count, "provider": notif.provider, "ok": ok},
    )
    return ok, msg_id, err


# ---------------------------------------------------------------------------
# Tâche principale
# ---------------------------------------------------------------------------
@shared_task(
    name="notifications.send_notification_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,         # 30s, 60s, 120s
    retry_backoff_max=600,    # plafond 10 minutes
    retry_jitter=True,
    max_retries=3,
)
def send_notification_task(self, notification_id: int) -> dict:
    """Envoie la notification identifiée par son PK."""
    try:
        notif = Notification.objects.get(pk=notification_id)
    except Notification.DoesNotExist:
        logger.error("send_notification_task: notification %s introuvable", notification_id)
        return {"ok": False, "error": "Notification not found"}

    if notif.status in (NotificationStatus.SENT, NotificationStatus.DELIVERED, NotificationStatus.CANCELLED):
        return {"ok": True, "skipped": True, "status": notif.status}

    if notif.retry_count >= notif.max_retries:
        notif.status = NotificationStatus.FAILED
        notif.failed_at = timezone.now()
        notif.save(update_fields=["status", "failed_at"])
        return {"ok": False, "error": "Max retries exhausted"}

    ok, msg_id, err = _execute_send(notif)
    if not ok and notif.retry_count < notif.max_retries:
        # Laisse Celery faire le retry (raise → autoretry)
        raise RuntimeError(f"Envoi échoué (retry {notif.retry_count}/{notif.max_retries}) : {err}")
    return {"ok": ok, "provider_message_id": msg_id, "error": err}


# ---------------------------------------------------------------------------
# Retry des échecs récents (cron Celery Beat — toutes les 15 minutes)
# ---------------------------------------------------------------------------
@shared_task(name="notifications.retry_failed_notifications")
def retry_failed_notifications(max_age_hours: int = 24, batch: int = 100) -> dict:
    """Relance les notifications FAILED des dernières heures avec retry_count < max."""
    from datetime import timedelta
    cutoff = timezone.now() - timedelta(hours=max_age_hours)
    qs = (
        Notification.objects.filter(
            status=NotificationStatus.FAILED,
            failed_at__gte=cutoff,
        )
        .filter(retry_count__lt=models_F("max_retries"))
        .order_by("failed_at")[:batch]
    )
    n = 0
    for notif in qs:
        notif.status = NotificationStatus.QUEUED
        notif.save(update_fields=["status", "updated_at"])
        send_notification_task.delay(notif.id)
        n += 1
    return {"requeued": n}


def models_F(field: str):  # pragma: no cover — petit helper local
    from django.db.models import F
    return F(field)


# ---------------------------------------------------------------------------
# Legacy alias (compatibilité avec d'anciens appels)
# ---------------------------------------------------------------------------
@shared_task(name="notifications.send", bind=True, max_retries=3, default_retry_delay=30)
def send_notification(
    self,
    *,
    channel: str,
    recipient: str,
    template_code: str | None = None,
    subject: str = "",
    body: str = "",
    context: dict | None = None,
):
    """Ancienne signature. Crée la Notification puis délègue."""
    from .services.dispatcher import enqueue_notification

    template = None
    if template_code:
        template = NotificationTemplate.objects.filter(code=template_code).first()
        if template and not body:
            body = template.body

    result = enqueue_notification(
        channel=channel,
        recipient=recipient,
        body=body,
        subject=subject,
        template=template,
        context=context or {},
        message_type=MessageType.AUTOMATIC_REMINDER,
    )
    return {"ok": result.ok, "notification_id": result.notification_id, "error": result.error}
