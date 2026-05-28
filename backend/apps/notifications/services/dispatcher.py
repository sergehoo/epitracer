"""Dispatcher orchestrant le routage et l'envoi d'une notification.

Pipeline :
    1. validate + normalize + détection provider (router.py)
    2. création de l'objet Notification (status=PENDING)
    3. dispatch synchrone (eager) OU enqueue Celery (recommandé)
    4. persiste l'état + audit log
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.notifications.models import (
    Channel, Direction, MessageType, Notification, NotificationStatus,
    NotificationTemplate, Provider,
)
from apps.notifications.services.audit import Actions, log_action
from apps.notifications.services.router import (
    NotificationProviderRouter, PhoneValidationError,
)

logger = logging.getLogger("epidemitracker.notifications.dispatcher")


@dataclass
class SendResult:
    ok: bool
    notification_id: Optional[int] = None
    provider: str = ""
    provider_message_id: str = ""
    error: str = ""


# ---------------------------------------------------------------------------
# Rendu de template avec variables {var}
# ---------------------------------------------------------------------------
def _render(template_body: str, context: dict) -> str:
    if not context:
        return template_body
    try:
        return template_body.format(**context)
    except (KeyError, IndexError) as exc:
        logger.warning("Template rendering failed (missing var %s) — falling back to raw", exc)
        return template_body


# ---------------------------------------------------------------------------
# Création + enfilage
# ---------------------------------------------------------------------------
def enqueue_notification(
    *,
    channel: str,
    recipient: str,
    body: str,
    subject: str = "",
    traveler=None,
    template: Optional[NotificationTemplate] = None,
    context: Optional[dict] = None,
    message_type: str = MessageType.AUTOMATIC_REMINDER,
    sent_by=None,
    request=None,
    force_provider: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> SendResult:
    """Point d'entrée unique : valide, persiste, et enqueue l'envoi Celery.

    Args:
        channel : "sms" ou "whatsapp"
        recipient : numéro brut (sera normalisé)
        body : contenu pré-rendu (variables déjà substituées si template)
        traveler : Traveler associé (optionnel, recommandé pour traçabilité)
        template : NotificationTemplate utilisé (si rendu serveur)
        context : variables pour le template (utilisé si body non fourni)
        message_type : catégorie d'audit
        sent_by : User qui déclenche l'envoi (None = système)
        request : HttpRequest pour journaliser IP + UA (optionnel)
        force_provider : surcharge le routage (admin uniquement, refusé pour CI→Twilio)
        metadata : payload libre stocké sur Notification.metadata

    Returns:
        SendResult avec l'ID de notification créée et le statut initial.
    """
    channel = (channel or "").lower()
    if channel not in {Channel.SMS, Channel.WHATSAPP}:
        return SendResult(ok=False, error=f"Canal non supporté : {channel!r}")

    # 1) Détection provider (avec validation du numéro)
    try:
        decision = NotificationProviderRouter.detect(recipient, channel=channel)
    except PhoneValidationError as exc:
        return SendResult(ok=False, error=str(exc))
    except Exception as exc:  # noqa: BLE001
        return SendResult(ok=False, error=f"Erreur de routage : {exc}")

    # 2) Application forced_provider — interdit de contourner la règle CI→OrangeCI
    final_provider = decision.provider
    if force_provider and force_provider != final_provider:
        if decision.is_ivoirian and force_provider != Provider.ORANGE_CI:
            return SendResult(
                ok=False,
                error="Numéro ivoirien : envoi Twilio refusé (politique nationale).",
            )
        final_provider = force_provider

    # 3) Rendu body si template + context fournis (body laissé vide)
    final_body = body
    if not final_body and template and context:
        final_body = _render(template.body, context)
    elif template and context:
        # On considère que body fourni est prioritaire (édition libre)
        pass

    if not final_body or not final_body.strip():
        return SendResult(ok=False, error="Le corps du message est vide.")
    if len(final_body) > 1530:
        return SendResult(
            ok=False,
            error="Message trop long (max 1530 caractères, soit 10 segments SMS).",
        )

    # 4) Création de l'objet Notification
    notif = Notification.objects.create(
        channel=channel,
        template=template,
        traveler=traveler,
        recipient=recipient,
        normalized_phone=decision.normalized,
        body=final_body,
        subject=subject,
        context=context or {},
        direction=Direction.OUTBOUND,
        message_type=message_type,
        status=NotificationStatus.QUEUED,
        provider=final_provider,
        sent_by=sent_by if sent_by and sent_by.is_authenticated else None,
        queued_at=timezone.now(),
        metadata={
            **(metadata or {}),
            "routing": {
                "country_code": decision.country_code,
                "is_ivoirian": decision.is_ivoirian,
            },
        },
    )

    log_action(notification=notif, action=Actions.CREATE, actor=sent_by, request=request)

    # 5) Enqueue Celery (best-effort : si Celery KO, on essaye en sync)
    try:
        from apps.notifications.tasks import send_notification_task
        send_notification_task.delay(notif.id)
        log_action(notification=notif, action=Actions.SEND, actor=sent_by, request=request,
                   metadata={"mode": "celery_async"})
    except Exception as exc:  # noqa: BLE001
        logger.warning("Celery enqueue failed, fallback to sync send : %s", exc)
        return _send_sync(notif)

    return SendResult(
        ok=True,
        notification_id=notif.id,
        provider=final_provider,
        provider_message_id="",
        error="",
    )


def _send_sync(notif: Notification) -> SendResult:
    """Envoi synchrone si Celery indisponible — utilisé en fallback."""
    from apps.notifications.tasks import _execute_send  # import local pour éviter cycle
    ok, msg_id, err = _execute_send(notif)
    return SendResult(
        ok=ok,
        notification_id=notif.id,
        provider=notif.provider,
        provider_message_id=msg_id,
        error=err,
    )


# ---------------------------------------------------------------------------
# Helpers métier — utilisés depuis les vues admin et les autres apps
# ---------------------------------------------------------------------------
def send_manual_message(
    *,
    traveler,
    recipient: str,
    body: str,
    channel: str = Channel.SMS,
    sent_by,
    request=None,
) -> SendResult:
    """Envoi manuel d'un message libre depuis le dashboard admin.

    Tracé avec sent_by (obligatoire) et message_type = MANUAL_MESSAGE.
    """
    if sent_by is None or not getattr(sent_by, "is_authenticated", False):
        return SendResult(ok=False, error="Utilisateur non authentifié.")

    return enqueue_notification(
        channel=channel,
        recipient=recipient,
        body=body,
        traveler=traveler,
        message_type=MessageType.MANUAL_MESSAGE,
        sent_by=sent_by,
        request=request,
    )


def send_template_message(
    *,
    traveler,
    recipient: str,
    template_code: str,
    context: Optional[dict] = None,
    channel: str = Channel.SMS,
    sent_by=None,
    request=None,
    message_type: str = MessageType.MANUAL_MESSAGE,
) -> SendResult:
    """Envoi depuis un template prédéfini (avec rendu de variables)."""
    template = NotificationTemplate.objects.filter(code=template_code, is_active=True).first()
    if not template:
        return SendResult(ok=False, error=f"Template introuvable : {template_code}")

    body = _render(template.body, context or {})

    return enqueue_notification(
        channel=channel,
        recipient=recipient,
        body=body,
        subject=template.subject,
        traveler=traveler,
        template=template,
        context=context or {},
        message_type=message_type,
        sent_by=sent_by,
        request=request,
    )
