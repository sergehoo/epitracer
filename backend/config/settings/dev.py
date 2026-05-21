"""Settings de développement local."""
from .base import *  # noqa: F401,F403
from .base import INSTALLED_APPS, MIDDLEWARE

DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]
# IMPORTANT : Debug Toolbar APRÈS CORS, sinon la toolbar peut intercepter
# la preflight OPTIONS et ne pas remettre les headers Access-Control-*.
# On insère après CorsMiddleware (premier dans MIDDLEWARE).
MIDDLEWARE = [MIDDLEWARE[0], "debug_toolbar.middleware.DebugToolbarMiddleware", *MIDDLEWARE[1:]]

INTERNAL_IPS = ["127.0.0.1"]


def _show_toolbar(request):
    """N'affiche la toolbar QUE sur les pages HTML.

    Empêche la toolbar de s'attacher aux XHR / fetch (sinon la preflight
    CORS peut traîner plusieurs secondes et casser le tracking).
    """
    if request.path.startswith("/api/") or request.path.startswith("/media/"):
        return False
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return False
    return DEBUG


DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": _show_toolbar}

# Email console en dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# CORS très permissif en dev (en plus des regex de base.py)
CORS_ALLOW_ALL_ORIGINS = True
