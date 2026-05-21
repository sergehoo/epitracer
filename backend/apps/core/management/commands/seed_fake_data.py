"""Génère un jeu de fake data riche pour tester toute la plateforme EpiTrace.

Crée des voyageurs avec des **clusters volontaires** pour exercer la page
« Mise en relation » :
  * Vol partagé : AF572 (5), KQ560 (3), ET924 (4)
  * Téléphone partagé : 2 paires (urgences)
  * Pays de provenance : 8 venant de RDC, 5 de Guinée, 4 du Nigeria, etc.
  * Cas-contact (CompanionLink) : 2 chaînes
  * Résidence Abidjan : Sofitel Ivoire (4), Pullman (3), Radisson (3)

Crée aussi des enquêtes Ebola, pass sanitaires, alertes et visites de pages
pour exercer le dashboard, la cartographie, la surveillance et l'analytics.

Usage :
    python manage.py seed_fake_data                  # ajoute aux données existantes
    python manage.py seed_fake_data --reset          # purge les voyageurs démo avant
    python manage.py seed_fake_data --count 200      # plus de voyageurs aléatoires
"""
from __future__ import annotations

import random
import string
from datetime import date, datetime, time, timedelta

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.diseases.models import Disease
from apps.ebola.models import (
    EbolaDeclaration, EbolaExposureAssessment, EbolaInvestigation, EbolaSymptomReport,
)
from apps.ebola.services import apply_risk_outcome
from apps.geo.models import Country, EntryPoint
from apps.health_pass.services import issue_pass_for_ebola_investigation
from apps.surveillance.models import AlertSeverity, AlertStatus, HealthAlert
from apps.analytics.models import PageVisit, Portal
from apps.travelers.models import CompanionLink, Traveler, TravelHistoryEntry


# =========================================================================
#                               Datasets
# =========================================================================
FIRST_NAMES_M = [
    "Mamadou", "Jean-Paul", "Ibrahim", "Kouadio", "Bakary", "Adama", "Sékou",
    "Yves", "Désiré", "Vincent", "Thierry", "Olivier", "Yao", "Étienne",
    "Salif", "Souleymane", "Karim", "Lamine", "Ousmane", "Pierre",
]
FIRST_NAMES_F = [
    "Aïcha", "Sarah", "Fatim", "Awa", "Mariam", "Aminata", "Nadège", "Yvette",
    "Christelle", "Akissi", "Affoué", "Adjoua", "Rokia", "Korotoumou",
    "Mireille", "Sandra", "Edwige", "Solange", "Bintou", "Esther",
]
LAST_NAMES = [
    "KONÉ", "OUATTARA", "TRAORÉ", "DIALLO", "BAMBA", "TOURÉ", "KEÏTA",
    "DIABATÉ", "COULIBALY", "DIARRA", "KOUASSI", "YAO", "N'GUESSAN",
    "ASSI", "KOUAMÉ", "BROU", "DJEDJE", "ADJOUMANI", "GBAGBO", "FOFANA",
    "CISSÉ", "DRAMÉ", "SANOGO", "CAMARA", "DOUMBIA", "ZADI",
]
PROFESSIONS = [
    "Commerçant(e)", "Étudiant(e)", "Ingénieur", "Médecin", "Enseignant(e)",
    "Journaliste", "Cadre", "Chauffeur", "Pasteur", "Diplomate",
    "Mineur", "Agent humanitaire", "Marin", "Pilote", "Comptable",
]
HOTELS_ABIDJAN = [
    ("Sofitel Hôtel Ivoire", "Cocody", "Riviera"),
    ("Pullman Abidjan", "Plateau", "Plateau"),
    ("Radisson Blu Abidjan", "Port-Bouët", "Riviera Bonoumin"),
    ("Onomo Hôtel Adjamé", "Adjamé", "Adjamé"),
    ("Heden Golf Hôtel", "Cocody", "Riviera Golf"),
    ("Azalaï Hôtel Abidjan", "Marcory", "Zone 4"),
    ("Novotel Abidjan", "Plateau", "Plateau"),
]
NON_ABJ_CITIES = [
    ("Yamoussoukro", "Yamoussoukro", "Habitat", -5.27, 6.82),
    ("Bouaké", "Bouaké", "Air-France", -5.03, 7.69),
    ("San-Pédro", "San-Pédro", "Centre", -6.63, 4.75),
    ("Korhogo", "Korhogo", "Quartier Soba", -5.62, 9.46),
]
PHONES_SHARED = [
    "+2250712345678",  # partagé par 2 voyageurs (urgence)
    "+2250587654321",  # partagé par 2 voyageurs (urgence)
]
PHONE_PREFIXES = ["+22507", "+22501", "+22505", "+22577"]

