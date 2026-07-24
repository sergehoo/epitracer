"""Peuple les templates SMS / WhatsApp standard EpiTrace.

Ton :
    - rassurant, respectueux, non intrusif
    - orienté assistance, jamais menaçant
    - variables {first_name}, {checkin_link}, {location_link}, {message}

Usage :
    python manage.py seed_notification_templates
"""
from __future__ import annotations

from django.core.management.base import BaseCommand


TEMPLATES = [
    {
        "code": "FOLLOWUP_DAILY_SMS",
        "name": "Rappel quotidien suivi 21j",
        "description": "Invitation quotidienne à confirmer son état de santé.",
        "channels": ["sms", "whatsapp"],
        "subject": "Confirmation état de santé",
        "body": (
            "Bonjour {first_name}, nous espérons que vous allez bien. "
            "Merci de prendre quelques secondes pour confirmer votre état de santé "
            "aujourd'hui : {checkin_link}"
        ),
        "variables_schema": {
            "first_name": "string",
            "checkin_link": "url",
        },
    },
    {
        "code": "SYMPTOM_ASSISTANCE_SMS",
        "name": "Réponse à signalement de symptômes",
        "description": "Accusé bienveillant après déclaration de symptômes.",
        "channels": ["sms", "whatsapp"],
        "subject": "Suivi sanitaire — accompagnement",
        "body": (
            "Bonjour {first_name}, merci pour votre signalement. "
            "Une équipe sanitaire peut vous orienter calmement. "
            "En cas d'urgence, contactez le 143 ou le 185."
        ),
        "variables_schema": {"first_name": "string"},
    },
    {
        "code": "LOCATION_REQUEST_SMS",
        "name": "Demande de partage de position",
        "description": "Invitation à partager sa position pour faciliter l'accompagnement.",
        "channels": ["sms", "whatsapp"],
        "subject": "Partage de position",
        "body": (
            "Bonjour {first_name}, pour faciliter votre accompagnement sanitaire, "
            "vous pouvez partager votre position actuelle ici : {location_link}"
        ),
        "variables_schema": {
            "first_name": "string",
            "location_link": "url",
        },
    },
    {
        "code": "FOLLOWUP_END_SMS",
        "name": "Fin de période de suivi",
        "description": "Message de clôture après 21 jours sans symptôme.",
        "channels": ["sms", "whatsapp"],
        "subject": "Fin d'accompagnement sanitaire",
        "body": (
            "Bonjour {first_name}, votre période d'accompagnement sanitaire est terminée. "
            "Merci pour votre coopération et bon séjour."
        ),
        "variables_schema": {"first_name": "string"},
    },
    {
        "code": "MANUAL_ADMIN_NOTICE",
        "name": "Message libre de l'équipe sanitaire",
        "description": "Wrapper pour message manuel envoyé par un agent.",
        "channels": ["sms", "whatsapp"],
        "subject": "Message de l'équipe sanitaire",
        "body": "Bonjour {first_name}, message de l'équipe sanitaire : {message}",
        "variables_schema": {
            "first_name": "string",
            "message": "string",
        },
    },
    # ── TELEGRAM — invitations à rejoindre le bot (canal opt-in) ────────
    # Ces templates NE remplacent PAS SMS/Email/WhatsApp — ils invitent
    # simplement le voyageur à activer Telegram comme canal additionnel gratuit.
    {
        "code": "TELEGRAM_INVITE_SMS",
        "name": "Invitation Telegram (SMS)",
        "description": "Invite le voyageur à activer le canal Telegram en 1 clic.",
        "channels": ["sms", "whatsapp"],
        "subject": "Notifications Telegram (optionnel)",
        "body": (
            "Bonjour {first_name}, activez les notifications Telegram (gratuit) "
            "en cliquant sur ce lien : {telegram_link} — INHP"
        ),
        "variables_schema": {
            "first_name": "string",
            "telegram_link": "url",
        },
    },
    {
        "code": "TELEGRAM_INVITE_EMAIL",
        "name": "Invitation Telegram (Email)",
        "description": "Version email de l'invitation à activer le canal Telegram.",
        "channels": ["email"],
        "subject": "Activez Telegram pour vos notifications INHP (optionnel)",
        "body": (
            "Bonjour {first_name},\n\n"
            "Le dispositif Mon Pass Sanitaire propose désormais un canal "
            "supplémentaire pour recevoir ses notifications : Telegram.\n\n"
            "Avantages : gratuit, instantané, riche (formatting, PDF joignables).\n"
            "Ne remplace pas les SMS/Email — c'est un canal additionnel.\n\n"
            "Pour l'activer en 1 clic (aucune saisie) :\n"
            "{telegram_link}\n\n"
            "Votre voyageur reste identifié : {traveler_id}\n\n"
            "— INHP / Mon Pass Sanitaire"
        ),
        "variables_schema": {
            "first_name": "string",
            "traveler_id": "string",
            "telegram_link": "url",
        },
    },
    {
        "code": "EBOLA_PREVENTION_SMS",
        "name": "Rappel de prévention Ebola",
        "description": "Consignes générales de prévention MVE.",
        "channels": ["sms", "whatsapp"],
        "subject": "Conseils de prévention",
        "body": (
            "Rappel santé : lavez-vous régulièrement les mains, évitez les contacts "
            "à risque et contactez le 143 ou le 185 en cas de fièvre ou symptôme inhabituel."
        ),
        "variables_schema": {},
    },
]


class Command(BaseCommand):
    help = "Seed les templates SMS / WhatsApp officiels EpiTrace (idempotent)."

    def handle(self, *args, **options):
        from apps.notifications.models import NotificationTemplate

        n_created, n_updated = 0, 0
        for spec in TEMPLATES:
            obj, created = NotificationTemplate.objects.update_or_create(
                code=spec["code"],
                defaults={
                    "name": spec["name"],
                    "description": spec["description"],
                    "subject": spec["subject"],
                    "body": spec["body"],
                    "channels": spec["channels"],
                    "variables_schema": spec.get("variables_schema") or {},
                    "is_active": True,
                },
            )
            if created:
                n_created += 1
                self.stdout.write(f"  + {spec['code']}")
            else:
                n_updated += 1
                self.stdout.write(f"  ~ {spec['code']}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"=== Templates seedés : {n_created} créés, {n_updated} mis à jour ==="
        ))
