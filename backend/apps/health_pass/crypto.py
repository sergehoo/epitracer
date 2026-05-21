"""
Service cryptographique pour le Health Pass.

Format du QR (compact, base64url) :

    EPMS1.<base64url(payload_json)>.<base64url(signature_ed25519)>

- préfixe EPMS1 = "EpidemiTracker Pass v1"
- payload : JSON minimal, signé en Ed25519 par la clé serveur
- vérification offline possible : il suffit de la clé publique
- révocation : on consulte la liste de révocation (CRL) en ligne quand dispo

Champs payload signés :
{
    "iss": "MSHPCMU-CI",
    "kid": "<id clé>",
    "pid": "<pass_number>",
    "tid": "<traveler public id>",
    "dis": "EBOLA",
    "rsk": "low",
    "scr": 12,
    "iat": "<ISO>",
    "exp": "<ISO>"
}
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from django.conf import settings


PREFIX = "EPMS1"


def _b64u_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64u_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


@lru_cache(maxsize=1)
def _load_private_key() -> Ed25519PrivateKey:
    path = Path(settings.HEALTHPASS["PRIVATE_KEY_PATH"])
    if not path.exists():
        raise RuntimeError(
            f"Clé privée Ed25519 introuvable à {path}. "
            "Exécuter `python manage.py generate_pass_keys`."
        )
    return serialization.load_pem_private_key(path.read_bytes(), password=None)  # type: ignore[return-value]


@lru_cache(maxsize=1)
def _load_public_key() -> Ed25519PublicKey:
    path = Path(settings.HEALTHPASS["PUBLIC_KEY_PATH"])
    if not path.exists():
        raise RuntimeError(f"Clé publique Ed25519 introuvable à {path}.")
    return serialization.load_pem_public_key(path.read_bytes())  # type: ignore[return-value]


def public_kid() -> str:
    """Identifiant court de la clé publique (8 premiers caractères du sha256)."""
    pub = _load_public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return hashlib.sha256(pub).hexdigest()[:8]


def public_key_pem() -> bytes:
    return _load_public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def sign_payload(payload: dict) -> tuple[str, str]:
    """Signe un payload et retourne (qr_token, signature_b64)."""
    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    signature = _load_private_key().sign(payload_json)
    token = f"{PREFIX}.{_b64u_encode(payload_json)}.{_b64u_encode(signature)}"
    return token, _b64u_encode(signature)


def verify_token(token: str) -> dict:
    """Vérifie un QR token. Renvoie le payload si valide, lève InvalidSignature sinon."""
    try:
        prefix, payload_b64, sig_b64 = token.split(".", 2)
    except ValueError as exc:
        raise InvalidSignature("Format de QR invalide.") from exc
    if prefix != PREFIX:
        raise InvalidSignature("Préfixe QR inconnu.")
    payload_bytes = _b64u_decode(payload_b64)
    signature = _b64u_decode(sig_b64)
    _load_public_key().verify(signature, payload_bytes)
    return json.loads(payload_bytes)


def is_expired(payload: dict) -> bool:
    exp = payload.get("exp")
    if not exp:
        return True
    try:
        dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
    except ValueError:
        return True
    from django.utils import timezone as tz
    return dt <= tz.now()
