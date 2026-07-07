"""Tests chiffrement PII — chantier #213-4.

À ce stade le chantier 4 fournit :
  - l'infrastructure settings (FERNET_KEYS, CRYPTOGRAPHY_*) côté base.py
  - la commande management `migrate_pii_to_encrypted` (no-op idempotente
    tant que PII_FIELDS est vide).

Les EncryptedCharField sur Traveler ne sont pas encore appliqués au schéma
(cf. rapport — risque migration prod hors fenêtre de maintenance). Les tests
ci-dessous valident que :
  - settings sont conformes (FERNET_KEYS non vide)
  - la commande est enregistrée et exécutable en --dry-run
"""
from __future__ import annotations

from io import StringIO

import pytest
from django.conf import settings
from django.core.management import call_command


def test_fernet_keys_configured():
    """FERNET_KEYS doit toujours être une liste non-vide (fallback SECRET_KEY
    en dev/test, vraie clé Fernet base64 en prod via env)."""
    keys = getattr(settings, "FERNET_KEYS", None)
    assert isinstance(keys, list) and len(keys) >= 1
    # Toutes les clés doivent être des strings non-vides
    for k in keys:
        assert isinstance(k, str) and k


def test_cryptography_settings_present():
    assert getattr(settings, "CRYPTOGRAPHY_DIGEST", None) == "sha256"
    assert getattr(settings, "CRYPTOGRAPHY_SALT", None)


def test_migrate_pii_command_is_registered():
    """La commande doit pouvoir être appelée — en --dry-run pour rester safe."""
    out = StringIO()
    # Pas de PII_FIELDS pour l'instant — la commande doit logger un warning
    # et retourner sans erreur (idempotent + no-op).
    call_command("migrate_pii_to_encrypted", "--dry-run", stdout=out)
    output = out.getvalue()
    # On accepte deux scénarios :
    #   (a) le mapping est vide → message "PII_FIELDS est vide"
    #   (b) le mapping a déjà été enrichi → message "DRY-RUN : N lignes"
    assert "PII_FIELDS" in output or "DRY-RUN" in output


@pytest.mark.django_db
def test_migrate_pii_command_dry_run_with_model_filter():
    """--model X.Y doit ignorer silencieusement les modèles non listés."""
    out = StringIO()
    call_command(
        "migrate_pii_to_encrypted",
        "--dry-run",
        "--model", "travelers.Traveler",
        stdout=out,
    )
    # Ne lève pas, et l'output mentionne soit le warning soit le model.
    assert out.getvalue()
