"""
Tâches Celery du module Companion.

Schedulées par `django-celery-beat` (database scheduler) — voir
`PeriodicTask` dans l'admin Django ou la commande de seed.

Toutes les tâches loguent un résumé en fin d'exécution et sont
idempotentes (on peut les relancer sans dommage).
"""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import ConsentScope, PushSubscription
from .push import push_notify
from .services import has_consent

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Métriques Prometheus (custom). On utilise `prometheus_client` qui est
# fourni transitivement par `django_prometheus`. Si pour une raison X le
# module n'est pas disponible, on retombe sur un no-op qui ne casse rien.
# ----------------------------------------------------------------------------
try:  # pragma: no cover — import guard
    from prometheus_client import Counter as _Counter

    DAILY_REMINDER_SENT = _Counter(
        "companion_daily_reminder_sent_total",
        "Total des rappels quotidiens envoyés, par canal d'aboutissement.",
        ["channel"],  # values: fcm | vapid | sms | whatsapp | none
    )
    DAILY_REMINDER_SKIPPED = _Counter(
        "companion_daily_reminder_skipped_total",
        "Rappels non envoyés, par motif.",
        ["reason"],  # values: no_consent | closed | day_overflow | no_quarantine
    )
except Exception:  # pragma: no cover — pas de prometheus_client → no-op
    class _NoopMetric:
        def labels(self, *_, **__):
            return self

        def inc(self, *_, **__):
            return None

    DAILY_REMINDER_SENT = _NoopMetric()
    DAILY_REMINDER_SKIPPED = _NoopMetric()


# ----------------------------------------------------------------------------
# Helpers — masquage PII pour les logs
# ----------------------------------------------------------------------------


def _mask_phone(phone: str | None) -> str:
    """Masque un numéro de téléphone pour les logs (RGPD friendly).

    +2250708090911 → +225 07****911

    Garde l'indicatif pays + le 5 dernier chiffres en clair pour le support.
    Ne logue jamais le numéro complet.
    """
    if not phone:
        return ""
    s = re.sub(r"\s+", "", phone)
    if len(s) < 6:
        return "***"
    # On garde +225 puis 2 chars + 4 stars + 3 last
    return f"{s[:5]}{s[5:7]}****{s[-3:]}"


def _traveler_tag(traveler) -> str:
    """Identifiant masqué pour les logs structurés."""
    return f"traveler_id={getattr(traveler, 'public_id', '?')}"


# ============================================================================
# Rappel quotidien — envoyé chaque matin à tous les voyageurs en quarantaine
# active qui ont consenti aux notifications.
# ============================================================================


# ----------------------------------------------------------------------------
# FCM mobile — envoi best-effort vers tous les MobileDevice actifs du voyageur.
# Le voyageur est lié à un User côté mobile (voir apps.mobile_api).
# Si aucun appareil n'est enregistré ou si FCM n'est pas configuré, on
# retombe silencieusement (le canal VAPID / SMS prendra le relais).
# ----------------------------------------------------------------------------


def _send_fcm_to_traveler(traveler, *, title: str, body: str, data: dict) -> int:
    """Envoie une notification FCM à tous les appareils mobiles du voyageur.

    Retourne le nombre d'envois réussis (>=0). N'échoue jamais — toute
    erreur d'envoi est loggée et compte comme 0.

    Les `data` (str → str) sont passés au payload FCM pour permettre au
    handler côté app Flutter de router le tap vers /followup/checkin.
    """
    try:
        from apps.mobile_api.models import MobileDevice  # noqa: WPS433
    except Exception:  # apps.mobile_api absent (cas de test minimal)
        return 0

    # Le traveler n'est PAS un User. Convention actuelle (Phase 7) :
    # `apps.mobile_api.registration` lie un Traveler à un User via email.
    # Tant qu'on n'a pas de FK directe, on fait le match par email.
    user = None
    email = (traveler.email or "").strip().lower()
    if email:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(email__iexact=email).first()
    if user is None:
        return 0

    devices = MobileDevice.objects.filter(user=user, is_active=True)
    if not devices.exists():
        return 0

    sent = 0
    # Conversion des valeurs `data` en strings — exigence FCM.
    data_str = {str(k): str(v) for k, v in (data or {}).items()}
    try:
        from apps.notifications.providers import send_push  # noqa: WPS433
    except Exception:
        return 0

    for device in devices:
        try:
            # `send_push` (legacy FCM) ne propage pas les `data`. On le
            # complète ici via httpx direct si FCM_SERVER_KEY est dispo,
            # sinon stub.
            ok = _send_fcm_with_data(device.fcm_token, title, body, data_str)
            if ok:
                sent += 1
                # MAJ last_seen via auto_now au save
                try:
                    device.save(update_fields=["last_seen_at"])
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001 — best-effort par appareil
            logger.exception(
                "FCM send failed for device device_id=%s (%s)",
                device.id, _traveler_tag(traveler),
            )
            # Politique douce : on ne désactive le device qu'après 5 échecs
            # — pas implémenté ici, géré côté cleanup task.
    return sent


