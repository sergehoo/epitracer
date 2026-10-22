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
    # CSP — middleware + nonce. Activé en prod via prod.py (CSP_*).
    # Doit rester avant LOCAL_APPS pour que les tags template soient
    # disponibles dans nos templates Django.
    "csp",
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
    "apps.mobile_api",
    "apps.companion",
    "apps.reports",
    # Phase 9A — fondation du suivi médical complet (protocoles, prélèvements,
    # analyses labo, classifications, timeline d'actions, géoloc obligatoire).
    "apps.medical",
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
    # CSP — injecte le header Content-Security-Policy (et le report-only en
    # bascule) à partir des settings CSP_*. Placé juste après SecurityMiddleware
    # pour bénéficier du nonce dans tous les templates Django downstream.
    "csp.middleware.CSPMiddleware",
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
# Validation des uploads publics (task #213 — sécurité P0)
# Utilisée par apps.core.validators.validate_uploaded_file qui vérifie :
#   - taille max
#   - MIME déclaré (Content-Type côté client — non-fiable mais on rejette
#     les Content-Type non whitelistés en premier filtre)
#   - magic bytes (en-tête réel du fichier — non triché côté client)
# ---------------------------------------------------------------------------
MAX_UPLOAD_SIZE_MB = env.int("MAX_UPLOAD_SIZE_MB", default=5)
ALLOWED_UPLOAD_MIMES = env.list(
    "ALLOWED_UPLOAD_MIMES",
    default=[
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/pdf",
    ],
)
# Limite globale Django sur le corps multipart (sécurité défense-en-profondeur).
# 8 Mo : laisse une marge au MAX_UPLOAD_SIZE_MB + champs texte du formulaire.
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int(
    "DATA_UPLOAD_MAX_MEMORY_SIZE", default=8 * 1024 * 1024,
)
FILE_UPLOAD_MAX_MEMORY_SIZE = env.int(
    "FILE_UPLOAD_MAX_MEMORY_SIZE", default=8 * 1024 * 1024,
)

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
        # Consultation publique d'un pass par public_id — protégé contre
        # l'énumération brute (30/min par IP est largement suffisant pour
        # un usage légitime, et bloque un scanner massif).
        "qr_verify_public": "30/min",
        # Envoi manuel de notifications (SMS/WhatsApp) par un agent.
        # Anti-spam pour éviter qu'un compte compromis ou un agent
        # malveillant envoie en masse aux voyageurs.
        "notifications_send": "30/hour",
        # Companion : limites généreuses pour la PWA, plus serrées
        # sur les pings de localisation pour éviter le tracking abusif.
        "companion_checkin": "12/hour",
        # Phase 9B — endpoints publics suivi médical (PWA + Flutter).
        "mobile_followup": "10/min",
       
        "companion_location": "60/hour",
        "companion_consent": "30/hour",
        "companion_push": "30/hour",
        # MFA email — renvoi de code OTP (cooldown anti-spam)
        "mfa_resend": "6/min",
        # Password reset public — anti-énumération + anti-spam
        "password_reset": "5/hour",
        # ── Sécurité P0 (task #213) — endpoints très exposés ─────────────
        # Formulaire voyageur public (PublicTravelerRegisterView).
        # 5/min IP suffit pour un usage légitime (un voyageur = 1 soumission).
        "public_registration": "5/min",
        # Consultation publique d'un pass par public_id (anti-énumération).
        # Duplique qr_verify_public pour clarté sémantique côté views.
        "public_pass_consult": "20/min",
        # Mobile — demande OTP voyageur (apps.mobile_api.voyageur_auth).
        # 3/min IP + cooldown applicatif côté phone (cache Redis).
        "mobile_otp_request": "3/min",
        # Mobile — login agents (alias EpidemiTokenObtainPair).
        "mobile_login": "10/min",
        # Mobile — Phase 8B : récupération du schéma DynamicForm.
        # 20/min/IP suffit largement pour un client mobile (1 fetch + drafts).
        "mobile_form_schema": "20/min",
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
    # IMPORTANT : nos tâches ont des noms CUSTOM via @shared_task(name="...")
    # — par ex. "notifications.send_notification_task" et NON
    # "apps.notifications.tasks.send_notification_task". Il faut donc router
    # sur le NOM ENREGISTRÉ, sinon Celery tombe sur la queue par défaut
    # "celery" que personne ne consomme (-Q default,notifications,...).
    "notifications.*": {"queue": "notifications"},
    "quarantine.*": {"queue": "quarantine"},
    "passes.*": {"queue": "passes"},
    "surveillance.*": {"queue": "surveillance"},
    "companion.*": {"queue": "notifications"},  # purge/cleanup → queue notifications
    "core.*": {"queue": "default"},
    # Phase 9A — `medical.*` partage la queue quarantaine (workflow proche).
    "medical.*": {"queue": "quarantine"},
    # Patterns module path conservés en filet de sécurité si une tâche n'a
    # pas de `name=` explicite.
    "apps.notifications.tasks.*": {"queue": "notifications"},
    "apps.quarantine.tasks.*": {"queue": "quarantine"},
    "apps.health_pass.tasks.*": {"queue": "passes"},
    "apps.surveillance.tasks.*": {"queue": "surveillance"},
}

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
# Backend Django par défaut — utilisé seulement par les usages legacy de
# `send_mail()`. La chaîne email métier passe TOUJOURS par EmailRouter qui
# choisit lui-même la connexion SMTP (PUBLIC ou INTERNAL) selon email_type.
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@epidemitracker.local")
ANYMAIL = {
    "SENDGRID_API_KEY": env("ANYMAIL_SENDGRID_API_KEY", default=""),
}

