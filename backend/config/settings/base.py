"""
Settings de base d'EpidemiTracker.

Les settings sont découpés en :
- base.py  : commun à tous les environnements
- dev.py   : développement local
- prod.py  : production (HTTPS, sécurité durcie, observabilité)
- test.py  : pytest (DB en mémoire si possible, providers stub)

Toutes les variables sensibles passent par les variables d'environnement
(.env via django-environ) — aucune valeur secrète n'est commitée.
"""
from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import environ

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # /app
APPS_DIR = BASE_DIR / "apps"

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DJANGO_CSRF_TRUSTED_ORIGINS=(list, []),
    SECURE_SSL_REDIRECT=(bool, False),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
    SECURE_HSTS_SECONDS=(int, 0),
)
# Lecture du .env (présent en dev/CI, absent en prod où on injecte via env runtime)
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

# ---------------------------------------------------------------------------
# Core Django
# ---------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-in-prod")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.contrib.gis",  # PostGIS / GeoDjango
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "django_extensions",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "django_celery_beat",
    "django_celery_results",
    "django_prometheus",
    "channels",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "guardian",
    "simple_history",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.audit",
    "apps.geo",
    "apps.diseases",
    "apps.forms",
    "apps.travelers",
    "apps.ebola",
    "apps.scoring",
    "apps.health_pass",
    "apps.quarantine",
    "apps.surveillance",
    "apps.notifications",
    "apps.realtime",
    "apps.analytics",
    "apps.companion",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    # CORS DOIT être tout en haut, AVANT les autres middlewares qui
    # peuvent produire une réponse (Prometheus, Security, etc.). Sinon
    # la preflight OPTIONS peut être interceptée et renvoyée sans les
    # headers Access-Control-* attendus par le navigateur.
    "corsheaders.middleware.CorsMiddleware",
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "apps.audit.middleware.AuditContextMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database (Postgres + PostGIS)
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        default="postgis://postgres:postgres@db:5433/epidemiebola",
    )
}
# Force engine PostGIS
DATABASES["default"]["ENGINE"] = "django.contrib.gis.db.backends.postgis"
DATABASES["default"]["CONN_MAX_AGE"] = 60

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = (
    "django.contrib.auth.backends.ModelBackend",
    "guardian.backends.ObjectPermissionBackend",
)
ANONYMOUS_USER_NAME = "AnonymousUser"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
# Hashage robuste : Argon2 en premier
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

# ---------------------------------------------------------------------------
# i18n / TZ
# ---------------------------------------------------------------------------
LANGUAGE_CODE = env("DJANGO_LANGUAGE_CODE", default="fr-fr")
TIME_ZONE = env("DJANGO_TIME_ZONE", default="Africa/Abidjan")
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

# ---------------------------------------------------------------------------
# Static / Media
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
FILE_UPLOAD_PERMISSIONS = 0o644

# ---------------------------------------------------------------------------
# DRF
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "user": "1000/min",
        "anon": "60/min",
        "login": "10/min",
        "qr_verify": "300/min",
        # Companion : limites généreuses pour la PWA, plus serrées
        # sur les pings de localisation pour éviter le tracking abusif.
        "companion_checkin": "12/hour",
        "companion_location": "60/hour",
        "companion_consent": "30/hour",
        "companion_push": "30/hour",
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}

# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_TOKEN_LIFETIME_MIN", default=30)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": env("JWT_ALGORITHM", default="HS256"),
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default=SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.serializers.EpidemiTokenObtainPairSerializer",
}

# ---------------------------------------------------------------------------
# Spectacular (OpenAPI / Swagger)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "EpidemiTracker API",
    "DESCRIPTION": (
        "Plateforme nationale de surveillance épidémiologique des voyageurs.\n\n"
        "Modules : multi-maladies, enquêtes dynamiques, Ebola, scoring, "
        "health pass QR, quarantaine 21 jours, dashboards temps réel."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v1/",
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=[])
# Par défaut on autorise les domaines de production + tests :
#   destinationci.com         (portail public voyageurs)
#   *.veillesanitaire.com     (admin.veillesanitaire.com + api.veillesanitaire.com)
#   *.lvh.me                  (tests locaux avec sous-domaines)
#   localhost / 127.0.0.1     (tous ports)
CORS_ALLOWED_ORIGIN_REGEXES = env.list(
    "DJANGO_CORS_ALLOWED_ORIGIN_REGEXES",
    default=[
        r"^https?://(.*\.)?destinationci\.com(:\d+)?$",
        r"^https?://(.*\.)?veillesanitaire\.com(:\d+)?$",
        r"^https?://(.*\.)?lvh\.me(:\d+)?$",
        r"^http://localhost(:\d+)?$",
        r"^http://127\.0\.0\.1(:\d+)?$",
    ],
)
# Headers explicitement autorisés sur la preflight (utile car notre client
# envoie Authorization, Content-Type, X-Requested-With, etc.)
CORS_ALLOW_HEADERS = list(
    env.list(
        "DJANGO_CORS_ALLOW_HEADERS",
        default=[
            "accept", "accept-encoding", "authorization", "content-type",
            "dnt", "origin", "user-agent", "x-csrftoken", "x-requested-with",
        ],
    )
)
CORS_ALLOW_METHODS = ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"]