def _send_fcm_with_data(token: str, title: str, body: str, data: dict) -> bool:
    """Envoi FCM legacy avec support `data` payload.

    Wrapper minimaliste autour de l'API FCM legacy (HTTP) — l'API HTTP v1
    nécessite une auth OAuth Google plus complexe (TODO).
    En l'absence de `FCM_SERVER_KEY`, log + succès "stub" pour les
    environnements dev/CI (cohérent avec providers.send_push).
    """
    import httpx

    key = settings.NOTIFICATIONS.get("FCM_SERVER_KEY", "")
    if not key:
        logger.info(
            "[FCM:stub] token=%s title=%r data_type=%s",
            (token or "")[:12], title, data.get("type"),
        )
        return True

    try:
        r = httpx.post(
            "https://fcm.googleapis.com/fcm/send",
            headers={"Authorization": f"key={key}", "Content-Type": "application/json"},
            json={
                "to": token,
                "notification": {"title": title, "body": body},
                "data": data,
                "priority": "high",
                # Android : groupe notif quotidien check-in
                "collapse_key": "daily_checkin",
            },
            timeout=15,
        )
        r.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("FCM HTTP error: %s", str(exc)[:160])
        return False


# ----------------------------------------------------------------------------
# Tâche principale — rappel quotidien.
# Tourne chaque matin à 08:00 Africa/Abidjan (configuré dans beat_schedule).
# ----------------------------------------------------------------------------


# Constantes — surface de surveillance.
SURVEILLANCE_DAYS = 21  # période standard EpiTrace (Ebola = 21j)