# ---------------------------------------------------------------------------
# Email multi-expéditeur — DUAL SMTP
#
# PUBLIC  (voyageurs, grand public)  → Amazon SES SMTP via destinationci.com
# INTERNAL (admin, agents, système)  → SMTP serveur via veillesanitaire.com
#
# La séparation est imposée côté backend par apps.notifications.services.email_router.
# Le frontend ne choisit JAMAIS l'expéditeur. Voir docs/EMAIL_MULTI_SENDER_SETUP.md
# ---------------------------------------------------------------------------
EMAIL_PROFILES = {
    "public": {
        # Amazon SES SMTP — voyageurs / public
        "host": env("PUBLIC_EMAIL_HOST", default="email-smtp.eu-west-1.amazonaws.com"),
        "port": env.int("PUBLIC_EMAIL_PORT", default=587),
        "use_tls": env.bool("PUBLIC_EMAIL_USE_TLS", default=True),
        "use_ssl": env.bool("PUBLIC_EMAIL_USE_SSL", default=False),
        "username": env("PUBLIC_EMAIL_HOST_USER", default=""),
        "password": env("PUBLIC_EMAIL_HOST_PASSWORD", default=""),
        "from_name": env("PUBLIC_EMAIL_FROM_NAME", default="Destination CI - Accompagnement Voyageur"),
        "from_address": env("PUBLIC_EMAIL_FROM_ADDRESS", default="infos@destinationci.com"),
        "reply_to": env("DEFAULT_REPLY_TO_PUBLIC", default="infos@destinationci.com"),
        "timeout": env.int("PUBLIC_EMAIL_TIMEOUT", default=20),
    },
    "internal": {
        # SMTP serveur (sortant local) — admin / agents
        "host": env("INTERNAL_EMAIL_HOST", default="localhost"),
        "port": env.int("INTERNAL_EMAIL_PORT", default=587),
        "use_tls": env.bool("INTERNAL_EMAIL_USE_TLS", default=True),
        "use_ssl": env.bool("INTERNAL_EMAIL_USE_SSL", default=False),
        "username": env("INTERNAL_EMAIL_HOST_USER", default=""),
        "password": env("INTERNAL_EMAIL_HOST_PASSWORD", default=""),
        "from_name": env("INTERNAL_EMAIL_FROM_NAME", default="INHP - Veille Sanitaire"),
        "from_address": env("INTERNAL_EMAIL_FROM_ADDRESS", default="inhp@veillesanitaire.com"),
        "reply_to": env("DEFAULT_REPLY_TO_INTERNAL", default="inhp@veillesanitaire.com"),
        "timeout": env.int("INTERNAL_EMAIL_TIMEOUT", default=20),
    },
}

