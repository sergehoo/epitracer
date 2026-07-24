"""Settings de production - sécurité durcie, observabilité activée."""
from __future__ import annotations

import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

# Sécurité durcie (overridable via env mais valeurs strictes par défaut)
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)  # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_SAMESITE = "Strict"

# ---------------------------------------------------------------------------
# CSP — en prod : ENFORCE (pas report-only) par défaut. On garde report-uri
# en option pour collecter les violations résiduelles dans Sentry / endpoint
# custom. Override via env CSP_REPORT_ONLY=true permet un rollback à chaud
# sans redéploiement.
# ---------------------------------------------------------------------------
CSP_REPORT_ONLY = env.bool("CSP_REPORT_ONLY", default=False)

# Sentry
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(transaction_style="url"),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.05),
        send_default_pii=False,
        environment=env("SENTRY_ENVIRONMENT", default="production"),
    )

# OpenTelemetry auto-instrumentation (activée si endpoint défini)
OTEL_EXPORTER_OTLP_ENDPOINT = env("OTEL_EXPORTER_OTLP_ENDPOINT", default="")
if OTEL_EXPORTER_OTLP_ENDPOINT:
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.django import DjangoInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": env("OTEL_SERVICE_NAME", default="epidemitracker-api")})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT)))
        trace.set_tracer_provider(provider)
        DjangoInstrumentor().instrument()
    except Exception:  # pragma: no cover - opt-in best effort
        pass


# ---------------------------------------------------------------------------
# Hard checks Telegram — D-01 (ostack:challenge)
# ---------------------------------------------------------------------------
# Refuse le boot en prod si TELEGRAM_BOT_TOKEN est configuré mais que le
# secret webhook est vide. Sans ce secret, N'IMPORTE QUI peut POST au webhook
# et créer/rebrander des TelegramSubscription frauduleuses (hijacking).
#
# Politique : soit le bot est totalement désactivé (token vide → pas de webhook
# exposé), soit il est activé ET protégé par un secret ≥ 32 caractères.
# ---------------------------------------------------------------------------
from django.core.exceptions import ImproperlyConfigured  # noqa: E402

if TELEGRAM_BOT_TOKEN:
    if not TELEGRAM_WEBHOOK_SECRET:
        raise ImproperlyConfigured(
            "TELEGRAM_WEBHOOK_SECRET est obligatoire en production dès lors que "
            "TELEGRAM_BOT_TOKEN est défini. Sans lui, le webhook /api/v1/telegram/"
            "webhook/ accepte n'importe quel POST — risque de hijacking des "
            "abonnements voyageur. Générer un secret : "
            "python -c \"import secrets;print(secrets.token_urlsafe(48))\" "
            "puis l'ajouter au .env de prod."
        )
    if len(TELEGRAM_WEBHOOK_SECRET) < 32:
        raise ImproperlyConfigured(
            f"TELEGRAM_WEBHOOK_SECRET trop court ({len(TELEGRAM_WEBHOOK_SECRET)} "
            "caractères). Minimum 32 recommandé (48+ optimal)."
        )
