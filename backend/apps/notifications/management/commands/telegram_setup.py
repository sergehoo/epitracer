"""Commande management pour configurer le webhook Telegram sur le bot.

Usage :
    # Vérifier la config actuelle
    python manage.py telegram_setup --info

    # Configurer le webhook (URL par défaut depuis SITE_URL_API)
    python manage.py telegram_setup --set

    # Configurer une URL personnalisée
    python manage.py telegram_setup --set --url https://api.veillesanitaire.com/api/v1/telegram/webhook/

    # Supprimer le webhook (mode polling)
    python manage.py telegram_setup --delete
"""
from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.notifications.services.telegram import (
    TelegramNotConfigured, delete_webhook, get_webhook_info, is_configured,
    set_webhook,
)


class Command(BaseCommand):
    help = "Configure ou inspecte le webhook Telegram."

    def add_arguments(self, parser):
        parser.add_argument("--info", action="store_true", help="Affiche l'état actuel du webhook.")
        parser.add_argument("--set", action="store_true", help="Configure le webhook.")
        parser.add_argument("--delete", action="store_true", help="Supprime le webhook.")
        parser.add_argument("--url", type=str, default="", help="URL personnalisée.")

    def handle(self, *args, **opts):
        if not is_configured():
            raise CommandError(
                "TELEGRAM_BOT_TOKEN non configuré. Ajoutez-le au fichier .env."
            )

        try:
            if opts["info"]:
                info = get_webhook_info()
                self.stdout.write(self.style.SUCCESS("État actuel du webhook :"))
                self.stdout.write(str(info))
                return

            if opts["delete"]:
                res = delete_webhook()
                self.stdout.write(self.style.WARNING(f"Webhook supprimé : {res}"))
                return

            if opts["set"]:
                url = opts["url"].strip()
                if not url:
                    api_base = getattr(settings, "SITE_URL_API", "") or ""
                    if not api_base:
                        raise CommandError(
                            "Aucune --url fournie et SITE_URL_API n'est pas défini."
                        )
                    url = f"{api_base.rstrip('/')}/api/v1/telegram/webhook/"

                secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "") or ""
                if not secret:
                    self.stdout.write(self.style.WARNING(
                        "⚠  TELEGRAM_WEBHOOK_SECRET vide — le webhook n'aura "
                        "PAS de vérification de signature. Recommandé en prod."
                    ))

                res = set_webhook(url, secret_token=secret)
                self.stdout.write(self.style.SUCCESS(f"Webhook configuré : {res}"))
                self.stdout.write(f"→ URL : {url}")
                return

            self.stdout.write(self.style.NOTICE(
                "Aucune action fournie. Utilisez --info / --set / --delete."
            ))
        except TelegramNotConfigured as exc:
            raise CommandError(str(exc))