# URL de la page de connexion admin (utilisée dans les emails de création
# de compte et reset password). Doit être l'URL Next.js exacte (/auth/login).
ADMIN_LOGIN_URL = env("ADMIN_LOGIN_URL", default="https://admin.veillesanitaire.com/auth/login")

# Durée de validité des tokens de reset password (heures)
PASSWORD_RESET_TOKEN_TTL_HOURS = env.int("PASSWORD_RESET_TOKEN_TTL_HOURS", default=24)

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
# Content-Security-Policy (django-csp) — task #213
#
# Mode par défaut : REPORT-ONLY (en dev / staging). Permet de mesurer les
# violations sans casser la PWA, l'admin Next.js ou les pages Django avant
# de passer en mode "enforce" via prod.py.
#
# Stratégie :
#   - default-src 'self'
#   - script-src  'self' + nonce (généré par le middleware csp)
#   - style-src   'self' 'unsafe-inline'  (Tailwind / Next.js inline)
#                 + https://fonts.googleapis.com
#   - img-src     'self' data: https:
#   - font-src    'self' https://fonts.gstatic.com data:
#   - connect-src 'self' wss: https://api.veillesanitaire.com
#                 https://api-staging.veillesanitaire.com
#   - frame-ancestors 'none'    (anti-clickjacking, > X-Frame-Options DENY)
#   - report-uri  (optionnel, configurable via env)
#
# Le frontend Next.js applique sa propre CSP via headers Traefik côté SSR ;
# cette config s'applique aux réponses Django (admin, swagger, healthcheck,
# media servi en debug).
# ---------------------------------------------------------------------------
CSP_REPORT_ONLY = env.bool("CSP_REPORT_ONLY", default=True)

CSP_DEFAULT_SRC = ("'self'",)

# 'self' + nonce(via templatetag {% csp_nonce %}). 'unsafe-inline' RESTE
# nécessaire pour l'admin Django (script inline) ET Next.js qui inline du
# JS au build (chunks runtime). Une fois le portail Next.js entièrement
# migré en CSP3 strict-dynamic on pourra retirer 'unsafe-inline'.
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")
CSP_INCLUDE_NONCE_IN = ("script-src",)

# Tailwind + admin Django + Swagger + Google Fonts (utilisés par les PDFs
# Reportlab embarqués mais pas dans le navigateur — gardé par sécurité).
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com", "data:")

# Images : QR codes générés en data: + media servi sur /media/.
CSP_IMG_SRC = ("'self'", "data:", "blob:", "https:")

# Connect : appels XHR/fetch + WebSocket Channels (api.veillesanitaire.com/ws/).
CSP_CONNECT_SRC = env.list(
    "CSP_CONNECT_SRC",
    default=[
        "'self'",
        "https://api.veillesanitaire.com",
        "https://api-staging.veillesanitaire.com",
        "https://admin.veillesanitaire.com",
        "https://destinationci.com",
        "wss://api.veillesanitaire.com",
        "wss://api-staging.veillesanitaire.com",
    ],
)

# Anti-clickjacking : aucun parent autorisé (plus strict que X-Frame-Options
# DENY déjà en place — frame-ancestors prime sur XFO en CSP Level 2).
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = ("'self'",)
CSP_OBJECT_SRC = ("'none'",)

# Sources média (audio/video) — pas utilisé pour l'instant mais on bloque
# explicitement.
CSP_MEDIA_SRC = ("'self'", "blob:", "data:")

# Worker (service worker PWA, side-loaded sous /voyageur/).
CSP_WORKER_SRC = ("'self'", "blob:")

# Endpoint de report optionnel — Django logge les violations.
CSP_REPORT_URI = env("CSP_REPORT_URI", default="")
# Active la directive seulement si un endpoint est configuré.
if not CSP_REPORT_URI:
    CSP_REPORT_URI = None

# Exempter les endpoints suivants (collectstatic + media + healthchecks)
# de l'en-tête CSP — sinon on pollue les logs pour rien.
CSP_EXCLUDE_URL_PREFIXES = (
    "/static/",
    "/media/",
    "/healthz",
    "/metrics",
)

