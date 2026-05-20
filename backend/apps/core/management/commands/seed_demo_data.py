"""Génère un jeu de données de démo (5 voyageurs + 1 enquête Ebola high)."""
from __future__ import annotations

from datetime import date

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.ebola.models import EbolaExposureAssessment, EbolaInvestigation, EbolaSymptomReport
from apps.ebola.services import apply_risk_outcome
from apps.geo.models import Country, EntryPoint
from apps.travelers.models import Traveler


class Command(BaseCommand):
    help = "Crée 5 voyageurs et 1 enquête Ebola de démo."

    def handle(self, *args, **opts):
        ep = EntryPoint.objects.filter(code="ABJ-AIRPORT").first()
        cd = Country.objects.filter(code="CD").first()
        ci = Country.objects.filter(code="CI").first()

        names = [
            ("Aïcha", "DIALLO", "F"),
            ("Mamadou", "KONÉ", "M"),
            ("Sarah", "MENSAH", "F"),
            ("Jean-Paul", "OUATTARA", "M"),
            ("Fatim", "TRAORÉ", "F"),
        ]
        travelers = []
        today = date.today()
        for first, last, sex in names:
            t = Traveler.objects.create(
                first_name=first, last_name=last, gender=sex,
                nationality=ci,
                id_document_number=f"P{abs(hash(first+last)) % 10**6:06d}",
                phone_mobile="+22507" + str(abs(hash(first+last)))[:8],
                email=f"{first.lower()}.{last.lower()}@example.ci",
                arrival_date=today,
                entry_point=ep,
                confinement_city="Abidjan",
                confinement_commune="Cocody",
                confinement_neighborhood="II Plateaux",
                confinement_location=Point(-3.9663, 5.3653, srid=4326),
                consented_data_processing=True,
            )
            travelers.append(t)
        self.stdout.write(self.style.SUCCESS(f"  {len(travelers)} voyageurs créés"))

        # Une enquête à haut risque (alignée DOCX)
        inv = EbolaInvestigation.objects.create(
            traveler=travelers[0],
            entry_point=ep,
            status="new",
            notes="Patient en provenance de RDC, signes cliniques à surveiller.",
        )
        EbolaExposureAssessment.objects.create(
            investigation=inv,
            visited_ebola_zone=True,
            visited_ebola_zone_details="Goma, RDC",
            contact_with_case=False,
            attended_funeral_or_touched_corpse=True,
            visited_ebola_healthcare_facility=True,
        )
        EbolaSymptomReport.objects.create(
            investigation=inv,
            reported_at=timezone.now(),
            temperature_celsius=39.1,
            fever=True,
            intense_fatigue=True,
            severe_headache=True,
            diarrhea_nausea_vomiting=True,
        )
        apply_risk_outcome(inv)
        self.stdout.write(self.style.SUCCESS(
            f"  Enquête {inv.case_number} créée : score={inv.risk_score} ({inv.risk_level}) - statut={inv.status}"
        ))
