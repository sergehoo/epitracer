"""Métriques Prometheus du sous-module rapports automatisés.

Import safe : si prometheus_client absent (dev env minimal), tous les
compteurs deviennent des no-op → aucun crash.

Exposé automatiquement via django-prometheus si branché (voir
config/urls.py — endpoint /metrics/).

Convention : préfixe `epitrace_reports_` pour disambiguer parmi les autres
apps qui exportent aussi vers le même endpoint.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Shim safe — no-op si prometheus_client absent
# ---------------------------------------------------------------------------
try:
    from prometheus_client import Counter, Gauge, Histogram

    _AVAILABLE = True
except ImportError:  # pragma: no cover
    _AVAILABLE = False

    class _NoOp:
        def __init__(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            pass

        def set(self, *args, **kwargs):
            pass

        def observe(self, *args, **kwargs):
            pass

    Counter = Gauge = Histogram = _NoOp  # type: ignore


# ---------------------------------------------------------------------------
# 7 métriques (respect strict de la spec § 12)
# ---------------------------------------------------------------------------

# Génération
REPORTS_GENERATED_TOTAL = Counter(
    "epitrace_reports_generated_total",
    "Nombre total de rapports générés avec succès",
    ["report_type"],
)
REPORTS_FAILED_TOTAL = Counter(
    "epitrace_reports_failed_total",
    "Nombre total d'échecs de génération",
    ["report_type", "reason"],
)
REPORT_GENERATION_DURATION = Histogram(
    "epitrace_report_generation_duration_seconds",
    "Durée de génération complète (agg + PDF + Excel)",
    ["report_type"],
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300),
)

# Envois
REPORT_SMS_SENT_TOTAL = Counter(
    "epitrace_report_sms_sent_total",
    "SMS de rapport envoyés",
    ["report_type", "provider"],
)
REPORT_EMAIL_SENT_TOTAL = Counter(
    "epitrace_report_email_sent_total",
    "Emails de rapport envoyés",
    ["report_type"],
)
REPORT_DELIVERY_FAILED_TOTAL = Counter(
    "epitrace_report_delivery_failed_total",
    "Échecs de livraison (avant retry)",
    ["report_type", "channel", "reason"],
)

# Destinataires
REPORT_RECIPIENTS_TOTAL = Gauge(
    "epitrace_report_recipients_total",
    "Nombre de destinataires actifs",
    ["preferred_channel"],
)


# ---------------------------------------------------------------------------
# Helpers pour maintenir la Gauge des destinataires actifs
# ---------------------------------------------------------------------------
def refresh_recipients_gauge() -> None:
    """Recalcule la Gauge REPORT_RECIPIENTS_TOTAL depuis la DB.

    À appeler dans une tâche Celery périodique (ex. horaire) pour que la
    Gauge reflète l'état réel — les Counter s'incrémentent seuls dans les
    tasks, mais la Gauge doit être rafraîchie explicitement.
    """
    if not _AVAILABLE:
        return
    try:
        from .models import AutomatedReportRecipient, PreferredChannel
        counts = {
            PreferredChannel.SMS: 0,
            PreferredChannel.EMAIL: 0,
            PreferredChannel.BOTH: 0,
        }
        rows = (
            AutomatedReportRecipient.objects
            .filter(is_active=True, consent_date__isnull=False)
            .values_list("preferred_channel", flat=True)
        )
        for ch in rows:
            counts[ch] = counts.get(ch, 0) + 1
        for ch, cnt in counts.items():
            REPORT_RECIPIENTS_TOTAL.labels(preferred_channel=ch).set(cnt)
    except Exception:  # noqa: BLE001
        # Best-effort : ne jamais planter le worker à cause d'une métrique
        pass


def is_prometheus_available() -> bool:
    """Utilitaire pour les tests + health checks."""
    return _AVAILABLE
