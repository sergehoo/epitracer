"""Garde anti SMS pumping — appliquée à CHAQUE SMS dans le dispatcher.

Ordre des contrôles (avant création de la Notification) :
  1. indicatif international autorisé (liste blanche optionnelle) ;
  2. quotas par numéro E.164 (heure + jour), selon la priorité :
     `otp` (strict), `standard`, `urgent` (plafond dédié, jamais illimité) ;
  3. quota par voyageur et par jour (hors urgences) ;
  4. urgences : enveloppe journalière dédiée, hors budget standard ;
     autres : plafond journalier par fournisseur + budget global
     journalier/mensuel. Dépassement → coupe-circuit (fournisseur(s)
     suspendus, alerte admin) : le message est conservé en attente,
     aucune dépense supplémentaire avant reprise par un administrateur ;
  5. détection de pics sur le trafic international (journal + alerte).

Compteurs : `INCR` Redis atomiques (aucun dépassement en concurrence) ;
les compteurs journaliers/mensuels sont initialisés depuis la base, et la
base sert de repli si Redis est indisponible.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from django.conf import settings
from django.core.cache import cache
from django.db.models import Case, F, IntegerField, Sum, Value, When
from django.db.models.functions import Length
from django.utils import timezone

from apps.core.ratelimit import fingerprint
from apps.notifications.models import (
    Channel,
    MessageType,
    Notification,
    NotificationStatus,
    Provider,
)

from . import availability
from .errors import ErrorCode
from .security import SecurityEventKind, alert_admins, log_security_event, mask_phone

logger = logging.getLogger("epidemitracker.notifications.sms_guard")

SMS_PROVIDERS = (Provider.ORANGE_CI, Provider.TWILIO)


class SmsPriority:
    URGENT = "urgent"
    OTP = "otp"
    STANDARD = "standard"


def sms_segments(body: str) -> int:
    """SMS facturés : 1 jusqu'à 160 caractères, puis 153 par segment."""
    n = len(body or "")
    return 1 if n <= 160 else -(-n // 153)


def priority_for(message_type: str, metadata: dict | None) -> str:
    meta = metadata or {}
    if message_type == MessageType.OTP or meta.get("kind") == "otp":
        return SmsPriority.OTP
    if (
        message_type in availability.URGENT_MESSAGE_TYPES
        or meta.get("urgent")
        or meta.get("kind") in availability.URGENT_KINDS
    ):
        return SmsPriority.URGENT
    return SmsPriority.STANDARD


@dataclass
class GuardDecision:
    allowed: bool
    priority: str = SmsPriority.STANDARD
    segments: int = 1
    error_code: str = ""
    message: str = ""
    reservations: list = field(default_factory=list)

    def release(self) -> None:
        """Annule les réservations (message finalement non créé)."""
        for key, amount in self.reservations:
            try:
                cache.decr(key, amount)
            except ValueError:
                pass
        self.reservations = []


# ---------------------------------------------------------------------------
# Compteurs
# ---------------------------------------------------------------------------
def _cfg() -> dict:
    return getattr(settings, "SMS_GUARD", {}) or {}


def _periods() -> dict[str, str]:
    now = timezone.localtime()
    return {
        "hour": now.strftime("%Y%m%d%H"),
        "day": now.strftime("%Y%m%d"),
        "month": now.strftime("%Y%m"),
    }


_TTL = {"hour": 3600 + 60, "day": 86400 + 600, "month": 32 * 86400}
_PERIOD_LABELS = {"day": "journalier", "month": "mensuel"}


def _sms_today():
    start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    return Notification.all_objects.filter(channel=Channel.SMS, created_at__gte=start).exclude(
        status=NotificationStatus.CANCELLED,
    )


def _segments_sum(qs) -> int:
    agg = qs.annotate(blen=Length("body")).aggregate(
        n=Sum(
            Case(
                When(blen__lte=160, then=Value(1)),
                default=(F("blen") + 152) / 153,
                output_field=IntegerField(),
            )
        )
    )
    return int(agg["n"] or 0)


def _incr(key: str, period: str, amount: int, seed=None) -> int | None:
    """INCR atomique ; `seed()` initialise un compteur absent depuis la base."""
    full_key = f"smsg:{key}"
    if seed is not None and cache.get(full_key) is None:
        try:
            cache.add(full_key, int(seed()), timeout=_TTL[period])
        except Exception:  # noqa: BLE001 — un seed raté ne bloque pas
            logger.exception("Initialisation du compteur %s impossible", key)
    for _ in range(2):
        added = cache.add(full_key, 0, timeout=_TTL[period])
        if added is None:
            return None
        try:
            value = cache.incr(full_key, amount)
        except ValueError:
            continue
        return None if value is None else int(value)
    return None


class _Reserver:
    def __init__(self, decision: GuardDecision):
        self.decision = decision

    def take(
        self, key: str, period: str, amount: int, limit: int, *, seed=None, fallback=None
    ) -> bool:
        if not limit:
            return True
        count = _incr(key, period, amount, seed)
        if count is None:
            # Redis indisponible : décision prise sur la base (fail safe).
            current = int(fallback()) if fallback else 0
            return current + amount <= limit
        self.decision.reservations.append((f"smsg:{key}", amount))
        return count <= limit

    def undo_last(self) -> None:
        if self.decision.reservations:
            key, amount = self.decision.reservations.pop()
            try:
                cache.decr(key, amount)
            except ValueError:
                pass


_REFUSALS = {
    ErrorCode.SMS_QUOTA_EXCEEDED: (
        "Limite d'envoi SMS atteinte pour ce destinataire. Réessayez plus tard."
    ),
    ErrorCode.URGENT_CAP: "Plafond des SMS urgents atteint : contacter l'administrateur national.",
    ErrorCode.COUNTRY_BLOCKED: "Envoi SMS non autorisé vers ce pays.",
}


def _refuse(
    decision: GuardDecision,
    code: str,
    kind: str,
    *,
    phone: str,
    traveler,
    source: str,
    details: dict,
) -> GuardDecision:
    decision.release()
    decision.allowed = False
    decision.error_code = code
    decision.message = _REFUSALS[code]
    log_security_event(
        kind,
        source=source or "dispatcher",
        phone=phone,
        traveler=traveler,
        details=details,
        dedupe=f"{kind}:{phone}:{details.get('rule', '')}",
    )
    return decision


def _calling_code_allowed(phone: str) -> bool:
    codes = [
        c.strip().lstrip("+") for c in (_cfg().get("ALLOWED_CALLING_CODES") or []) if c.strip()
    ]
    if not codes or phone.startswith("+225"):
        return True
    return any(phone[1:].startswith(code) for code in codes)


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------
def check_and_reserve(
    *,
    phone: str,
    provider: str,
    body: str,
    message_type: str,
    metadata: dict | None = None,
    traveler=None,
    source: str = "",
) -> GuardDecision:
    cfg = _cfg()
    decision = GuardDecision(
        allowed=True,
        priority=priority_for(message_type, metadata),
        segments=sms_segments(body),
    )
    if not cfg.get("ENABLED", True) or not phone:
        return decision
    context = {"phone": phone, "traveler": traveler, "source": source}

    if not _calling_code_allowed(phone):
        return _refuse(
            decision,
            ErrorCode.COUNTRY_BLOCKED,
            SecurityEventKind.COUNTRY_BLOCKED,
            details={"rule": "calling_code"},
            **context,
        )

    p = _periods()
    r = _Reserver(decision)
    for rule in _recipient_rules(decision, cfg, phone=phone, traveler=traveler, periods=p):
        key, period, limit, seed, kind, details = rule
        if not r.take(key, period, 1, limit, seed=seed, fallback=seed):
            return _refuse(
                decision,
                ErrorCode.SMS_QUOTA_EXCEEDED,
                kind,
                details={**details, "limit": limit},
                **context,
            )

    if decision.priority == SmsPriority.URGENT:
        return _reserve_urgent(decision, r, cfg, periods=p, context=context)

    if not availability.is_suspended(provider):
        _check_budget(decision, r, provider=provider, phone=phone, source=source, periods=p)
    _detect_spike(phone=phone, provider=provider, source=source, periods=p)
    return decision


def _recipient_rules(decision: GuardDecision, cfg: dict, *, phone: str, traveler, periods: dict):
    """Quotas par numéro (heure, jour) puis par voyageur (jour, hors urgences)."""
    ph = fingerprint(phone)
    hour_limit, day_limit = cfg["PER_NUMBER"][decision.priority]

    def number_today() -> int:
        return _sms_today().filter(normalized_phone=phone).count()

    base = {"priority": decision.priority}
    rules = [
        (
            f"num:{decision.priority}:{ph}:{periods['hour']}",
            "hour",
            hour_limit,
            None,
            SecurityEventKind.NUMBER_QUOTA,
            {**base, "rule": "number_hour"},
        ),
        (
            f"num:{decision.priority}:{ph}:{periods['day']}",
            "day",
            day_limit,
            number_today,
            SecurityEventKind.NUMBER_QUOTA,
            {**base, "rule": "number_day"},
        ),
    ]
    if getattr(traveler, "pk", None) and decision.priority != SmsPriority.URGENT:

        def traveler_today() -> int:
            return _sms_today().filter(traveler_id=traveler.pk).count()

        rules.append(
            (
                f"trv:{traveler.pk}:{periods['day']}",
                "day",
                cfg.get("PER_TRAVELER_DAY", 0),
                traveler_today,
                SecurityEventKind.TRAVELER_QUOTA,
                {"rule": "traveler_day"},
            )
        )
    return rules


def _reserve_urgent(
    decision: GuardDecision, r: _Reserver, cfg: dict, *, periods: dict, context: dict
) -> GuardDecision:
    """Urgences médicales : enveloppe journalière dédiée, jamais illimitée."""
    limit = cfg.get("URGENT_DAILY", 0)
    if r.take(f"urgent:{periods['day']}", "day", decision.segments, limit):
        return decision
    refused = _refuse(
        decision,
        ErrorCode.URGENT_CAP,
        SecurityEventKind.URGENT_CAP,
        details={"rule": "urgent_daily", "limit": limit},
        **context,
    )
    alert_admins(
        "[EpiTrace] Plafond des SMS urgents atteint",
        f"L'enveloppe journalière des SMS médicaux urgents ({limit} SMS) est épuisée. "
        "Les alertes urgentes suivantes ne partent plus par SMS (email maintenu). "
        "Vérifier l'activité puis ajuster SMS_URGENT_DAILY si nécessaire.",
        kind="urgent_cap",
        once_key=f"urgent_cap:{periods['day']}",
        once_window=86400,
    )
    return refused


def _check_budget(
    decision: GuardDecision, r: _Reserver, *, provider: str, phone: str, source: str, periods: dict
) -> None:
    """Plafond fournisseur + budget global. Dépassement → coupe-circuit."""
    cfg = _cfg()
    seg = decision.segments

    def provider_today() -> int:
        return _segments_sum(_sms_today().filter(provider=provider))

    def budget_today() -> int:
        return _segments_sum(_sms_today())

    def budget_month() -> int:
        start = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return _segments_sum(
            Notification.all_objects.filter(
                channel=Channel.SMS,
                created_at__gte=start,
            ).exclude(status=NotificationStatus.CANCELLED)
        )

    cap = (cfg.get("PER_PROVIDER_DAY") or {}).get(provider, 0)
    if not r.take(
        f"prov:{provider}:{periods['day']}",
        "day",
        seg,
        cap,
        seed=provider_today,
        fallback=provider_today,
    ):
        r.undo_last()
        _trip(
            decision,
            [provider],
            kind=SecurityEventKind.PROVIDER_CAP,
            phone=phone,
            source=source,
            detail=f"Plafond journalier {provider} atteint ({cap} SMS).",
        )
        return

    for period, limit, seed in (
        ("day", cfg.get("BUDGET_DAILY", 0), budget_today),
        ("month", cfg.get("BUDGET_MONTHLY", 0), budget_month),
    ):
        key = f"budget:{periods[period]}"
        if not r.take(key, period, seg, limit, seed=seed, fallback=seed):
            r.undo_last()
            _trip(
                decision,
                list(SMS_PROVIDERS),
                kind=SecurityEventKind.BUDGET_EXCEEDED,
                phone=phone,
                source=source,
                detail=f"Budget SMS {_PERIOD_LABELS[period]} atteint ({limit} SMS).",
            )
            return
        _maybe_alert_threshold(period, key, limit)


def _maybe_alert_threshold(period: str, key: str, limit: int) -> None:
    ratio = _cfg().get("ALERT_RATIO", 0.8)
    if not limit or not ratio:
        return
    current = cache.get(f"smsg:{key}")
    if current is None or int(current) < int(limit * ratio):
        return
    label = "journalier" if period == "day" else "mensuel"
    if cache.add(f"smsg:alerted:{key}", 1, timeout=_TTL[period]) is False:
        return
    log_security_event(
        SecurityEventKind.BUDGET_ALERT,
        source="budget",
        details={"period": period, "used": int(current), "limit": limit},
    )
    alert_admins(
        f"[EpiTrace] Budget SMS {label} à {int(ratio * 100)} %",
        f"Consommation SMS : {int(current)} / {limit} (budget {label}). Au-delà du plafond, "
        "les envois non urgents seront suspendus jusqu'à décision d'un administrateur.",
        kind="budget_alert",
    )


def _trip(
    decision: GuardDecision,
    providers: list[str],
    *,
    kind: str,
    phone: str,
    source: str,
    detail: str,
) -> None:
    """Coupe-circuit : suspend le(s) fournisseur(s) ; le message sera retenu."""
    for prov in providers:
        availability.suspend_provider(prov, reason_code=ErrorCode.BUDGET_EXCEEDED, detail=detail)
    log_security_event(
        kind,
        source=source or "dispatcher",
        phone=phone,
        details={"detail": detail, "providers": providers},
        dedupe=f"{kind}:{','.join(providers)}",
        dedupe_window=3600,
    )
    decision.error_code = ErrorCode.BUDGET_EXCEEDED


def _detect_spike(*, phone: str, provider: str, source: str, periods: dict) -> None:
    """Pic de trafic international (signature typique du SMS pumping)."""
    if phone.startswith("+225"):
        return
    cfg = _cfg()
    hour = periods["hour"]
    prefix = phone[:6]
    for key, limit, scope in (
        (f"spike:pfx:{prefix}:{hour}", cfg.get("SPIKE_INTL_PREFIX_HOUR", 0), f"préfixe {prefix}"),
        (f"spike:intl:{hour}", cfg.get("SPIKE_INTL_TOTAL_HOUR", 0), "international"),
    ):
        if not limit:
            continue
        count = _incr(key, "hour", 1)
        if count is None or count != limit + 1:
            continue
        log_security_event(
            SecurityEventKind.SPIKE,
            source=source or "dispatcher",
            phone=phone,
            details={"scope": scope, "count": count, "limit_per_hour": limit, "provider": provider},
        )
        alert_admins(
            "[EpiTrace] Pic anormal de SMS internationaux",
            f"Plus de {limit} SMS internationaux en une heure ({scope}). Signature possible "
            "de SMS pumping : vérifier les inscriptions récentes et le journal des événements "
            f"de sécurité. Dernier destinataire : {mask_phone(phone)}.",
            kind="sms_spike",
            once_key=f"spike:{scope}:{hour}",
        )
