"""Idempotence des envois automatiques (rappels, relances, fin de suivi).

Deux verrous complémentaires, tous deux portés par des contraintes d'unicité
PostgreSQL (donc valables entre workers Celery concurrents) :

  - `claim_reminder()` réserve « un rappel <kind> pour ce voyageur ce jour-là »
    AVANT tout envoi, tous canaux confondus (FCM, Web Push, SMS) ;
  - `reminder_dedup_key()` alimente `Notification.dedup_key` pour qu'un même
    SMS de rappel ne soit jamais enregistré deux fois (redélivrance de tâche).

Les messages manuels et les alertes médicales urgentes n'utilisent ni l'un ni
l'autre : ils ne sont jamais bloqués.
"""

from __future__ import annotations

from datetime import date

from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from apps.notifications.models import ReminderDispatch


class ReminderKind:
    DAILY_CHECKIN = "daily_checkin"
    MISSED_CHECKIN = "missed_checkin"
    FOLLOWUP_COMPLETE = "followup_complete"


def reminder_dedup_key(kind: str, traveler_id: int, on_date: date, channel: str) -> str:
    return f"{kind}:{traveler_id}:{on_date:%Y%m%d}:{channel}"[:120]


def claim_reminder(traveler, kind: str, on_date: date | None = None) -> bool:
    """Réserve l'envoi d'un rappel. False si déjà envoyé (doublon évité)."""
    on_date = on_date or timezone.localdate()
    try:
        with transaction.atomic():
            ReminderDispatch.objects.create(
                traveler=traveler,
                kind=kind,
                reminder_date=on_date,
            )
        return True
    except IntegrityError:
        ReminderDispatch.all_objects.filter(
            traveler=traveler,
            kind=kind,
            reminder_date=on_date,
        ).update(
            duplicates_avoided=F("duplicates_avoided") + 1,
            last_duplicate_at=timezone.now(),
        )
        return False