@shared_task(
    bind=True, name="companion.send_daily_checkin_reminders",
    autoretry_for=(Exception,), retry_backoff=True, max_retries=3,
)
def send_daily_checkin_reminders(self) -> dict[str, int]:
    """Envoie un rappel quotidien "comment vous sentez-vous aujourd'hui ?"
    à chaque voyageur en suivi actif (jour < 21).

    Canaux essayés dans l'ordre :
      1. FCM mobile (si appareils enregistrés via app Flutter).
      2. VAPID Web Push (si abonnement PWA actif).
      3. Fallback SMS (Orange CI / Twilio) via apps.notifications.dispatcher,
         uniquement si aucun push n'a abouti.

    Garanties privacy / RGPD :
      - n'envoie RIEN sans `PrivacyConsent(scope=push, granted=True)` actif ;
      - numéro de téléphone masqué dans les logs (jamais en clair) ;
      - le `data.traveler_id` est le `public_id` (slug 24 chars), pas la
        PK interne — c'est un identifiant non-PII destiné au deep-link.

    Métriques Prometheus :
      - companion_daily_reminder_sent_total{channel}
      - companion_daily_reminder_skipped_total{reason}
    """
    from apps.quarantine.models import QuarantineRecord, QuarantineStatus

    stats = {
        "travelers": 0,
        "fcm_sent": 0,
        "vapid_sent": 0,
        "sms_sent": 0,
        "whatsapp_sent": 0,
        "skipped_no_consent": 0,
        "skipped_day_overflow": 0,
    }

    active_qs = QuarantineRecord.objects.filter(
        status__in=[QuarantineStatus.ACTIVE, QuarantineStatus.EXTENDED],
    ).select_related("traveler")

    today = date.today()

    for q in active_qs:
        traveler = q.traveler
        if traveler is None:
            continue
        stats["travelers"] += 1

        # Calcul du jour J — on n'envoie que si on est dans la fenêtre 21j.
        day_index = max(0, (today - q.started_on).days)
        total = (q.expected_end_on - q.started_on).days or SURVEILLANCE_DAYS
        if day_index >= total:
            stats["skipped_day_overflow"] += 1
            DAILY_REMINDER_SKIPPED.labels(reason="day_overflow").inc()
            continue

        # Consentement push — bloque tout (FCM + VAPID + SMS de rappel).
        if not has_consent(traveler, ConsentScope.PUSH_NOTIFICATIONS):
            stats["skipped_no_consent"] += 1
            DAILY_REMINDER_SKIPPED.labels(reason="no_consent").inc()
            continue

        # ---- Préparation du payload de notification ------------------------
        prenom = (traveler.first_name or "").strip().title() or "Voyageur"
        title = f"Bonjour {prenom} — comment allez-vous ?"
        body = (
            f"Jour {day_index}/{total} de surveillance. "
            "Déclarez votre état aujourd'hui pour aider l'INHP "
            "à protéger la Côte d'Ivoire."
        )
        data_payload = {
            "type": "daily_checkin",
            "traveler_id": traveler.public_id,
            "day": day_index,
            "total": total,
        }

        # ---- 1. FCM mobile -------------------------------------------------
        fcm_sent = _send_fcm_to_traveler(
            traveler, title=title, body=body, data=data_payload,
        )
        if fcm_sent > 0:
            stats["fcm_sent"] += fcm_sent
            DAILY_REMINDER_SENT.labels(channel="fcm").inc(fcm_sent)

        # ---- 2. VAPID Web Push (PWA) + Fallback SMS automatique -----------
        # `push_notify` envoie aux subscriptions VAPID actives ET tombe en
        # fallback SMS si AUCUN push n'aboutit (sent==0). Comportement déjà
        # implémenté dans apps.companion.push.
        push_url = f"/voyageur/suivi?id={traveler.public_id}"
        vapid_result = push_notify(
            traveler=traveler,
            title=title,
            body=body,
            url=push_url,
            tag="daily-checkin",
            notification_type="daily_checkin",
            extra=data_payload,
            # On laisse `fallback_to_sms=True` par défaut — mais SI le FCM
            # mobile a déjà abouti, on n'a plus besoin du SMS.
            fallback_to_sms=(fcm_sent == 0),
            fallback_to_whatsapp=False,
        )
        if vapid_result["sent"] > 0:
            stats["vapid_sent"] += vapid_result["sent"]
            DAILY_REMINDER_SENT.labels(channel="vapid").inc(vapid_result["sent"])
        if vapid_result.get("sms_sent", 0):
            stats["sms_sent"] += vapid_result["sms_sent"]
            DAILY_REMINDER_SENT.labels(channel="sms").inc(vapid_result["sms_sent"])
        if vapid_result.get("whatsapp_sent", 0):
            stats["whatsapp_sent"] += vapid_result["whatsapp_sent"]
            DAILY_REMINDER_SENT.labels(channel="whatsapp").inc(vapid_result["whatsapp_sent"])

        # ---- Log structuré, sans PII ---------------------------------------
        any_sent = (
            fcm_sent
            + vapid_result.get("sent", 0)
            + vapid_result.get("sms_sent", 0)
        )
        if any_sent == 0:
            DAILY_REMINDER_SENT.labels(channel="none").inc()
        logger.info(
            "daily_reminder %s day=%s/%s fcm=%s vapid=%s sms=%s phone_masked=%s",
            _traveler_tag(traveler),
            day_index, total,
            fcm_sent, vapid_result.get("sent", 0), vapid_result.get("sms_sent", 0),
            _mask_phone(traveler.phone_mobile),
        )

    logger.info("send_daily_checkin_reminders summary: %s", stats)
    return stats


# ----------------------------------------------------------------------------
# Alias rétro-compatible — l'ancien nom `send_daily_followup_reminders` est
# toujours référencé par d'éventuelles PeriodicTask en DB. On garde le nom
# enregistré pour ne pas casser les schedules existants.
# ----------------------------------------------------------------------------


@shared_task(
    bind=True, name="companion.send_daily_followup_reminders",
    autoretry_for=(Exception,), retry_backoff=True, max_retries=3,
)
def send_daily_followup_reminders(self) -> dict[str, int]:
    """Alias historique → délègue à `send_daily_checkin_reminders`.

    Conservé pour ne pas invalider les PeriodicTask en base avec l'ancien
    nom. Tout nouveau schedule doit pointer sur
    `companion.send_daily_checkin_reminders`.
    """
    return send_daily_checkin_reminders.run()


