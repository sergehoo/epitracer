"""
Middleware ASGI qui authentifie un WebSocket via JWT en query string.

Le frontend admin se connecte à :
    wss://api.veillesanitaire.com/ws/alerts/?token=<JWT>

Le `AuthMiddlewareStack` de Channels ne gère que les sessions cookies.
Pour les WS sans cookies (cas frontend SPA séparé), on lit `?token=`
et on valide via `rest_framework_simplejwt`.
"""
from __future__ import annotations

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


@database_sync_to_async
def _get_user_from_jwt(raw_token: str):
    """Décode un JWT SimpleJWT et retourne l'utilisateur ou AnonymousUser."""
    try:
        from rest_framework_simplejwt.tokens import UntypedToken
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
        from django.contrib.auth import get_user_model

        UntypedToken(raw_token)  # valide signature + expiration
        # Le payload contient user_id
        from rest_framework_simplejwt.authentication import JWTAuthentication
        validated = JWTAuthentication().get_validated_token(raw_token)
        user = JWTAuthentication().get_user(validated)
        return user
    except Exception as exc:  # noqa: BLE001
        logger.debug("WS JWT auth failed: %s", exc)
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    """Middleware ASGI : lit ?token=... dans la query string et auth l'user."""

    async def __call__(self, scope, receive, send):
        # Default = anonymous (le consumer décidera s'il accepte ou refuse)
        scope["user"] = AnonymousUser()

        qs = scope.get("query_string", b"").decode("utf-8", errors="ignore")
        params = parse_qs(qs)
        tokens = params.get("token") or params.get("access")
        if tokens:
            scope["user"] = await _get_user_from_jwt(tokens[0])

        return await super().__call__(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    """Wrapper sucre pour utilisation dans config/asgi.py."""
    return JwtAuthMiddleware(inner)
