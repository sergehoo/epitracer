"""Seed les données de référence : rôles RBAC, maladies, pays à risque, points d'entrée CI."""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import RoleCode, Role
from apps.diseases.models import (
    Disease,
    DiseaseSeverity,
    RiskFactor,
    Symptom,
    TransmissionMode,
)
from apps.geo.models import Country, EntryPoint, EntryPointType, RiskLevel
from apps.notifications.models import NotificationTemplate

User = get_user_model()


DISEASES = [
    {
        "code": "EBOLA",
        "name": "Maladie à virus Ebola",
        "short_name": "Ebola",
        "icd11_code": "1D60",
        "severity": DiseaseSeverity.CRITICAL,
        "color": "#dc2626",
        "incubation_min_days": 2,
        "incubation_max_days": 21,
        "surveillance_days": 21,
        "quarantine_days": 21,
        "transmission_modes": [TransmissionMode.CONTACT, TransmissionMode.BLOOD],
        "risk_countries": ["CD", "UG", "GN", "SL", "LR", "CG"],
        "case_definition": "Fièvre brutale + 3 symptômes parmi : céphalées, vomissements, anorexie, diarrhée, asthénie, douleurs abdominales, ou contact à risque.",
        "requires_quarantine": True,
        "requires_pass": True,
    },
    {
        "code": "MPOX",
        "name": "Mpox (variole simienne)",
        "short_name": "Mpox",
        "icd11_code": "1E70",
        "severity": DiseaseSeverity.HIGH,
        "color": "#f59e0b",
        "incubation_min_days": 5,
        "incubation_max_days": 21,
        "surveillance_days": 21,
        "quarantine_days": 21,
        "transmission_modes": [TransmissionMode.CONTACT, TransmissionMode.DROPLET],
        "risk_countries": ["CD", "CG", "NG", "CM"],
        "requires_quarantine": True,
        "requires_pass": True,
    },
    {
        "code": "COVID19",
        "name": "COVID-19",
        "short_name": "COVID-19",
        "icd11_code": "RA01",
        "severity": DiseaseSeverity.MODERATE,
        "color": "#0ea5e9",
        "incubation_min_days": 2,
        "incubation_max_days": 14,
        "surveillance_days": 14,
        "quarantine_days": 7,
        "transmission_modes": [TransmissionMode.AIRBORNE, TransmissionMode.DROPLET],
        "risk_countries": [],
        "requires_quarantine": False,
        "requires_pass": True,
    },
    {
        "code": "CHOLERA",
        "name": "Choléra",
        "short_name": "Choléra",
        "icd11_code": "1A00",
        "severity": DiseaseSeverity.HIGH,
        "color": "#10b981",
        "incubation_min_days": 1,
        "incubation_max_days": 5,
        "surveillance_days": 5,
        "quarantine_days": 0,
        "transmission_modes": [TransmissionMode.FECAL_ORAL],
        "requires_quarantine": False,
        "requires_pass": False,
    },
    {
        "code": "LASSA",
        "name": "Fièvre de Lassa",
        "short_name": "Lassa",
        "icd11_code": "1D61",
        "severity": DiseaseSeverity.HIGH,
        "color": "#7c3aed",
        "incubation_min_days": 6,
        "incubation_max_days": 21,
        "surveillance_days": 21,
        "quarantine_days": 21,
        "transmission_modes": [TransmissionMode.CONTACT, TransmissionMode.BLOOD],
        "risk_countries": ["NG", "SL", "GN", "LR"],
        "requires_quarantine": True,
        "requires_pass": True,
    },
    {
        "code": "YELLOW_FEVER",
        "name": "Fièvre jaune",
        "short_name": "Fièvre jaune",
        "icd11_code": "1D47",
        "severity": DiseaseSeverity.MODERATE,
        "color": "#eab308",
        "incubation_min_days": 3,
        "incubation_max_days": 6,
        "surveillance_days": 6,
        "quarantine_days": 0,
        "transmission_modes": [TransmissionMode.VECTOR],
        "requires_quarantine": False,
        "requires_pass": True,
    },
]


EBOLA_SYMPTOMS = [
    ("fever", "Fièvre", 3, False),
    ("headache", "Céphalées", 1, False),
    ("muscle_pain", "Douleurs musculaires", 1, False),
    ("fatigue", "Fatigue intense", 1, False),
    ("vomiting", "Vomissements", 2, False),
    ("diarrhea", "Diarrhée", 2, False),
    ("abdominal_pain", "Douleurs abdominales", 1, False),
    ("rash", "Éruption cutanée", 1, False),
    ("red_eyes", "Yeux rouges", 1, False),
    ("bleeding", "Saignements inexpliqués", 5, True),
    ("bloody_vomit", "Vomissements sanglants", 5, True),
    ("bloody_stools", "Selles sanglantes", 5, True),
]


