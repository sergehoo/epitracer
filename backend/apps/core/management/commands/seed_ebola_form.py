"""Crée (ou met à jour) le formulaire d'enquête Ebola dynamique aligné DOCX INHP.

Source : "FICHE PASSAGER EBOLA RDC 2026 DEF" — République de Côte d'Ivoire,
Ministère de la Santé, INHP. Reflète strictement les 7 sections.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.diseases.models import Disease
from apps.forms.models import (
    DynamicForm,
    FieldOption,
    FieldType,
    FormField,
    FormSection,
)


FORM = {
    "code": "ebola_inhp_v1",
    "title": "FICHE DE RENSEIGNEMENT PASSAGER — Maladie à Virus Ebola (MVE)",
    "description": (
        "À remplir obligatoirement par tout passager à l'arrivée sur le territoire national. "
        "Formulaire officiel INHP — République de Côte d'Ivoire."
    ),
    "version": 1,
    "sections": [
        # ---------------------------------------------------------------
        # SECTION 1 — Informations sur le voyage
        # ---------------------------------------------------------------
        {
            "code": "voyage", "title": "1. Informations sur le voyage", "order": 1, "fields": [
                {"code": "arrival_date", "label": "Date d'arrivée", "type": FieldType.DATE, "required": True},
                {"code": "flight_or_voyage_number", "label": "N° de vol / Moyen de transport",
                 "type": FieldType.TEXT, "required": True},
                {"code": "seat_number", "label": "N° de siège", "type": FieldType.TEXT},
                {"code": "entry_point", "label": "Point d'entrée", "type": FieldType.TEXT, "required": True},
            ],
        },
        # ---------------------------------------------------------------
        # SECTION 2 — Identité et contacts du passager
        # ---------------------------------------------------------------
        {
            "code": "identite", "title": "2. Identité et contacts du passager", "order": 2, "fields": [
                {"code": "last_name", "label": "Nom de famille", "type": FieldType.TEXT, "required": True},
                {"code": "first_name", "label": "Prénoms", "type": FieldType.TEXT, "required": True},
                {"code": "age", "label": "Âge", "type": FieldType.INTEGER, "required": True, "min": 0, "max": 130},
                {"code": "age_unit", "label": "Unité (Ans / Mois)", "type": FieldType.RADIO,
                 "options": [("years", "Ans"), ("months", "Mois")], "required": True},
                {"code": "gender", "label": "Sexe", "type": FieldType.RADIO,
                 "options": [("M", "Masculin"), ("F", "Féminin")], "required": True},
                {"code": "profession", "label": "Profession", "type": FieldType.TEXT, "required": True},
                {"code": "id_document_number", "label": "N° Passeport", "type": FieldType.TEXT, "required": True},
                {"code": "phone_mobile", "label": "Téléphone Portable", "type": FieldType.PHONE, "required": True},
                {"code": "email", "label": "Adresse E-mail", "type": FieldType.EMAIL},
                {"code": "postal_address", "label": "Adresse Postale", "type": FieldType.TEXTAREA},
            ],
        },
        # ---------------------------------------------------------------
        # SECTION 3 — Historique des déplacements (21 derniers jours)
        # ---------------------------------------------------------------
        {
            "code": "historique", "title": "3. Historique des déplacements (3 dernières semaines / 21 derniers jours)",
            "order": 3, "fields": [
                # Provenance
                {"code": "origin_country", "label": "Pays de provenance", "type": FieldType.COUNTRY, "required": True},
                {"code": "origin_city", "label": "Ville", "type": FieldType.TEXT, "required": True},
                {"code": "origin_residence_address", "label": "Adresse de résidence là-bas", "type": FieldType.TEXT},
                {"code": "origin_hotel_room", "label": "Hôtel / N° Chambre", "type": FieldType.TEXT},
                {"code": "origin_duration", "label": "Durée du séjour dans ce pays", "type": FieldType.TEXT,
                 "required": True},
                # Transit
                {"code": "transit_country", "label": "Pays de transit", "type": FieldType.COUNTRY},
                {"code": "transit_city", "label": "Ville (transit)", "type": FieldType.TEXT},
                {"code": "transit_residence_address", "label": "Adresse de résidence là-bas (transit)",
                 "type": FieldType.TEXT},
                {"code": "transit_hotel_room", "label": "Hôtel / N° Chambre (transit)", "type": FieldType.TEXT},
                {"code": "transit_duration", "label": "Durée du transit dans ce pays", "type": FieldType.TEXT},
                # Autres pays visités
                {"code": "other_country_1", "label": "Pays 1 visité (3 dernières semaines)", "type": FieldType.COUNTRY},
                {"code": "other_country_1_period", "label": "Période de visite Pays 1 (Du ../../2026 au ../../2026)",
                 "type": FieldType.TEXT},
                {"code": "other_country_2", "label": "Pays 2 visité (3 dernières semaines)", "type": FieldType.COUNTRY},
                {"code": "other_country_2_period", "label": "Période de visite Pays 2 (Du ../../2026 au ../../2026)",
                 "type": FieldType.TEXT},
            ],
        },
        # ---------------------------------------------------------------
        # SECTION 4 — Adresse de résidence et confinement en CI
        # ---------------------------------------------------------------
        {
            "code": "confinement", "title": "4. Adresse de résidence et confinement en Côte d'Ivoire",
            "order": 4, "fields": [
                {"code": "city", "label": "Ville", "type": FieldType.TEXT, "required": True},
                {"code": "commune", "label": "Commune", "type": FieldType.TEXT, "required": True},
                {"code": "neighborhood", "label": "Quartier", "type": FieldType.TEXT, "required": True},
                {"code": "street_number", "label": "N° de Rue", "type": FieldType.TEXT},
                {"code": "lot", "label": "N° Lot", "type": FieldType.TEXT},
                {"code": "hotel", "label": "Hôtel / Lieu d'hébergement", "type": FieldType.TEXT},
                {"code": "room_number", "label": "N° de Chambre", "type": FieldType.TEXT},
                {"code": "emergency_phone_ci", "label": "Téléphone d'urgence obligatoire en Côte d'Ivoire",
                 "type": FieldType.PHONE, "required": True},
                {"code": "geoloc", "label": "Géolocalisation (lat,lng)", "type": FieldType.GEOLOCATION},
            ],
        },
        # ---------------------------------------------------------------
        # SECTION 5 — Évaluation épidémiologique du risque (21 derniers jours)
        # ---------------------------------------------------------------
        {
            "code": "exposition", "title": "5. Évaluation Épidémiologique du Risque (21 derniers jours)",
            "order": 5, "fields": [
                {"code": "visited_ebola_zone",
                 "label": "Avez-vous séjourné ou transité par une zone touchée par l'épidémie d'Ebola ?",
                 "type": FieldType.BOOLEAN, "required": True, "risk_weight": 5},
                {"code": "visited_ebola_zone_details",
                 "label": "Si oui, précisez la ville / région et le pays",
                 "type": FieldType.TEXT},
                {"code": "contact_with_case",
                 "label": "Avez-vous été en contact avec une personne malade ou suspectée d'avoir Ebola ?",
                 "type": FieldType.BOOLEAN, "required": True, "risk_weight": 7},
                {"code": "attended_funeral_or_touched_corpse",
                 "label": "Avez-vous assisté à des funérailles ou touché une dépouille humaine ?",
                 "type": FieldType.BOOLEAN, "required": True, "risk_weight": 4},
                {"code": "visited_ebola_healthcare_facility",
                 "label": "Avez-vous fréquenté un établissement de soins traitant des patients Ebola ?",
                 "type": FieldType.BOOLEAN, "required": True, "risk_weight": 3},
            ],
        },
        # ---------------------------------------------------------------
        # SECTION 6 — État de santé (48h)
        # ---------------------------------------------------------------
        {
            "code": "symptomes", "title": "6. État de santé (Symptômes ressentis au cours des dernières 48 heures)",
            "order": 6, "fields": [
                {"code": "fever", "label": "Fièvre (≥ 38°C) ou sensation de forte chaleur",
                 "type": FieldType.BOOLEAN, "required": True, "risk_weight": 2},
                {"code": "intense_fatigue", "label": "Fatigue intense, faiblesse généralisée inexpliquée",
                 "type": FieldType.BOOLEAN, "required": True, "risk_weight": 1},
                {"code": "muscle_joint_pain", "label": "Douleurs musculaires, articulaires ou courbatures",
                 "type": FieldType.BOOLEAN, "required": True, "risk_weight": 1},
                {"code": "severe_headache", "label": "Maux de tête intenses (Céphalées)",
                 "type": FieldType.BOOLEAN, "required": True, "risk_weight": 1},
                {"code": "sore_throat_or_abdominal", "label": "Maux de gorge ou douleurs abdominales (estomac)",
                 "type": FieldType.BOOLEAN, "required": True, "risk_weight": 1},
                {"code": "diarrhea_nausea_vomiting", "label": "Diarrhée, nausées ou vomissements fréquents",
                 "type": FieldType.BOOLEAN, "required": True, "risk_weight": 2},
                {"code": "unexplained_bleeding",
                 "label": "Saignements inexpliqués (nez, gencives, peau, urines, selles)",
                 "type": FieldType.BOOLEAN, "required": True, "risk_weight": 5},
                {"code": "temperature", "label": "Température mesurée (°C)", "type": FieldType.NUMBER,
                 "min": 30, "max": 45},
            ],
        },
        # ---------------------------------------------------------------
        # SECTION 7 — Certification + signature
        # ---------------------------------------------------------------
        {
            "code": "declaration", "title": "7. Certification & signature",
            "description": "Je certifie sur l'honneur l'exactitude des renseignements portés sur cette fiche.",
            "order": 7, "fields": [
                {"code": "signed_place", "label": "Fait à", "type": FieldType.TEXT, "required": True},
                {"code": "signed_at", "label": "Date", "type": FieldType.DATE, "required": True},
                {"code": "truthful", "label": "Je certifie sur l'honneur l'exactitude des renseignements",
                 "type": FieldType.BOOLEAN, "required": True},
                {"code": "signature", "label": "Signature du passager", "type": FieldType.SIGNATURE,
                 "required": True},
            ],
        },
    ],
}


class Command(BaseCommand):
    help = "Crée le formulaire d'enquête Ebola dynamique aligné strictement sur la fiche INHP."

    @transaction.atomic
    def handle(self, *args, **opts):
        disease = Disease.objects.filter(code="EBOLA").first()
        if disease is None:
            self.stderr.write(self.style.ERROR(
                "La maladie EBOLA n'existe pas. Exécuter d'abord seed_reference_data."
            ))
            return

        form, _ = DynamicForm.objects.update_or_create(
            disease=disease,
            code=FORM["code"],
            version=FORM["version"],
            defaults={
                "title": FORM["title"],
                "description": FORM["description"],
                "is_active": True,
                "is_default": True,
            },
        )

        form.sections.all().delete()
        for sec in FORM["sections"]:
            s = FormSection.objects.create(
                form=form, code=sec["code"], title=sec["title"],
                description=sec.get("description", ""), order=sec["order"],
            )
            for idx, f in enumerate(sec["fields"]):
                field = FormField.objects.create(
                    section=s,
                    code=f["code"], label=f["label"], type=f["type"],
                    is_required=f.get("required", False), order=idx,
                    risk_weight=f.get("risk_weight", 0),
                    min_value=f.get("min"), max_value=f.get("max"),
                    placeholder=f.get("placeholder", ""),
                )
                for v_idx, (val, lbl) in enumerate(f.get("options", [])):
                    FieldOption.objects.create(field=field, value=val, label=lbl, order=v_idx)

        total_fields = sum(len(s["fields"]) for s in FORM["sections"])
        self.stdout.write(self.style.SUCCESS(
            f"Formulaire Ebola synchronisé : {form.code} v{form.version} ({total_fields} champs, 7 sections)."
        ))
