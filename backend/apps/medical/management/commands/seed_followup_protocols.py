"""Seed du protocole de suivi par défaut pour Ebola (Phase 9A).

Idempotent — peut être rejoué autant de fois que nécessaire. Crée la
maladie Ebola si elle n'existe pas (sécurité staging) puis crée /
met à jour le `DiseaseFollowupProtocol` associé.

Usage:
    python manage.py seed_followup_protocols
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.diseases.models import Disease, DiseaseSeverity
from apps.medical.models import DiseaseFollowupProtocol


EBOLA_PROTOCOL = {
    "duration_days": 21,
    "daily_checkin_required": True,
    "daily_checkin_recommended": False,
    "critical_symptoms": [
        "fever",
        "unexplained_bleeding",
        "conjunctivitis",
        "chest_pain",
    ],
    "monitored_symptoms": [
        "fever",
        "fatigue",
        "muscle_pain",
        "headache",
        "sore_throat",
        "abdominal_pain",
        "diarrhea",
        "vomiting",
        "unexplained_bleeding",
        "conjunctivitis",
        "chest_pain",
    ],
    # Règles d'escalade : 2 check-ins manqués OU 1 symptôme critique → escalade.
    "escalation_rules": {
        "missed_checkins": 2,
        "critical_symptom": True,
    },
    # Règles de clôture : 21 jours pleins + aucun symptôme critique → close auto.
    "closure_rules": {
        "days_completed": 21,
        "no_critical_symptom": True,
    },
    # Planning notifications : rappel quotidien à 08:00, check des manqués à 48 h.
    "notification_schedule": {
        "daily_reminder_hour": 8,
        "missed_followup_check_hours": 48,
    },
    # Visite terrain : déclenchée après 3 check-ins manqués OU symptôme critique.
    "field_visit_rules": {
        "trigger_after_missed_checkins": 3,
        "trigger_on_critical_symptom": True,
    },
    # Règles prélèvement / labo — modèle libre, à enrichir en 9B/9C.
    "sample_required_rules": {
        "if_symptom": ["fever", "unexplained_bleeding"],
    },
    "lab_analysis_required_rules": {
        "test_type": "PCR Ebola",
        "on_sample_types": ["blood"],
    },
    "require_geolocation": True,
    "geolocation_alert_after_hours": 24,
    "is_active": True,
}


class Command(BaseCommand):
    help = "Crée / met à jour les DiseaseFollowupProtocol par défaut (Ebola)."

    def handle(self, *args, **options) -> None:
        with transaction.atomic():
            disease, created = Disease.objects.get_or_create(
                code="EBOLA",
                defaults={
                    "name": "Maladie à virus Ebola",
                    "short_name": "Ebola",
                    "severity": DiseaseSeverity.CRITICAL,
                    "color": "#dc2626",
                    "incubation_min_days": 2,
                    "incubation_max_days": 21,
                    "surveillance_days": 21,
                    "quarantine_days": 21,
                    "risk_countries": ["CD", "UG"],
                    "requires_quarantine": True,
                    "requires_pass": True,
                },
            )
            if created:
                self.stdout.write(self.style.WARNING(
                    "Disease EBOLA n'existait pas — créée avec les valeurs par défaut."
                ))

            protocol, was_created = DiseaseFollowupProtocol.objects.update_or_create(
                disease=disease,
                defaults=EBOLA_PROTOCOL,
            )

            action = "créé" if was_created else "mis à jour"
            self.stdout.write(self.style.SUCCESS(
                f"Protocole Ebola {action} (id={protocol.pk}, "
                f"durée={protocol.duration_days}j, "
                f"géoloc={'oui' if protocol.require_geolocation else 'non'}, "
                f"seuil alerte={protocol.geolocation_alert_after_hours}h)."
            ))