FLIGHTS_CLUSTERS = [
    ("AF572", 5, "plane"),   # Paris–Abidjan, 5 voyageurs
    ("KQ560", 3, "plane"),   # Nairobi–Abidjan, 3 voyageurs
    ("ET924", 4, "plane"),   # Addis-Abeba–Abidjan, 4 voyageurs
    ("RAM535", 3, "plane"),  # Casablanca–Abidjan, 3 voyageurs
    ("PORTABJ-22", 4, "boat"),  # bateau partagé
]

ORIGIN_COUNTRIES = {
    "CD": 7,   # RDC : 7 voyageurs (à risque Ebola)
    "GN": 5,   # Guinée
    "NG": 4,   # Nigeria
    "FR": 6,   # France
    "GH": 3,   # Ghana
    "UG": 2,   # Ouganda (Ebola)
    "SL": 2,   # Sierra Leone
    "LR": 2,   # Liberia
}

ABIDJAN_BBOX = (-4.05, 5.27, -3.85, 5.43)  # (lng_min, lat_min, lng_max, lat_max)


def _abidjan_point() -> Point:
    lng = random.uniform(ABIDJAN_BBOX[0], ABIDJAN_BBOX[2])
    lat = random.uniform(ABIDJAN_BBOX[1], ABIDJAN_BBOX[3])
    return Point(lng, lat, srid=4326)


def _short_phone() -> str:
    return random.choice(PHONE_PREFIXES) + "".join(random.choices(string.digits, k=8))


def _short_id_doc() -> str:
    return "P" + "".join(random.choices(string.digits, k=7))


