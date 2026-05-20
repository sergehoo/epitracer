"""Utilitaires partagés."""
from __future__ import annotations

import secrets
import string

import shortuuid


def short_id(prefix: str = "", length: int = 10) -> str:
    """Identifiant court lisible (ex: 'EBO-7F3A9K2X1Q')."""
    code = shortuuid.ShortUUID(alphabet=string.ascii_uppercase + string.digits).random(length=length)
    return f"{prefix}-{code}" if prefix else code


def secure_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)
