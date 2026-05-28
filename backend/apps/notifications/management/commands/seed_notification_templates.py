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
