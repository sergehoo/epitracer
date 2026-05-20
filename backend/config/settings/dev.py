"""Settings de développement local."""
from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE

DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]
MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware", *MIDDLEWARE]

INTERNAL_IPS = ["127.0.0.1"]
DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda r: DEBUG}

# Email console en dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS permissif en dev local
CORS_ALLOW_ALL_ORIGINS = True