EBOLA_RISK_FACTORS = [
    ("visited_outbreak_country", "Voyage en pays foyer Ebola", 5),
    ("contact_confirmed_case", "Contact avec un cas confirmé", 7),
    ("contact_suspect_case", "Contact avec un cas suspect", 4),
    ("attended_funeral", "Participation à des funérailles", 4),
    ("visited_healthcare", "Visite d'un centre de soins en zone à risque", 2),
    ("handled_bushmeat", "Manipulation de viande de brousse", 2),
    ("wildlife_contact", "Contact avec faune sauvage / chauve-souris / primates", 2),
    ("healthcare_worker", "Profession médicale en zone à risque", 2),
]


COUNTRIES = [
    # ISO-2, name, region, risk_level, risk_for_diseases
    ("CI", "Côte d'Ivoire", "Afrique", RiskLevel.LOW, []),
    ("GH", "Ghana", "Afrique", RiskLevel.LOW, []),
    ("NG", "Nigeria", "Afrique", RiskLevel.MODERATE, ["LASSA", "MPOX"]),
    ("CD", "République démocratique du Congo", "Afrique", RiskLevel.RED, ["EBOLA", "MPOX"]),
    ("CG", "République du Congo", "Afrique", RiskLevel.HIGH, ["EBOLA", "MPOX"]),
    ("UG", "Ouganda", "Afrique", RiskLevel.HIGH, ["EBOLA"]),
    ("GN", "Guinée", "Afrique", RiskLevel.HIGH, ["EBOLA", "LASSA"]),
    ("SL", "Sierra Leone", "Afrique", RiskLevel.HIGH, ["EBOLA", "LASSA"]),
    ("LR", "Liberia", "Afrique", RiskLevel.HIGH, ["EBOLA", "LASSA"]),
    ("FR", "France", "Europe", RiskLevel.LOW, []),
    ("US", "États-Unis", "Amérique", RiskLevel.LOW, []),
]


# Points d'entrée Côte d'Ivoire (sélection)
ENTRY_POINTS = [
    {
        "code": "ABJ-AIRPORT",
        "name": "Aéroport International Félix-Houphouët-Boigny",
        "type": EntryPointType.AIRPORT,
        "iata_code": "ABJ", "icao_code": "DIAP",
        "country": "CI", "city": "Abidjan",
        "lat": 5.2616, "lng": -3.9263,
    },
    {
        "code": "ABJ-PORT",
        "name": "Port Autonome d'Abidjan",
        "type": EntryPointType.SEAPORT,
        "country": "CI", "city": "Abidjan",
        "lat": 5.2789, "lng": -4.0083,
    },
    {
        "code": "SAN-PORT",
        "name": "Port de San-Pédro",
        "type": EntryPointType.SEAPORT,
        "country": "CI", "city": "San-Pédro",
        "lat": 4.7361, "lng": -6.6336,
    },
    {
        "code": "PGA-LAND",
        "name": "Frontière de Pôgô (CI/Mali)",
        "type": EntryPointType.LAND,
        "country": "CI", "city": "Pôgô",
        "lat": 10.0667, "lng": -5.7167,
    },
    {
        "code": "NDA-LAND",
        "name": "Frontière de Niablé (CI/Ghana)",
        "type": EntryPointType.LAND,
        "country": "CI", "city": "Niablé",
        "lat": 6.2333, "lng": -3.2333,
    },
    {
        "code": "AKJ-AIRPORT",
        "name": "Aéroport de Yamoussoukro",
        "type": EntryPointType.AIRPORT,
        "iata_code": "ASK", "icao_code": "DIYO",
        "country": "CI", "city": "Yamoussoukro",
        "lat": 6.9032, "lng": -5.3656,
    },
]