# ---------------------------------------------------------------------------
# Cache (Redis)
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("CACHE_URL", default="redis://redis:6379/4"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "epidemi",
    }
}
DJANGO_REDIS_IGNORE_EXCEPTIONS = True

# ---------------------------------------------------------------------------
# Channels (websocket realtime)
# ---------------------------------------------------------------------------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("CHANNEL_REDIS_URL", default="redis://redis:6379/1")],
            "capacity": 2000,
            "expiry": 60,
        },
    }
}

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/2")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/3")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TIME_LIMIT = 60 * 10
CELERY_TASK_SOFT_TIME_LIMIT = 60 * 8
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_RESULT_EXTENDED = True
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_ROUTES = {
    "apps.notifications.tasks.*": {"queue": "notifications"},
    "apps.quarantine.tasks.*": {"queue": "quarantine"},
    "apps.health_pass.tasks.*": {"queue": "passes"},
    "apps.surveillance.tasks.*": {"queue": "surveillance"},
}

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@epidemitracker.local")
ANYMAIL = {
    "SENDGRID_API_KEY": env("ANYMAIL_SENDGRID_API_KEY", default=""),
}

# ---------------------------------------------------------------------------
# Sécurité (durcie en prod.py)
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=False)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=False)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# Health Pass / QR cryptographic signing
# ---------------------------------------------------------------------------
HEALTHPASS = {
    "PRIVATE_KEY_PATH": env(
        "HEALTHPASS_PRIVATE_KEY_PATH",
        default=str(BASE_DIR / "keys" / "healthpass_ed25519_private.pem"),
    ),
    "PUBLIC_KEY_PATH": env(
        "HEALTHPASS_PUBLIC_KEY_PATH",
        default=str(BASE_DIR / "keys" / "healthpass_ed25519_public.pem"),
    ),
    "ISSUER": env("HEALTHPASS_ISSUER", default="MSHPCMU-CI"),
    "DEFAULT_TTL_DAYS": env.int("HEALTHPASS_DEFAULT_TTL_DAYS", default=30),
}

# ---------------------------------------------------------------------------
# Notifications providers
# ---------------------------------------------------------------------------
NOTIFICATIONS = {
    "SMS_PROVIDER": env("SMS_PROVIDER", default="stub"),
    "WHATSAPP_PROVIDER": env("WHATSAPP_PROVIDER", default="stub"),
    "TWILIO_ACCOUNT_SID": env("TWILIO_ACCOUNT_SID", default=""),
    "TWILIO_AUTH_TOKEN": env("TWILIO_AUTH_TOKEN", default=""),
    "TWILIO_FROM_NUMBER": env("TWILIO_FROM_NUMBER", default=""),
    "WHATSAPP_FROM_NUMBER": env("WHATSAPP_FROM_NUMBER", default=""),
    "FCM_SERVER_KEY": env("FCM_SERVER_KEY", default=""),
}

# ---------------------------------------------------------------------------
# Web Push (VAPID) — utilisé par apps.companion pour notifier la PWA voyageur
# ---------------------------------------------------------------------------
# Générer la paire de clés une fois via la commande :
#   python manage.py generate_vapid_keys
# Les fichiers sont stockés dans le volume `keys_data` (persistant).
# URL publique racine utilisée pour construire les liens cliquables dans
# les SMS de fallback (le SMS n'a pas de notion de domaine).
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", default="https://destinationci.com")

WEBPUSH = {
    "VAPID_PRIVATE_KEY_PATH": env(
        "VAPID_PRIVATE_KEY_PATH",
        default=str(BASE_DIR / "keys" / "vapid_private.pem"),
    ),
    "VAPID_PUBLIC_KEY_PATH": env(
        "VAPID_PUBLIC_KEY_PATH",
        default=str(BASE_DIR / "keys" / "vapid_public.pem"),
    ),
    # Champ "sub" du JWT VAPID — doit être un mailto: ou https: que le push
    # service peut contacter en cas de problème (RFC 8292).
    "VAPID_CLAIM_SUB": env(
        "VAPID_CLAIM_SUB", default="mailto:info@destinationci.com",
    ),
    # Clé publique exposée à l'API publique (`/api/v1/public/push/public-key/`)
    # pour que la PWA puisse appeler `pushManager.subscribe()` avec.
    # Calculée automatiquement à partir du PEM par le service.
}

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
APP_METADATA = {
    "COUNTRY_CODE": env("COUNTRY_CODE", default="CI"),
    "NATIONAL_ORG_NAME": env("NATIONAL_ORG_NAME", default="MSHPCMU"),
    "INHP_ORG_NAME": env("INHP_ORG_NAME", default="Institut National d'Hygiène Publique"),
    "DEFAULT_QUARANTINE_DAYS": env.int("DEFAULT_QUARANTINE_DAYS", default=21),
}

# ---------------------------------------------------------------------------
# Logging (structlog-ready, JSON en prod)
# ---------------------------------------------------------------------------
LOG_LEVEL = env("LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} [{module}:{lineno}] {message}",
            "style": "{",
        },
        "simple": {"format": "{levelname} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.db.backends": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "epidemitracker": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}

# Guardian (object-level perms)
GUARDIAN_RAISE_403 = True

# Sessions
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # frontend JS needs to read it
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 8  # 8h