# ---------------------------------------------------------------------------
# Chiffrement at-rest des PII (task #213 — chantier 4)
#
# Repose sur django-cryptography (Fernet) avec rotation via FERNET_KEYS.
# La première clé sert au chiffrement ; toutes les clés sont essayées
# en déchiffrement (rotation transparente : on AJOUTE la nouvelle clé en
# tête, on garde l'ancienne pendant la migration, puis on retire l'ancienne
# une fois `rotate_fernet` exécuté.
#
# IMPORTANT : la liste est lue depuis DJANGO_FERNET_KEYS au format
#   "key1,key2,..." (clés base64 url-safe 32 bytes).
# Générer une clé via :
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
#
# Si aucune clé n'est fournie, on retombe sur SECRET_KEY (dev/staging only —
# en prod c'est une erreur de config et `manage.py check --deploy` doit
# le signaler).
# ---------------------------------------------------------------------------
_fernet_keys_raw = env("DJANGO_FERNET_KEYS", default="")
if _fernet_keys_raw:
    FERNET_KEYS = [k.strip() for k in _fernet_keys_raw.split(",") if k.strip()]
else:
    # Fallback dev/test — DOIT être remplacé en prod via env.
    FERNET_KEYS = [SECRET_KEY]
# Désactive l'avertissement django-cryptography quand on utilise SECRET_KEY.
CRYPTOGRAPHY_KEY = None  # délégué à FERNET_KEYS
CRYPTOGRAPHY_DIGEST = "sha256"
CRYPTOGRAPHY_SALT = env("DJANGO_CRYPTOGRAPHY_SALT", default="epitrace.cryptography")

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
    # Legacy keys (compat ascendante)
    "SMS_PROVIDER": env("SMS_PROVIDER", default="auto"),  # "auto" = routage par numéro
    "FCM_SERVER_KEY": env("FCM_SERVER_KEY", default=""),

    # ── Orange Côte d'Ivoire (numéros +225) ──────────────────────────
    "ORANGE_CI_SMS_ENABLED": env.bool("ORANGE_CI_SMS_ENABLED", default=False),
    "ORANGE_CI_SMS_BASE_URL": env("ORANGE_CI_SMS_BASE_URL",
                                   default="https://api.orange.com/smsmessaging/v1"),
    "ORANGE_CI_SMS_TOKEN_URL": env("ORANGE_CI_SMS_TOKEN_URL",
                                    default="https://api.orange.com/oauth/v3/token"),
    "ORANGE_CI_SMS_CLIENT_ID": env("ORANGE_CI_SMS_CLIENT_ID", default=""),
    "ORANGE_CI_SMS_CLIENT_SECRET": env("ORANGE_CI_SMS_CLIENT_SECRET", default=""),
    # MSISDN émetteur du contrat Orange CI — Format E.164 (ex: +2250709862860).
    # OBLIGATOIRE : sert pour senderAddress dans le payload + path URL.
    "ORANGE_CI_SMS_SENDER_MSISDN": env("ORANGE_CI_SMS_SENDER_MSISDN", default=""),
    # Sender ID alphanumérique affiché chez le destinataire (5-11 chars).
    # À valider auprès d'Orange Business CI ; va dans le champ senderName.
    "ORANGE_CI_SMS_SENDER_NAME": env("ORANGE_CI_SMS_SENDER_NAME", default="EpiTrace"),
    "ORANGE_CI_SMS_TIMEOUT": env.int("ORANGE_CI_SMS_TIMEOUT", default=15),
    "ORANGE_CI_WEBHOOK_TOKEN": env("ORANGE_CI_WEBHOOK_TOKEN", default=""),
    # URL publique du delivery webhook — quand renseignée, on envoie un
    # `receiptRequest` dans le payload SMS pour qu'Orange CI nous notifie.
    "ORANGE_CI_SMS_CALLBACK_URL": env("ORANGE_CI_SMS_CALLBACK_URL", default=""),

    # ── Twilio (SMS international + WhatsApp) ────────────────────────
    "TWILIO_SMS_ENABLED": env.bool("TWILIO_SMS_ENABLED",
                                    default=bool(env("TWILIO_ACCOUNT_SID", default=""))),
    "TWILIO_ACCOUNT_SID": env("TWILIO_ACCOUNT_SID", default=""),
    "TWILIO_AUTH_TOKEN": env("TWILIO_AUTH_TOKEN", default=""),
    "TWILIO_FROM_NUMBER": env("TWILIO_FROM_NUMBER", default=""),
    "TWILIO_TIMEOUT": env.int("TWILIO_TIMEOUT", default=15),
    "TWILIO_STATUS_CALLBACK_BASE": env(
        "TWILIO_STATUS_CALLBACK_BASE",
        default="https://api.veillesanitaire.com",
    ),

    # ── WhatsApp (Phase C — Twilio ou Meta) ──────────────────────────
    "WHATSAPP_ENABLED": env.bool("WHATSAPP_ENABLED", default=False),
    "WHATSAPP_PROVIDER": env("WHATSAPP_PROVIDER", default="twilio"),  # "twilio" | "meta"
    "TWILIO_WHATSAPP_FROM": env("TWILIO_WHATSAPP_FROM", default=""),
    "WHATSAPP_FROM_NUMBER": env("WHATSAPP_FROM_NUMBER", default=""),  # legacy alias
    "META_WHATSAPP_TOKEN": env("META_WHATSAPP_TOKEN", default=""),
    "META_WHATSAPP_PHONE_NUMBER_ID": env("META_WHATSAPP_PHONE_NUMBER_ID", default=""),
    "META_WHATSAPP_BUSINESS_ACCOUNT_ID": env("META_WHATSAPP_BUSINESS_ACCOUNT_ID", default=""),
    # Tokens spécifiques webhooks Meta
    "META_WHATSAPP_VERIFY_TOKEN": env("META_WHATSAPP_VERIFY_TOKEN", default=""),
    "META_WHATSAPP_APP_SECRET": env("META_WHATSAPP_APP_SECRET", default=""),
    "META_WHATSAPP_API_VERSION": env("META_WHATSAPP_API_VERSION", default="v19.0"),
    "WHATSAPP_TIMEOUT": env.int("WHATSAPP_TIMEOUT", default=15),
}

