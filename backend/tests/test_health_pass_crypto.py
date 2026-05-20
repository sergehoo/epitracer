"""Tests du système cryptographique Health Pass."""
import os
import tempfile

import pytest
from cryptography.exceptions import InvalidSignature
from django.test import override_settings


@pytest.fixture
def temp_keys(tmp_path, monkeypatch):
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv = Ed25519PrivateKey.generate()
    priv_path = tmp_path / "priv.pem"
    pub_path = tmp_path / "pub.pem"
    priv_path.write_bytes(priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ))
    pub_path.write_bytes(priv.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    from django.conf import settings
    settings.HEALTHPASS["PRIVATE_KEY_PATH"] = str(priv_path)
    settings.HEALTHPASS["PUBLIC_KEY_PATH"] = str(pub_path)
    # Reset des caches lru
    from apps.health_pass import crypto
    crypto._load_private_key.cache_clear()
    crypto._load_public_key.cache_clear()
    return priv_path, pub_path


def test_sign_and_verify_roundtrip(temp_keys):
    from apps.health_pass.crypto import sign_payload, verify_token

    payload = {"pid": "PASS-XYZ", "exp": "2099-01-01T00:00:00+00:00"}
    token, _sig = sign_payload(payload)
    out = verify_token(token)
    assert out["pid"] == "PASS-XYZ"


def test_tampered_token_fails(temp_keys):
    from apps.health_pass.crypto import sign_payload, verify_token

    token, _ = sign_payload({"pid": "ABC"})
    head, body, sig = token.split(".")
    # On bidouille le payload encodé
    tampered = f"{head}.{body[:-2]}AA.{sig}"
    with pytest.raises(InvalidSignature):
        verify_token(tampered)