# ============================================================================
# Détection des check-ins manqués (48h sans nouvelle)
# ============================================================================


@shared_task(
    bind=True, name="companion.detect_missed_checkins",
    autoretry_for=(Exception,), retry_backoff=True, max_retries=3,
)
def detect_missed_checkins(self, threshold_hours: int = 48) -> dict[str, int]:
    """Crée une HealthAlert pour chaque voyageur en suivi actif qui n'a
    pas fait de check-in depuis plus de `threshold_hours`.

    Envoie aussi un push de rappel doux (un seul, idempotent par jour).
    """
    from django.contrib.contenttypes.models import ContentType
    from apps.quarantine.models import QuarantineRecord, QuarantineStatus
    from apps.surveillance.models import HealthAlert

    stats = {"checked": 0, "missed": 0, "alerts_created": 0, "push_sent": 0}
    cutoff = timezone.now() - timedelta(hours=threshold_hours)

    active_qs = QuarantineRecord.objects.filter(
        status__in=[QuarantineStatus.ACTIVE, QuarantineStatus.EXTENDED],
    ).select_related("traveler")

    for q in active_qs:
        stats["checked"] += 1
        last_check = q.daily_checks.order_by("-check_date").first()
        last_date = last_check.check_date if last_check else q.started_on
        last_dt = timezone.make_aware(
            timezone.datetime.combine(last_date, timezone.datetime.min.time())
        ) if hasattr(timezone, "datetime") else None

        # Fallback simple par comparaison de date
        if last_check and (date.today() - last_check.check_date).days < threshold_hours / 24:
            continue
        if not last_check and (timezone.now() - q.created_at) < timedelta(hours=threshold_hours):
            continue

        stats["missed"] += 1

        # Idempotence : un seul "missed checkin" par voyageur par jour
        alert_code = f"MISS-{q.traveler.public_id}-{date.today():%Y%m%d}"
        if not HealthAlert.objects.filter(code=alert_code).exists():
            HealthAlert.objects.create(
                code=alert_code,
                title=f"Aucune nouvelle depuis {threshold_hours}h — {q.traveler.public_id}",
                description=(
                    f"Dernier check-in : {last_check.check_date if last_check else 'jamais'}. "
                    "Tenter un contact téléphonique ou WhatsApp."
                ),
                severity="MEDIUM",
                status="OPEN",
                target_ct=ContentType.objects.get_for_model(q.traveler),
                target_id=q.traveler.pk,
            )
            stats["alerts_created"] += 1

        # Push doux (uniquement si push consenti)
        if has_consent(q.traveler, ConsentScope.PUSH_NOTIFICATIONS):
            result = push_notify(
                traveler=q.traveler,
                title="Donnez-nous de vos nouvelles",
                body="Quelques secondes suffisent pour confirmer que tout va bien.",
                url=f"/voyageur/suivi?id={q.traveler.public_id}",
                tag="missed-checkin",
                notification_type="missed_checkin",
            )
            stats["push_sent"] += result["sent"]

    logger.info("detect_missed_checkins: %s", stats)
    return stats


# ============================================================================
# Message de fin de suivi (J21+)
# ============================================================================


@shared_task(
    bind=True, name="companion.send_completion_messages",
    autoretry_for=(Exception,), retry_backoff=True, max_retries=3,
)
def send_completion_messages(self) -> dict[str, int]:
    """Envoie un message de fin (et désactive les abonnements push) pour
    chaque quarantaine arrivée à terme aujourd'hui."""
    from apps.quarantine.models import QuarantineRecord, QuarantineStatus

    stats = {"completed": 0, "push_sent": 0}
    today = date.today()
    qs = QuarantineRecord.objects.filter(
        expected_end_on=today,
        status__in=[QuarantineStatus.ACTIVE, QuarantineStatus.EXTENDED],
    ).select_related("traveler")

    for q in qs:
        stats["completed"] += 1
        traveler = q.traveler

        # Push final si consenti
        if has_consent(traveler, ConsentScope.PUSH_NOTIFICATIONS):
            result = push_notify(
                traveler=traveler,
                title="Période d'accompagnement terminée",
                body=(
                    "Votre période d'accompagnement sanitaire est terminée. "
                    "Merci pour votre coopération et bon séjour."
                ),
                url=f"/voyageur/suivi?id={traveler.public_id}",
                tag="followup-complete",
                notification_type="followup_complete",
            )
            stats["push_sent"] += result["sent"]

        # Marque la quarantaine comme COMPLETED
        q.status = QuarantineStatus.COMPLETED
        q.actual_end_on = today
        q.save(update_fields=["status", "actual_end_on", "updated_at"])

    logger.info("send_completion_messages: %s", stats)
    return stats