# ---------------------------------------------------------------------------
# Telegram Bot API — canal notifications direct (voyageur ↔ bot INHP)
# ---------------------------------------------------------------------------
# Configuration :
#   1. @BotFather → /newbot → récupérer le HTTP token (63 chars) → TELEGRAM_BOT_TOKEN
#   2. Choisir un nom d'utilisateur ex. @MonPassSanitaireINHP_bot → TELEGRAM_BOT_USERNAME
#   3. Générer un secret random ≥ 32 chars → TELEGRAM_WEBHOOK_SECRET
#   4. Lancer : python manage.py telegram_setup --set
#
# Le token du bot est un secret : ne JAMAIS le logger en clair.
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", default="")
TELEGRAM_WEBHOOK_SECRET = env("TELEGRAM_WEBHOOK_SECRET", default="")

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
# Phase 9A — Texte de consentement géolocalisation (Option 3, RGPD-safe).
#
# À présenter au voyageur dans la PWA (page /voyageur/suivi) et stocké dans
# `PrivacyConsent.consent_text_excerpt` au moment du recueil. Le texte
# explicite que désactiver le partage déclenche une alerte (et non un
# tracking caché — c'est conforme RGPD car le consentement reste révocable
# et la révocation n'entraîne PAS de sanction automatisée mais une décision
# humaine d'un agent INHP).
# ---------------------------------------------------------------------------
GEOLOCATION_CONSENT_TEXT = env(
    "GEOLOCATION_CONSENT_TEXT",
    default=(
        "Pendant les 21 jours de surveillance, votre position est partagée "
        "avec l'INHP toutes les 4 heures. Vous pouvez désactiver le partage "
        "à tout moment, mais cela déclenchera une alerte qui pourra "
        "entraîner une visite d'un agent sanitaire. Vos données sont "
        "supprimées 90 jours après la fin du suivi (politique RGPD)."
    ),
)

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