# =========================================================================
#                            Cluster builders
# =========================================================================
class Builder:
    def __init__(self, stdout, style, count_extra: int):
        self.stdout = stdout
        self.style = style
        self.count_extra = count_extra
        self.entry_points: list[EntryPoint] = list(EntryPoint.objects.all())
        self.countries: dict[str, Country] = {c.code: c for c in Country.objects.all()}
        self.ci = self.countries.get("CI")
        self.airport = (
            next((e for e in self.entry_points if e.code == "ABJ-AIRPORT"), None)
            or (self.entry_points[0] if self.entry_points else None)
        )
        self.seaport = next((e for e in self.entry_points if e.code == "ABJ-PORT"), self.airport)
        self.created: list[Traveler] = []

    # ---------- Création d'un voyageur ----------
    def _make_traveler(
        self,
        *,
        flight: str | None = None,
        transport_mode: str = "plane",
        entry_point: EntryPoint | None = None,
        hotel: tuple[str, str, str] | None = None,
        in_abidjan: bool = True,
        phone: str | None = None,
        nationality_code: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        gender: str | None = None,
        days_ago: int | None = None,
    ) -> Traveler:
        gender = gender or random.choice(["M", "F"])
        first_name = first_name or random.choice(
            FIRST_NAMES_M if gender == "M" else FIRST_NAMES_F
        )
        last_name = last_name or random.choice(LAST_NAMES)
        days_ago = random.randint(0, 30) if days_ago is None else days_ago
        arrival = date.today() - timedelta(days=days_ago)
        arrival_time = time(hour=random.randint(6, 23), minute=random.choice([0, 15, 30, 45]))
        nat = self.countries.get(nationality_code) if nationality_code else (
            self.countries.get(random.choice(list(ORIGIN_COUNTRIES.keys())))
        )

        if in_abidjan:
            h = hotel or random.choice(HOTELS_ABIDJAN)
            hotel_name, commune, neighborhood = h
            loc = _abidjan_point()
            city = "Abidjan"
        else:
            ci_city = random.choice(NON_ABJ_CITIES)
            city, commune, neighborhood = ci_city[0], ci_city[1], ci_city[2]
            loc = Point(ci_city[3] + random.uniform(-0.02, 0.02), ci_city[4] + random.uniform(-0.02, 0.02), srid=4326)
            hotel_name = ""

        t = Traveler.objects.create(
            arrival_date=arrival,
            arrival_time=arrival_time,
            transport_mode=transport_mode,
            flight_or_voyage_number=flight or "",
            seat_number=f"{random.randint(1, 35)}{random.choice('ABCDEF')}" if transport_mode == "plane" else "",
            entry_point=entry_point or (self.airport if transport_mode == "plane" else self.seaport),
            last_name=last_name,
            first_name=first_name,
            age=random.randint(18, 70),
            age_unit="years",
            date_of_birth=date(random.randint(1955, 2005), random.randint(1, 12), random.randint(1, 28)),
            gender=gender,
            profession=random.choice(PROFESSIONS),
            id_document_type="passport",
            id_document_number=_short_id_doc(),
            id_document_country=nat,
            nationality=nat,
            phone_mobile=phone or _short_phone(),
            email=f"{first_name.lower()}.{last_name.lower()}@example.ci".replace(" ", ""),
            confinement_city=city,
            confinement_commune=commune,
            confinement_neighborhood=neighborhood,
            confinement_hotel=hotel_name,
            confinement_room_number=str(random.randint(101, 580)) if hotel_name else "",
            emergency_phone_ci=_short_phone(),
            confinement_location=loc,
            consented_data_processing=True,
            signed_at=timezone.now(),
            signed_place=city,
        )
        # Backdate created_at pour les KPI temporels
        Traveler.objects.filter(pk=t.pk).update(
            created_at=timezone.now() - timedelta(days=days_ago),
        )
        self.created.append(t)
        return t

    # ---------- Historique de déplacement ----------
    def _add_history(self, traveler: Traveler, origin_code: str, *, transits: list[str] | None = None):
        origin = self.countries.get(origin_code)
        if origin:
            TravelHistoryEntry.objects.create(
                traveler=traveler,
                role="origin",
                country=origin,
                city=random.choice(["Goma", "Conakry", "Lagos", "Paris", "Accra", "Kampala"]),
                arrival_date=traveler.arrival_date - timedelta(days=random.randint(10, 25)),
                departure_date=traveler.arrival_date - timedelta(days=random.randint(1, 9)),
                duration_text=f"{random.randint(3, 20)} jours",
            )
        for code in (transits or []):
            t_country = self.countries.get(code)
            if t_country:
                TravelHistoryEntry.objects.create(
                    traveler=traveler,
                    role="transit",
                    country=t_country,
                    city="Hub",
                    duration_text="quelques heures",
                )

    # ---------- Enquête Ebola complète ----------
    def _make_investigation(self, traveler: Traveler, *, risk_profile: str = "low") -> EbolaInvestigation:
        """risk_profile in {low, moderate, high, critical}."""
        inv = EbolaInvestigation.objects.create(
            traveler=traveler,
            entry_point=traveler.entry_point,
            status="new",
            notes="Auto-généré par seed_fake_data.",
        )
        exposure = {
            "low":      (False, False, False, False),
            "moderate": (True,  False, False, False),
            "high":     (True,  False, True,  True),
            "critical": (True,  True,  True,  True),
        }[risk_profile]
        EbolaExposureAssessment.objects.create(
            investigation=inv,
            visited_ebola_zone=exposure[0],
            visited_ebola_zone_details="Goma, RDC" if exposure[0] else "",
            contact_with_case=exposure[1],
            attended_funeral_or_touched_corpse=exposure[2],
            visited_ebola_healthcare_facility=exposure[3],
        )
        temp_map = {"low": 36.7, "moderate": 37.6, "high": 38.6, "critical": 39.3}
        symptoms = {
            "low":      dict(fever=False, intense_fatigue=False, muscle_joint_pain=False),
            "moderate": dict(fever=True,  intense_fatigue=True,  muscle_joint_pain=False),
            "high":     dict(fever=True,  intense_fatigue=True,  muscle_joint_pain=True, severe_headache=True),
            "critical": dict(
                fever=True, intense_fatigue=True, muscle_joint_pain=True,
                severe_headache=True, diarrhea_nausea_vomiting=True, unexplained_bleeding=True,
            ),
        }[risk_profile]
        EbolaSymptomReport.objects.create(
            investigation=inv,
            reported_at=timezone.now(),
            temperature_celsius=temp_map[risk_profile],
            **symptoms,
        )
        EbolaDeclaration.objects.create(
            investigation=inv,
            declared_at=timezone.now(),
            declarant_full_name=traveler.full_name,
            signed_place=traveler.confinement_city or "Abidjan",
            truthful_declaration=True,
            consent_data_processing=True,
            consent_health_followup=True,
            consent_quarantine_if_needed=True,
        )
        apply_risk_outcome(inv)
        # Émission d'un pass sanitaire (ne plante pas si Disease EBOLA absent)
        try:
            issue_pass_for_ebola_investigation(inv)
        except Exception as e:  # noqa: BLE001
            self.stdout.write(self.style.WARNING(f"    Pass non émis ({e})"))
        return inv

    # ---------- Cluster builders ----------
    def build_flight_clusters(self):
        self.stdout.write("> Clusters par vol partagé")
        for flight, n, transport in FLIGHTS_CLUSTERS:
            for i in range(n):
                t = self._make_traveler(
                    flight=flight,
                    transport_mode=transport,
                    entry_point=self.airport if transport == "plane" else self.seaport,
                    in_abidjan=True,
                    nationality_code=random.choice(["CI", "FR", "CD", "GN", "NG"]),
                    days_ago=random.randint(0, 10),
                )
                # Profil de risque varié par cluster
                profile = (
                    "high" if flight in ("AF572", "ET924") and i == 0
                    else random.choices(
                        ["low", "moderate", "high"],
                        weights=[5, 3, 2],
                    )[0]
                )
                self._make_investigation(t, risk_profile=profile)
                # Si vol RAM535, lier à provenance CD
                if flight in ("AF572", "RAM535", "ET924") and i < 2:
                    self._add_history(t, "CD", transits=["FR"])
        self.stdout.write(self.style.SUCCESS(f"  → {sum(n for _, n, _ in FLIGHTS_CLUSTERS)} voyageurs créés"))

    def build_phone_clusters(self):
        self.stdout.write("> Clusters par téléphone partagé")
        for shared_phone in PHONES_SHARED:
            for _ in range(2):
                t = self._make_traveler(
                    flight=None,
                    transport_mode=random.choice(["plane", "car"]),
                    in_abidjan=True,
                    phone=shared_phone,
                    days_ago=random.randint(0, 20),
                )
                self._make_investigation(t, risk_profile="moderate")
        self.stdout.write(self.style.SUCCESS(f"  → {len(PHONES_SHARED)*2} voyageurs créés"))

    def build_origin_clusters(self):
        self.stdout.write("> Clusters par pays de provenance")
        for code, n in ORIGIN_COUNTRIES.items():
            for _ in range(n):
                t = self._make_traveler(
                    flight=random.choice(["", "SN230", "AT0532", "TK553"]),
                    in_abidjan=random.random() > 0.25,
                    nationality_code=code,
                    days_ago=random.randint(0, 25),
                )
                self._add_history(t, code, transits=random.choice([[], ["FR"], ["ML"], ["MA"]]))
                profile = "high" if code in ("CD", "UG") and random.random() < 0.4 else "low"
                self._make_investigation(t, risk_profile=profile)
        self.stdout.write(self.style.SUCCESS(f"  → {sum(ORIGIN_COUNTRIES.values())} voyageurs créés"))

    def build_companion_clusters(self):
        self.stdout.write("> Clusters cas-contact (CompanionLink)")
        # Chaîne 1 : 4 voyageurs (famille élargie)
        family = [self._make_traveler(
            in_abidjan=True,
            hotel=HOTELS_ABIDJAN[0],
            flight="ET924",
            transport_mode="plane",
            days_ago=random.randint(0, 5),
        ) for _ in range(4)]
        for i in range(1, 4):
            CompanionLink.objects.create(
                traveler=family[0], companion=family[i],
                relationship=random.choice(["Conjoint(e)", "Enfant", "Frère/Sœur"]),
            )
        # Une enquête modérée pour le chef de famille
        self._make_investigation(family[0], risk_profile="moderate")
        for member in family[1:]:
            self._make_investigation(member, risk_profile="low")

        # Chaîne 2 : 3 voyageurs (collègues)
        team = [self._make_traveler(
            in_abidjan=True, hotel=HOTELS_ABIDJAN[1],
            flight="AF572", transport_mode="plane",
            days_ago=random.randint(0, 6),
        ) for _ in range(3)]
        CompanionLink.objects.create(traveler=team[0], companion=team[1], relationship="Collègue")
        CompanionLink.objects.create(traveler=team[1], companion=team[2], relationship="Collègue")
        for member in team:
            self._make_investigation(member, risk_profile=random.choice(["low", "moderate"]))
        self.stdout.write(self.style.SUCCESS(f"  → 2 chaînes (4 + 3 voyageurs)"))

    def build_hotel_clusters(self):
        self.stdout.write("> Clusters résidence Abidjan (hôtel)")
        for hotel in HOTELS_ABIDJAN[:3]:  # 3 hôtels, ~3-4 chacun
            n = random.randint(3, 4)
            for _ in range(n):
                t = self._make_traveler(
                    hotel=hotel,
                    in_abidjan=True,
                    flight=random.choice(["", "AT0532", "TP1543"]),
                    days_ago=random.randint(0, 15),
                )
                self._make_investigation(t, risk_profile=random.choices(
                    ["low", "moderate", "high"], weights=[6, 3, 1])[0])
        self.stdout.write(self.style.SUCCESS("  → ~10 voyageurs créés"))

    def build_random_extras(self):
        if self.count_extra <= 0:
            return
        self.stdout.write(f"> {self.count_extra} voyageurs aléatoires supplémentaires")
        for _ in range(self.count_extra):
            t = self._make_traveler(
                flight=random.choice(["", "SN230", "AT0532", "TK553", "DT4536"]),
                transport_mode=random.choices(["plane", "car", "bus", "boat"], weights=[7, 2, 1, 1])[0],
                in_abidjan=random.random() > 0.3,
                days_ago=random.randint(0, 60),
            )
            profile = random.choices(
                ["low", "moderate", "high", "critical"], weights=[6, 3, 2, 1],
            )[0]
            self._make_investigation(t, risk_profile=profile)
        self.stdout.write(self.style.SUCCESS(f"  → {self.count_extra} voyageurs créés"))

    # ---------- Alertes ----------
    def build_alerts(self):
        self.stdout.write("> Alertes sanitaires")
        ebola = Disease.objects.filter(code="EBOLA").first()
        # Alerte critique sur le vol AF572 (cluster à risque)
        HealthAlert.objects.create(
            code="cluster_vol_af572",
            title="Cluster voyageurs vol AF572",
            description="5 voyageurs partagent le vol AF572 dont 1 cas suspect (risque élevé).",
            severity=AlertSeverity.HIGH,
            status=AlertStatus.OPEN,
            disease=ebola,
            entry_point=self.airport,
        )
        HealthAlert.objects.create(
            code="provenance_rdc_pic",
            title="Pic de voyageurs en provenance de RDC",
            description="7 voyageurs en provenance de RDC sur les 30 derniers jours.",
            severity=AlertSeverity.MEDIUM,
            status=AlertStatus.OPEN,
            disease=ebola,
        )
        HealthAlert.objects.create(
            code="signalement_symptomes",
            title="Voyageur symptomatique — Sofitel Ivoire",
            description="Cas suspect avec fièvre 39.1°C détecté à l'hôtel Sofitel Ivoire.",
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.OPEN,
            disease=ebola,
        )
        HealthAlert.objects.create(
            code="info_routine",
            title="Synthèse hebdomadaire",
            description="Tableau de bord hebdomadaire disponible.",
            severity=AlertSeverity.INFO,
            status=AlertStatus.RESOLVED,
        )
        self.stdout.write(self.style.SUCCESS("  → 4 alertes créées"))

    # ---------- Visites de pages (analytics) ----------
    def build_page_visits(self):
        self.stdout.write("> Visites de pages (analytics)")
        paths_public = ["/", "/voyageur", "/pass", "/verifier", "/assistance"]
        paths_admin = ["/dashboard", "/surveillance", "/cartographie", "/visites", "/relations"]
        languages = ["fr-FR", "fr", "en-US", "en-GB", "ar", "es"]
        countries = [
            ("CI", "Côte d'Ivoire"), ("FR", "France"), ("US", "États-Unis"),
            ("GH", "Ghana"), ("NG", "Nigeria"), ("CD", "RDC"),
            ("ML", "Mali"), ("SN", "Sénégal"), ("MA", "Maroc"),
        ]
        sessions = [f"sess-{i:04d}" for i in range(30)]
        total = 0
        now = timezone.now()
        for d in range(45):  # 45 jours d'historique
            day = now - timedelta(days=d)
            n = random.randint(20, 80)
            for _ in range(n):
                is_admin = random.random() < 0.2
                path = random.choice(paths_admin if is_admin else paths_public)
                cc, cname = random.choice(countries)
                pv = PageVisit.objects.create(
                    session_id=random.choice(sessions),
                    portal=Portal.ADMIN if is_admin else Portal.PUBLIC,
                    host="destinationci.com" if not is_admin else "admin.veillesanitaire.com",
                    path=path,
                    referrer="https://google.com/" if random.random() < 0.3 else "",
                    user_agent="Mozilla/5.0 (demo)",
                    ip_address=f"196.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}",
                    country_code=cc,
                    country_name=cname,
                    language=random.choice(languages),
                    timezone="Africa/Abidjan",
                    is_bot=False,
                )
                # Backdate
                PageVisit.objects.filter(pk=pv.pk).update(created_at=day)
                total += 1
        self.stdout.write(self.style.SUCCESS(f"  → {total} visites créées sur 45 jours"))


