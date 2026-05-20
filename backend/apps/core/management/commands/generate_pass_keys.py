"""Génère une paire de clés Ed25519 pour signer les Health Pass.

Usage :
    python manage.py generate_pass_keys [--force]

Les chemins sont définis dans settings.HEALTHPASS.
"""
from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Génère une paire de clés Ed25519 pour signer les Health Pass."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Écraser les clés existantes.")

    def handle(self, *args, **opts):
        priv_path = Path(settings.HEALTHPASS["PRIVATE_KEY_PATH"])
        pub_path = Path(settings.HEALTHPASS["PUBLIC_KEY_PATH"])
        priv_path.parent.mkdir(parents=True, exist_ok=True)

        if priv_path.exists() and not opts["force"]:
            self.stdout.write(self.style.WARNING(
                f"Une clé existe déjà à {priv_path}. Utiliser --force pour écraser."
            ))
            return

        private_key = Ed25519PrivateKey.generate()
        priv_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        priv_path.write_bytes(priv_bytes)
        pub_path.write_bytes(pub_bytes)
        priv_path.chmod(0o600)

        self.stdout.write(self.style.SUCCESS(
            f"Clés Ed25519 générées :\n  - private : {priv_path}\n  - public  : {pub_path}"
        ))
        self.stdout.write(self.style.WARNING(
            "⚠️  Ces clés sont CRITIQUES. Sauvegarder hors-ligne et restreindre les accès."
        ))