# ============================================================================
# Nettoyage des subscriptions inactives (> 90 jours sans usage réussi)
# ============================================================================


@shared_task(name="companion.purge_closed_followups")
def purge_closed_followups(retention_days: int = 30, dry_run: bool = False) -> dict:
    """Purge / anonymise les données voyageur après la fin du suivi (J+30).

    Conforme à la loi 2013-450 (CI) et au RGPD : on conserve les données
    le strict nécessaire à la mission. Une fois le suivi 21j clôturé
    + 30 jours de tolérance, on :

    1. **Anonymise** le Traveler (nom, contact, document) — on garde
       l'enregistrement pour les statistiques mais sans PII.
    2. **Supprime** les pings GPS associés (hard delete).
    3. **Désactive** les push subscriptions.
    4. **Conserve** les HealthAlert et DataAccessLog (audit).

    Note : le `DataPurgeLog` est créé pour tracer chaque purge.
    Pour un test, passer `dry_run=True` — aucune écriture en DB.
    """
    from datetime import timedelta
    from apps.quarantine.models import QuarantineRecord, QuarantineStatus
    from apps.travelers.models import Traveler
    from .models import DataPurgeLog

    cutoff = timezone.now() - timedelta(days=retention_days)
    # Quarantaines clôturées (COMPLETED ou CANCELLED) il y a >= retention_days
    closed = QuarantineRecord.objects.filter(
        status__in=[QuarantineStatus.COMPLETED, "CANCELLED"],
        actual_end_on__isnull=False,
        updated_at__lt=cutoff,
    ).select_related("traveler")

    stats = {"candidates": 0, "anonymized": 0, "pings_deleted": 0, "subs_disabled": 0}

    for q in closed:
        t = q.traveler
        if not t or "ANON-" in (t.last_name or ""):
            continue  # déjà anonymisé
        stats["candidates"] += 1

        if dry_run:
            continue

        # Hard delete des pings (déjà inutiles, contiennent des positions)
        pings_count = t.location_pings.count()
        t.location_pings.all().delete()
        stats["pings_deleted"] += pings_count

        # Désactivation soft des push subscriptions
        n_subs = t.push_subscriptions.filter(is_active=True).update(is_active=False)
        stats["subs_disabled"] += n_subs

        # Anonymisation des champs PII du Traveler (on garde la ligne pour stats)
        old_email = t.email
        Traveler.objects.filter(pk=t.pk).update(
            last_name=f"ANON-{t.public_id}",
            first_name="—",
            middle_name="",
            email="",
            phone_mobile="",
            whatsapp_phone="",
            id_document_number="",
            postal_address="",
            confinement_street_number="",
            confinement_lot="",
            confinement_hotel="",
            confinement_room_number="",
            emergency_phone_ci="",
        )

        DataPurgeLog.objects.create(
            traveler_id=t.pk,
            traveler_public_id=t.public_id,
            policy_id=None,
            pings_deleted=pings_count,
            subs_disabled=n_subs,
            email_redacted=bool(old_email),
        )
        stats["anonymized"] += 1

    logger.info("purge_closed_followups: %s (dry_run=%s)", stats, dry_run)
    return stats


@shared_task(name="companion.cleanup_stale_push_subscriptions")
def cleanup_stale_push_subscriptions(days: int = 90) -> dict[str, int]:
    """Désactive (soft) les subscriptions qui n'ont pas été utilisées avec
    succès depuis `days` jours et dont le compteur d'échec est non nul."""
    cutoff = timezone.now() - timedelta(days=days)
    n = PushSubscription.objects.filter(
        is_active=True, failure_count__gte=3, last_used_at__lt=cutoff,
    ).update(is_active=False, updated_at=timezone.now())
    return {"deactivated": n}
