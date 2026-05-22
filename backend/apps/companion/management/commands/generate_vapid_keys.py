"""Génère une paire de clés VAPID (P-256) pour Web Push.

Usage :
    python manage.py generate_vapid_keys [--force]

Les chemins sont définis dans settings.WEBPUSH.

La clé publique est exposée à la PWA via /api/v1/public/push/public-key/
et utilisée par `pushManager.subscribe({applicationServerKey})`.
"""
from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, generate_private_key
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Génère une paire de clés VAPID (ECDSA P-256) pour Web Push."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true",
            help="Écraser les clés existantes.",
        )

    def handle(self, *args, **opts):
        priv_path = Path(settings.WEBPUSH["VAPID_PRIVATE_KEY_PATH"])
        pub_path = Path(settings.WEBPUSH["VAPID_PUBLIC_KEY_PATH"])
        priv_path.parent.mkdir(parents=True, exist_ok=True)

        if priv_path.exists() and not opts["force"]:
            self.stdout.write(self.style.WARNING(
                f"Une clé VAPID existe déjà à {priv_path}. Utiliser --force pour écraser."
            ))
            return

        priv = generate_private_key(SECP256R1())
        priv_bytes = priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_bytes = priv.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        priv_path.write_bytes(priv_bytes)
        pub_path.write_bytes(pub_bytes)
        priv_path.chmod(0o600)

        # Convertir la publique en base64url pour la PWA
        from apps.companion.push import get_vapid_public_key_b64url
        get_vapid_public_key_b64url.cache_clear()  # type: ignore[attr-defined]
        b64 = get_vapid_public_key_b64url()

        self.stdout.write(self.style.SUCCESS(
            f"Clés VAPID générées :\n  - private : {priv_path}\n  - public  : {pub_path}\n"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"\nClé publique base64url (à exposer à la PWA) :\n  {b64}\n"
        ))
        self.stdout.write(self.style.WARNING(
            "\n⚠️  Sauvegarder la clé privée hors-ligne. "
            "Si elle est perdue ou volée, tous les abonnements deviennent caducs."
        ))
