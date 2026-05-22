"""ASGI - sert HTTP + WebSocket via Daphne/uvicorn."""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
django.setup()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

from apps.realtime.routing import websocket_urlpatterns  # noqa: E402
from apps.realtime.jwt_middleware import JwtAuthMiddlewareStack  # noqa: E402

django_asgi_app = get_asgi_application()

# Pile d'authentification WebSocket :
# 1. AllowedHostsOriginValidator → vérifie l'origine (CORS WS)
# 2. JwtAuthMiddlewareStack → tente d'abord l'auth via ?token=<JWT> en
#    query string (cas frontend SPA séparé sans cookies cross-domain).
# 3. AuthMiddlewareStack → fallback sur l'auth par cookie de session.
# Le consumer ferme la connexion avec code 4401 si scope["user"] reste
# anonymous à la fin.
application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            JwtAuthMiddlewareStack(
                AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
            )
        ),
    }
)
