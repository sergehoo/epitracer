"""Disponibilité des fournisseurs : suspension sur crédit épuisé, alerte, reprise.

Cycle de vie (ex. Orange CI) :
  1. Un envoi reçoit HTTP 403 / POL0001 → `suspend_provider()` passe l'état à
     `quota_exhausted` (transition unique, protégée par un verrou de ligne) et
     alerte les administrateurs nationaux une seule fois par incident.
  2. Tant que l'état est suspendu, les envois non urgents vers ce fournisseur
     sont mis en `on_hold` sans appel réseau ni bascule vers un autre
     fournisseur (les +225 ne partent jamais par Twilio).
  3. Après réapprovisionnement, un administrateur appelle `resume_provider()` :
     l'état redevient `available` et les messages en attente encore pertinents
     sont renvoyés ; les rappels datés devenus obsolètes sont annulés.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.notifications.models import (
    MessageType,
    Notification,
    NotificationStatus,
    Provider,
    ProviderAvailability,
    ProviderState,
)

from .audit import Actions, log_action
from .errors import ErrorCode

logger = logging.getLogger("epidemitracker.notifications.availability")

# Messages qui ne doivent jamais être retenus par une suspension : on tente
# quand même l'envoi (une seule fois) — le fournisseur décidera.
URGENT_MESSAGE_TYPES = frozenset({MessageType.SYMPTOM_ALERT})
URGENT_KINDS = frozenset({"medical_escalation", "symptom_alert", "critical_symptom"})


def is_urgent(notif: Notification) -> bool:
    if notif.message_type in URGENT_MESSAGE_TYPES:
        return True
    meta = notif.metadata or {}
    return bool(meta.get("urgent")) or meta.get("kind") in URGENT_KINDS


def get_state(provider: str) -> ProviderAvailability | None:
    if not provider:
        return None
    return ProviderAvailability.objects.filter(provider=provider).first()


def is_suspended(provider: str) -> bool:
    if not provider:
        return False
    return (
        ProviderAvailability.objects.filter(provider=provider)
        .exclude(
            state=ProviderState.AVAILABLE,
        )
        .exists()
    )


def suspend_provider(
    provider: str,
    *,
    reason_code: str = ErrorCode.QUOTA_EXHAUSTED,
    detail: str = "",
) -> bool:
    """Suspend un fournisseur. Retourne True si c'est une nouvelle suspension.

    Idempotent et sûr en concurrence : plusieurs workers qui reçoivent le même
    403 en parallèle ne déclenchent qu'une seule transition (et une alerte).
    """
    state = {
        ErrorCode.QUOTA_EXHAUSTED: ProviderState.QUOTA_EXHAUSTED,
        ErrorCode.BUDGET_EXCEEDED: ProviderState.BUDGET_EXCEEDED,
    }.get(reason_code, ProviderState.UNAVAILABLE)
    now = timezone.now()
    with transaction.atomic():
        row, _ = ProviderAvailability.objects.get_or_create(provider=provider)
        row = ProviderAvailability.objects.select_for_update().get(pk=row.pk)
        if row.is_suspended:
            row.last_failure_at = now
            row.save(update_fields=["last_failure_at", "updated_at"])
            return False
        row.state = state
        row.reason_code = reason_code
        row.technical_detail = (detail or "")[:2000]
        row.suspended_at = now
        row.last_failure_at = now
        row.blocked_attempts = 0
        row.alert_sent_at = now
        row.save()
    logger.error(
        "Fournisseur %s suspendu (%s) — envois automatiques mis en attente.",
        provider,
        reason_code,
    )
    transaction.on_commit(lambda: _alert_admins(provider, reason_code))
    return True


def record_blocked_attempt(provider: str) -> None:
    ProviderAvailability.objects.filter(provider=provider).update(
        blocked_attempts=F("blocked_attempts") + 1,
    )


def _alert_admins(provider: str, reason_code: str) -> int:
    """Alerte email des administrateurs nationaux (une fois par incident)."""
    from .security import alert_admins

    label = Provider(provider).label if provider in Provider.values else provider
    if reason_code == ErrorCode.QUOTA_EXHAUSTED:
        title = "crédit épuisé"
        cause = "Le crédit SMS est épuisé (réponse fournisseur 403 / POL0001)."
    elif reason_code == ErrorCode.BUDGET_EXCEEDED:
        title = "budget SMS atteint"
        cause = (
            "Le budget SMS configuré (journalier, mensuel ou plafond fournisseur) est "
            "atteint : coupe-circuit EpiTrace déclenché pour éviter une consommation "
            "anormale (SMS pumping possible). Vérifier le journal des événements de "
            "sécurité avant de reprendre."
        )
    else:
        title = "suspendu"
        cause = "Le fournisseur refuse les envois."
    body = (
        f"Alerte EpiTrace — fournisseur {label} suspendu.\n\n"
        f"{cause}\n"
        "Les envois automatiques vers ce fournisseur sont mis en attente : aucune "
        "nouvelle tentative et aucune bascule vers un autre fournisseur pour les "
        "numéros ivoiriens (+225). Les alertes médicales urgentes restent tentées "
        "dans leur enveloppe dédiée.\n\n"
        "Après vérification (ou réapprovisionnement), reprendre les envois depuis la "
        "page Notifications du tableau de bord (bouton « Reprendre les envois »)."
    )
    return alert_admins(
        f"[EpiTrace] {label} — {title}",
        body,
        kind="provider_suspended",
    )


def hold_notification(notif: Notification, *, error_code: str, detail: str = "") -> None:
    """Met une notification en attente fournisseur (sans la compter en échec)."""
    notif.status = NotificationStatus.ON_HOLD
    notif.error_code = error_code
    notif.error_message = (detail or "")[:1000]
    notif.save(update_fields=["status", "error_code", "error_message", "updated_at"])
    log_action(
        notification=notif,
        action=Actions.HOLD,
        metadata={"provider": notif.provider, "error_code": error_code},
    )


@dataclass
class ResumeResult:
    provider: str
    was_suspended: bool
    requeued: int = 0
    expired: int = 0


def _is_expired_reminder(notif: Notification, today) -> bool:
    """Un rappel daté (« Jour 20/21 ») ne doit pas partir un autre jour, ni un
    code OTP (valable 10 minutes) après coup."""
    if notif.message_type == MessageType.OTP:
        return notif.created_at < timezone.now() - timedelta(minutes=10)
    if not notif.dedup_key:
        return False
    reminder_date = (notif.metadata or {}).get("reminder_date")
    if reminder_date:
        return reminder_date < today.isoformat()
    return timezone.localdate(notif.created_at) < today


def resume_provider(
    provider: str,
    *,
    user=None,
    request=None,
    requeue: bool = True,
) -> ResumeResult:
    """Reprise contrôlée après réapprovisionnement (action administrateur)."""
    now = timezone.now()
    with transaction.atomic():
        row, _ = ProviderAvailability.objects.get_or_create(provider=provider)
        row = ProviderAvailability.objects.select_for_update().get(pk=row.pk)
        result = ResumeResult(provider=provider, was_suspended=row.is_suspended)
        row.state = ProviderState.AVAILABLE
        row.reason_code = ""
        row.technical_detail = ""  # la réponse brute reste dans l'historique (simple_history)
        row.resumed_at = now
        row.resumed_by = user if user is not None and user.is_authenticated else None
        row.blocked_attempts = 0
        row.save()

        today = timezone.localdate()
        held = list(
            Notification.objects.select_for_update()
            .filter(provider=provider, status=NotificationStatus.ON_HOLD)
            .order_by("created_at")
        )
        to_send: list[int] = []
        for notif in held:
            if not requeue or _is_expired_reminder(notif, today):
                notif.status = NotificationStatus.CANCELLED
                notif.error_code = ErrorCode.EXPIRED_ON_HOLD if requeue else notif.error_code
                notif.save(update_fields=["status", "error_code", "updated_at"])
                log_action(
                    notification=notif,
                    action=Actions.CANCEL,
                    actor=user,
                    request=request,
                    metadata={
                        "provider_resumed": True,
                        "reason": "expired" if requeue else "not_requeued",
                    },
                )
                result.expired += 1
                continue
            notif.status = NotificationStatus.QUEUED
            notif.error_code = ""
            notif.error_message = ""
            notif.queued_at = now
            notif.save(
                update_fields=[
                    "status",
                    "error_code",
                    "error_message",
                    "queued_at",
                    "updated_at",
                ]
            )
            log_action(
                notification=notif,
                action=Actions.RETRY,
                actor=user,
                request=request,
                metadata={"provider_resumed": True},
            )
            to_send.append(notif.id)
            result.requeued += 1

    from apps.notifications.tasks import send_notification_task

    for notif_id in to_send:
        transaction.on_commit(lambda nid=notif_id: send_notification_task.delay(nid))
    logger.warning(
        "Fournisseur %s repris par %s — %s renvoyé(s), %s obsolète(s).",
        provider,
        getattr(user, "email", "system"),
        result.requeued,
        result.expired,
    )
    return result
