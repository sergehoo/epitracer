"""Envoi en masse d'invitations Telegram aux voyageurs non-liés.

Cette commande respecte le principe : **Telegram est un canal opt-in additionnel**.
Elle envoie un SMS (ou email) à chaque voyageur qui n'a PAS encore de
TelegramSubscription active, avec le deep-link pré-rempli pour son TRV-XXX.

Usage :
    # Prévisualiser (aucun envoi) — combien de voyageurs seraient invités ?
    python manage.py broadcast_telegram_invite --dry-run

    # Envoyer via SMS aux 50 premiers
    python manage.py broadcast_telegram_invite --channel sms --limit 50

    # Envoyer via Email à tous ceux qui ont un email
    python manage.py broadcast_telegram_invite --channel email

    # Cibler uniquement les voyageurs inscrits ces N derniers jours
    python manage.py broadcast_telegram_invite --since-days 7

Contrôles :
    - Bornage par défaut : --limit 100 (évite le "oops j'ai broadcasté 50k SMS")
    - --since-days optionnel pour ne cibler que les inscriptions récentes
    - Requiert le template TELEGRAM_INVITE_SMS ou TELEGRAM_INVITE_EMAIL
    - Requiert TELEGRAM_BOT_USERNAME configuré (sinon deep-link vide)
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Exists, OuterRef
from django.utils import timezone

from apps.notifications.models import (
    Channel, NotificationTemplate, TelegramSubscription,
)
from apps.notifications.services.dispatcher import send_template_message
from apps.notifications.services.telegram import get_bot_username


class Command(BaseCommand):
    help = "Invite les voyageurs non-liés à activer le canal Telegram (SMS ou email)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--channel",
            choices=["sms", "whatsapp", "email"],
            default="sms",
            help="Canal utilisé pour l'invitation. Défaut : sms.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Nombre maximum d'invitations à envoyer. Défaut : 100 (safety).",
        )
        parser.add_argument(
            "--since-days",
            type=int,
            default=None,
            help="Ne cible que les voyageurs enregistrés dans les N derniers jours.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Prévisualise combien seraient invités sans rien envoyer.",
        )

    def handle(self, *args, **opts):
        channel = opts["channel"]
        limit = max(1, int(opts["limit"]))
        since_days = opts.get("since_days")
        dry_run = opts["dry_run"]

        # Sanity checks
        if not get_bot_username():
            raise CommandError(
                "TELEGRAM_BOT_USERNAME non configuré — impossible de générer "
                "le deep-link. Ajoutez-le au .env puis relancez."
            )

        template_code = (
            "TELEGRAM_INVITE_EMAIL" if channel == "email" else "TELEGRAM_INVITE_SMS"
        )
        template = NotificationTemplate.objects.filter(
            code=template_code, is_active=True,
        ).first()
        if not template:
            raise CommandError(
                f"Template introuvable : {template_code}. "
                "Lancez d'abord : python manage.py seed_notification_templates"
            )

        # Sélection des voyageurs sans TelegramSubscription active
        from apps.travelers.models import Traveler

        # Sous-requête EXISTS = plus rapide qu'un exclude sur reverse FK
        active_subs = TelegramSubscription.objects.filter(
            traveler_id=OuterRef("pk"), is_active=True,
        )
        qs = Traveler.objects.annotate(has_tg=Exists(active_subs)).filter(has_tg=False)

        if since_days:
            cutoff = timezone.now() - timedelta(days=int(since_days))
            qs = qs.filter(created_at__gte=cutoff)

        # Filtre par disponibilité du canal
        if channel == "email":
            qs = qs.exclude(email="")
        else:
            qs = qs.exclude(phone_mobile="")

        total_eligible = qs.count()
        qs = qs.order_by("-created_at")[:limit]

        self.stdout.write(f"Voyageurs éligibles (non-liés Telegram) : {total_eligible}")
        self.stdout.write(f"Sélectionnés pour cette exécution      : {qs.count()}")
        self.stdout.write(f"Canal                                  : {channel}")
        self.stdout.write(f"Template                               : {template_code}")

        if dry_run:
            self.stdout.write(self.style.WARNING("[DRY-RUN] Aucun envoi effectué."))
            return

        sent, failed = 0, 0
        for traveler in qs:
            recipient = (
                traveler.email if channel == "email"
                else (getattr(traveler, "whatsapp_phone", "") or traveler.phone_mobile)
            )
            if not recipient:
                failed += 1
                continue

            result = send_template_message(
                traveler=traveler,
                recipient=recipient,
                template_code=template_code,
                channel=channel,
                # context minimal — le _enrich_context ajoutera first_name,
                # traveler_id et telegram_link automatiquement.
                context={},
            )
            if result.ok:
                sent += 1
            else:
                failed += 1
                self.stdout.write(f"  ✗ {traveler.public_id} : {result.error}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Terminé — {sent} envois OK, {failed} échecs."
        ))