# =========================================================================
#                              Command
# =========================================================================
class Command(BaseCommand):
    help = "Génère un jeu complet de fake data réalistes (clusters, enquêtes, alertes, visites)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset", action="store_true",
            help="Purge toutes les données voyageurs/enquêtes/pass/alertes/visites avant de re-seeder.",
        )
        parser.add_argument(
            "--count", type=int, default=20,
            help="Voyageurs aléatoires supplémentaires (au-delà des clusters volontaires).",
        )
        parser.add_argument(
            "--seed", type=int, default=42,
            help="Seed du RNG pour reproductibilité.",
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        random.seed(opts["seed"])

        if opts["reset"]:
            self.stdout.write(self.style.WARNING("> RESET en cours…"))
            HealthAlert.objects.all().delete()
            PageVisit.objects.all().delete()
            # Cascade : EbolaInvestigation → Exposure/Symptom/Declaration ; HealthPass aussi
            EbolaInvestigation.objects.all().delete()
            CompanionLink.objects.all().delete()
            TravelHistoryEntry.objects.all().delete()
            Traveler.objects.all().delete()
            self.stdout.write(self.style.WARNING("  Données purgées."))

        # Pré-requis : références (countries + entry points + disease)
        if Country.objects.count() == 0 or EntryPoint.objects.count() == 0:
            self.stdout.write(self.style.ERROR(
                "Pré-requis manquants : lancez d'abord `python manage.py seed_reference_data`."
            ))
            return

        builder = Builder(self.stdout, self.style, count_extra=opts["count"])

        builder.build_flight_clusters()
        builder.build_phone_clusters()
        builder.build_origin_clusters()
        builder.build_companion_clusters()
        builder.build_hotel_clusters()
        builder.build_random_extras()
        builder.build_alerts()
        builder.build_page_visits()

        self.stdout.write(self.style.SUCCESS(
            f"\nSeed terminé : {len(builder.created)} voyageurs créés au total."
        ))
        self.stdout.write(self.style.SUCCESS(
            "→ Lancez le portail admin et visitez /dashboard, /surveillance, /cartographie, /relations, /visites."
        ))