NOTIFICATION_TEMPLATES = [
    {
        "code": "welcome_traveler",
        "name": "Bienvenue voyageur",
        "subject": "Bienvenue en Côte d'Ivoire",
        "body": "Bonjour {traveler_name}, votre arrivée est enregistrée. Pass : {pass_number}.",
        "channels": ["sms", "whatsapp", "email"],
    },
    {
        "code": "quarantine_daily_reminder",
        "name": "Rappel suivi quotidien",
        "subject": "Suivi sanitaire - Jour {day}",
        "body": "Bonjour, n'oubliez pas votre check sanitaire du jour. ID : {traveler_id}.",
        "channels": ["sms", "whatsapp"],
    },
    {
        "code": "pass_expiring",
        "name": "Pass bientôt expiré",
        "subject": "Votre pass sanitaire expire bientôt",
        "body": "Bonjour, votre pass {pass_number} expire le {expires_at}.",
        "channels": ["email", "sms"],
    },
    {
        "code": "alert_authority",
        "name": "Alerte autorité sanitaire",
        "subject": "[ALERTE] {title}",
        "body": "{description}",
        "channels": ["email"],
    },
]


class Command(BaseCommand):
    help = "Seed des données de référence (rôles, maladies, pays, points d'entrée, templates)."

    @transaction.atomic
    def handle(self, *args, **opts):
        self.stdout.write(self.style.MIGRATE_HEADING("> Rôles RBAC"))
        for code, label in RoleCode.choices:
            Role.objects.update_or_create(
                code=code,
                defaults={"name": label, "is_system": True},
            )
        self.stdout.write(self.style.SUCCESS(f"  {len(RoleCode.choices)} rôles synchronisés."))

        self.stdout.write(self.style.MIGRATE_HEADING("> Pays"))
        country_map = {}
        for code, name, region, risk, diseases in COUNTRIES:
            c, _ = Country.objects.update_or_create(
                code=code,
                defaults={
                    "name": name, "region": region,
                    "risk_level": risk, "risk_for_diseases": diseases,
                },
            )
            country_map[code] = c
        self.stdout.write(self.style.SUCCESS(f"  {len(country_map)} pays synchronisés."))

        self.stdout.write(self.style.MIGRATE_HEADING("> Maladies"))
        for d in DISEASES:
            obj, _ = Disease.objects.update_or_create(code=d["code"], defaults=d)
            if obj.code == "EBOLA":
                self._seed_ebola_metadata(obj)
        self.stdout.write(self.style.SUCCESS(f"  {len(DISEASES)} maladies synchronisées."))

        self.stdout.write(self.style.MIGRATE_HEADING("> Points d'entrée"))
        for ep in ENTRY_POINTS:
            country = country_map.get(ep["country"])
            EntryPoint.objects.update_or_create(
                code=ep["code"],
                defaults={
                    "name": ep["name"],
                    "type": ep["type"],
                    "iata_code": ep.get("iata_code", ""),
                    "icao_code": ep.get("icao_code", ""),
                    "country": country,
                    "city": ep.get("city", ""),
                    "location": Point(ep["lng"], ep["lat"], srid=4326),
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"  {len(ENTRY_POINTS)} points d'entrée synchronisés."))

        self.stdout.write(self.style.MIGRATE_HEADING("> Templates de notification"))
        for t in NOTIFICATION_TEMPLATES:
            NotificationTemplate.objects.update_or_create(
                code=t["code"],
                defaults={**t, "is_active": True},
            )
        self.stdout.write(self.style.SUCCESS(f"  {len(NOTIFICATION_TEMPLATES)} templates synchronisés."))

        # Bootstrap super admin si variables d'env présentes
        username = settings.env("DJANGO_SUPERUSER_USERNAME", default=None) if hasattr(settings, "env") else None
        # On évite de dépendre de env si non dispo (settings.env n'existe pas par défaut)
        import os
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
        if email and password and not User.objects.filter(email=email).exists():
            u = User.objects.create_superuser(email=email, password=password, username=username or email)
            from apps.accounts.models import RoleAssignment
            role = Role.objects.get(code=RoleCode.NATIONAL_ADMIN)
            RoleAssignment.objects.get_or_create(user=u, role=role, is_active=True)
            self.stdout.write(self.style.SUCCESS(f"  Superuser créé : {email}"))

        self.stdout.write(self.style.SUCCESS("\nSeed terminé."))

    def _seed_ebola_metadata(self, disease: Disease) -> None:
        for code, label, weight, red in EBOLA_SYMPTOMS:
            Symptom.objects.update_or_create(
                disease=disease, code=code,
                defaults={"label": label, "weight": weight, "is_red_flag": red},
            )
        for code, label, weight in EBOLA_RISK_FACTORS:
            RiskFactor.objects.update_or_create(
                disease=disease, code=code,
                defaults={"label": label, "weight": weight},
            )
