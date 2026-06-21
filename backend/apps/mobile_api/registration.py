"""Endpoints publics pour le flow d'enregistrement voyageur mobile.

L'app mobile a besoin de connaître la liste des formulaires d'enquête actifs
(Ebola, etc.) AVANT que l'utilisateur soit authentifié. Cette vue expose un
résumé léger : id, code, titre, maladie associée, description, lien web.

Phase 8B — En plus du picker, on expose :
    GET  /api/mobile/forms/<code>/schema/         schéma complet du formulaire
    POST /api/mobile/forms/<code>/submissions/    soumission + délivrance du pass

Aucun PII n'est exposé ici — uniquement des métadonnées de formulaires
publiables (le schema n'est PAS du PII).
"""
from __future__ import annotations

import logging

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class ActiveFormsListView(APIView):
    """GET /api/mobile/registration/forms/

    Retourne la liste des formulaires d'enquête actifs (lecture publique).
    Inclut l'URL de remplissage web vers destinationci.com pour redirection
    depuis l'app mobile.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "registration_forms"

    def get(self, request):
        try:
            from apps.forms.models import DynamicForm
        except Exception:
            return Response({"results": []})

        # URL du portail public — paramètre projet ou défaut prod
        public_base = getattr(
            settings, "PUBLIC_WEB_BASE_URL", "https://destinationci.com",
        ).rstrip("/")

        qs = (
            DynamicForm.objects.filter(is_active=True)
            .select_related("disease")
            .order_by("-is_default", "title")
        )

        out = []
        for f in qs:
            disease_code = getattr(f.disease, "code", None) if f.disease_id else None
            disease_name = getattr(f.disease, "name", None) if f.disease_id else None
            # URL canonique du formulaire web — voyageur enregistrement
            # Si le code est "ebola_arrival" ou similaire, on garde l'URL générique
            # sauf si un slug spécifique est défini.
            web_url = f"{public_base}/voyageur"
            if f.code:
                web_url = f"{public_base}/voyageur?form={f.code}"

            out.append({
                "id": f.pk,
                "code": f.code,
                "title": f.title,
                "description": getattr(f, "description", "") or "",
                "disease_code": disease_code,
                "disease_name": disease_name,
                "is_default": bool(getattr(f, "is_default", False)),
                "web_url": web_url,
            })

        # Fallback : si aucun formulaire actif en base, on expose au moins le
        # formulaire d'enregistrement générique pour ne jamais bloquer le user.
        if not out:
            out.append({
                "id": None,
                "code": "default",
                "title": "Enregistrement voyageur — Côte d'Ivoire",
                "description": "Formulaire d'enregistrement sanitaire à remplir avant ou à l'arrivée.",
                "disease_code": None,
                "disease_name": None,
                "is_default": True,
                "web_url": f"{public_base}/voyageur",
            })

        return Response({"results": out, "count": len(out)})


# =============================================================================
#                Phase 8B — Schéma complet + soumission native
# =============================================================================

# ----- Schéma de secours hardcodé (formulaire Ebola officiel INHP) ----------
# Utilisé quand aucun DynamicForm n'est en base. Permet à l'app mobile d'avoir
# TOUJOURS un formulaire à rendre, même fraichement déployée. Doit rester
# strictement aligné sur backend/apps/core/management/commands/seed_ebola_form.py.
_FALLBACK_EBOLA_SCHEMA: dict = {
    "id": None,
    "code": "ebola_inhp_v1",
    "title": "FICHE DE RENSEIGNEMENT PASSAGER — Maladie à Virus Ebola",
    "description": (
        "À remplir obligatoirement par tout passager à l'arrivée sur le territoire national. "
        "Formulaire officiel INHP — République de Côte d'Ivoire."
    ),
    "version": 1,
    "disease_code": "EBOLA",
    "is_active": True,
    "is_default": True,
    "sections": [
        {
            "id": 1, "code": "voyage", "title": "1. Informations sur le voyage",
            "description": "", "order": 1,
            "fields_list": [
                {"id": 101, "code": "arrival_date", "label": "Date d'arrivée",
                 "type": "date", "is_required": True, "order": 0,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 102, "code": "flight_or_voyage_number",
                 "label": "N° de vol / Moyen de transport",
                 "type": "text", "is_required": True, "order": 1,
                 "help_text": "", "placeholder": "Ex. AF703", "options": [], "conditions": []},
                {"id": 103, "code": "seat_number", "label": "N° de siège",
                 "type": "text", "is_required": False, "order": 2,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 104, "code": "entry_point", "label": "Point d'entrée",
                 "type": "text", "is_required": True, "order": 3,
                 "help_text": "Aéroport / port / poste frontière", "placeholder": "",
                 "options": [], "conditions": []},
            ],
        },
        {
            "id": 2, "code": "identite", "title": "2. Identité et contacts du passager",
            "description": "", "order": 2,
            "fields_list": [
                {"id": 201, "code": "last_name", "label": "Nom de famille",
                 "type": "text", "is_required": True, "order": 0,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 202, "code": "first_name", "label": "Prénoms",
                 "type": "text", "is_required": True, "order": 1,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 203, "code": "age", "label": "Âge",
                 "type": "integer", "is_required": True, "order": 2,
                 "min_value": 0, "max_value": 130,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 204, "code": "age_unit", "label": "Unité",
                 "type": "radio", "is_required": True, "order": 3,
                 "help_text": "", "placeholder": "", "conditions": [],
                 "options": [
                     {"id": 1, "value": "years", "label": "Ans", "order": 0},
                     {"id": 2, "value": "months", "label": "Mois", "order": 1},
                 ]},
                {"id": 205, "code": "gender", "label": "Sexe",
                 "type": "radio", "is_required": True, "order": 4,
                 "help_text": "", "placeholder": "", "conditions": [],
                 "options": [
                     {"id": 3, "value": "M", "label": "Masculin", "order": 0},
                     {"id": 4, "value": "F", "label": "Féminin", "order": 1},
                 ]},
                {"id": 206, "code": "profession", "label": "Profession",
                 "type": "text", "is_required": True, "order": 5,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 207, "code": "id_document_number", "label": "N° Passeport",
                 "type": "text", "is_required": True, "order": 6,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 208, "code": "phone_mobile", "label": "Téléphone Portable",
                 "type": "phone", "is_required": True, "order": 7,
                 "help_text": "", "placeholder": "+225 …", "options": [], "conditions": []},
                {"id": 209, "code": "email", "label": "Adresse E-mail",
                 "type": "email", "is_required": False, "order": 8,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 210, "code": "postal_address", "label": "Adresse Postale",
                 "type": "textarea", "is_required": False, "order": 9,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
            ],
        },
        {
            "id": 3, "code": "historique",
            "title": "3. Historique des déplacements (21 derniers jours)",
            "description": "", "order": 3,
            "fields_list": [
                {"id": 301, "code": "origin_country", "label": "Pays de provenance",
                 "type": "country", "is_required": True, "order": 0,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 302, "code": "origin_city", "label": "Ville",
                 "type": "text", "is_required": True, "order": 1,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 303, "code": "origin_duration", "label": "Durée du séjour",
                 "type": "text", "is_required": True, "order": 2,
                 "help_text": "Ex. 12 jours", "placeholder": "",
                 "options": [], "conditions": []},
            ],
        },
        {
            "id": 4, "code": "confinement",
            "title": "4. Adresse de résidence et confinement en Côte d'Ivoire",
            "description": "", "order": 4,
            "fields_list": [
                {"id": 401, "code": "city", "label": "Ville",
                 "type": "text", "is_required": True, "order": 0,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 402, "code": "commune", "label": "Commune",
                 "type": "text", "is_required": True, "order": 1,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 403, "code": "neighborhood", "label": "Quartier",
                 "type": "text", "is_required": True, "order": 2,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 404, "code": "hotel", "label": "Hôtel / Lieu d'hébergement",
                 "type": "text", "is_required": False, "order": 3,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 405, "code": "emergency_phone_ci",
                 "label": "Téléphone d'urgence en Côte d'Ivoire",
                 "type": "phone", "is_required": True, "order": 4,
                 "help_text": "", "placeholder": "+225 …", "options": [], "conditions": []},
                {"id": 406, "code": "whatsapp_phone", "label": "Téléphone WhatsApp",
                 "type": "phone", "is_required": True, "order": 5,
                 "help_text": "Pour vous joindre pendant les 21 jours de suivi",
                 "placeholder": "+225 …", "options": [], "conditions": []},
                {"id": 407, "code": "geoloc", "label": "Géolocalisation (lat,lng)",
                 "type": "geolocation", "is_required": False, "order": 6,
                 "help_text": "Position de votre lieu de confinement",
                 "placeholder": "", "options": [], "conditions": []},
            ],
        },
        {
            "id": 5, "code": "exposition",
            "title": "5. Évaluation Épidémiologique du Risque",
            "description": "21 derniers jours", "order": 5,
            "fields_list": [
                {"id": 501, "code": "visited_ebola_zone",
                 "label": "Avez-vous séjourné dans une zone touchée par l'épidémie ?",
                 "type": "boolean", "is_required": True, "order": 0,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 502, "code": "visited_ebola_zone_details",
                 "label": "Si oui, précisez la ville/région et le pays",
                 "type": "text", "is_required": False, "order": 1,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 503, "code": "contact_with_case",
                 "label": "Avez-vous été en contact avec une personne malade ou suspectée ?",
                 "type": "boolean", "is_required": True, "order": 2,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 504, "code": "attended_funeral_or_touched_corpse",
                 "label": "Avez-vous assisté à des funérailles ou touché une dépouille ?",
                 "type": "boolean", "is_required": True, "order": 3,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 505, "code": "visited_ebola_healthcare_facility",
                 "label": "Avez-vous fréquenté un établissement de soins traitant Ebola ?",
                 "type": "boolean", "is_required": True, "order": 4,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
            ],
        },
        {
            "id": 6, "code": "symptomes",
            "title": "6. État de santé (48 dernières heures)",
            "description": "", "order": 6,
            "fields_list": [
                {"id": 601, "code": "fever",
                 "label": "Fièvre (≥ 38°C) ou sensation de forte chaleur",
                 "type": "boolean", "is_required": True, "order": 0,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 602, "code": "intense_fatigue",
                 "label": "Fatigue intense, faiblesse généralisée",
                 "type": "boolean", "is_required": True, "order": 1,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 603, "code": "muscle_joint_pain",
                 "label": "Douleurs musculaires, articulaires ou courbatures",
                 "type": "boolean", "is_required": True, "order": 2,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 604, "code": "severe_headache",
                 "label": "Maux de tête intenses",
                 "type": "boolean", "is_required": True, "order": 3,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 605, "code": "sore_throat_or_abdominal",
                 "label": "Maux de gorge ou douleurs abdominales",
                 "type": "boolean", "is_required": True, "order": 4,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 606, "code": "diarrhea_nausea_vomiting",
                 "label": "Diarrhée, nausées ou vomissements",
                 "type": "boolean", "is_required": True, "order": 5,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 607, "code": "unexplained_bleeding",
                 "label": "Saignements inexpliqués",
                 "type": "boolean", "is_required": True, "order": 6,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 608, "code": "temperature",
                 "label": "Température mesurée (°C)",
                 "type": "number", "is_required": False, "order": 7,
                 "min_value": 30, "max_value": 45,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
            ],
        },
        {
            "id": 7, "code": "declaration", "title": "7. Certification & signature",
            "description": "Je certifie sur l'honneur l'exactitude des renseignements.",
            "order": 7,
            "fields_list": [
                {"id": 701, "code": "signed_place", "label": "Fait à",
                 "type": "text", "is_required": True, "order": 0,
                 "help_text": "", "placeholder": "Abidjan", "options": [], "conditions": []},
                {"id": 702, "code": "signed_at", "label": "Date",
                 "type": "date", "is_required": True, "order": 1,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 703, "code": "truthful",
                 "label": "Je certifie sur l'honneur l'exactitude des renseignements",
                 "type": "boolean", "is_required": True, "order": 2,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
                {"id": 704, "code": "signature", "label": "Signature du passager",
                 "type": "signature", "is_required": True, "order": 3,
                 "help_text": "", "placeholder": "", "options": [], "conditions": []},
            ],
        },
    ],
}


class MobileFormSchemaView(APIView):
    """GET /api/mobile/forms/<code>/schema/

    Renvoie le schéma complet (sections + fields + options + conditions) du
    formulaire `code`. Si rien en base, sert le schéma de secours Ebola.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mobile_form_schema"

    def get(self, request, code: str):
        try:
            from apps.forms.models import DynamicForm
            from apps.forms.serializers import DynamicFormSerializer
        except Exception:
            return Response(_FALLBACK_EBOLA_SCHEMA)

        qs = (
            DynamicForm.objects.filter(code=code, is_active=True)
            .select_related("disease")
            .prefetch_related("sections__fields__options", "sections__fields__conditions")
            .order_by("-version")
        )
        form = qs.first()
        if form is None:
            # Pas trouvé en base → fallback hardcodé. Permet aux tests mobile
            # de tourner sans seed Ebola.
            logger.info("mobile.form_schema fallback for code=%s", code)
            return Response(_FALLBACK_EBOLA_SCHEMA)

        return Response(DynamicFormSerializer(form).data)


class MobileFormSubmissionView(APIView):
    """POST /api/mobile/forms/<code>/submissions/

    Body :
        {
            "answers": { "<field_code>": <value>, ... },
            "passport_document": "<base64 PNG/JPG>",  (optionnel)
            "signature": "<data:image/png;base64,...>" (optionnel mais recommandé)
        }

    Réutilise la logique de PublicTravelerRegisterView (ebola). À terme la
    factorisation pourra basculer dans apps/forms/services.py mais pour
    l'instant on délègue à l'endpoint existant via un adapter qui mappe
    answers → dict structuré attendu par PublicTravelerSubmissionSerializer.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_registration"

    # Sections "officielles" reconnues par le pipeline ebola existant.
    # Si le DynamicForm utilise d'autres `section.code`, on tombe en best
    # effort sur le mapping `_INFER_BY_FIELD` ci-dessous.
    _KNOWN_SECTIONS = {
        "voyage", "identite", "historique", "confinement",
        "exposition", "exposure", "symptomes", "symptoms",
        "declaration",
    }

    # Mapping field_code → section officielle (fallback si la section n'est
    # pas explicitement reconnue dans le schema).
    _INFER_BY_FIELD = {
        # voyage
        "arrival_date": "voyage", "arrival_time": "voyage",
        "transport_mode": "voyage", "flight_or_voyage_number": "voyage",
        "seat_number": "voyage", "entry_point_code": "voyage",
        "entry_point_id": "voyage", "entry_point": "voyage",
        # identite
        "last_name": "identite", "first_name": "identite", "middle_name": "identite",
        "age": "identite", "age_unit": "identite", "date_of_birth": "identite",
        "gender": "identite", "profession": "identite",
        "id_document_type": "identite", "id_document_number": "identite",
        "id_document_country_code": "identite", "nationality_code": "identite",
        "phone_mobile": "identite", "email": "identite", "postal_address": "identite",
        # confinement
        "city": "confinement", "commune": "confinement", "neighborhood": "confinement",
        "street_number": "confinement", "lot": "confinement", "hotel": "confinement",
        "room_number": "confinement", "emergency_phone_ci": "confinement",
        "whatsapp_phone": "confinement", "latitude": "confinement",
        "longitude": "confinement", "geoloc": "confinement",
        # exposition
        "visited_ebola_zone": "exposure",
        "visited_ebola_zone_details": "exposure",
        "contact_with_case": "exposure",
        "attended_funeral_or_touched_corpse": "exposure",
        "visited_ebola_healthcare_facility": "exposure",
        # symptômes
        "fever": "symptoms", "intense_fatigue": "symptoms",
        "muscle_joint_pain": "symptoms", "severe_headache": "symptoms",
        "sore_throat_or_abdominal": "symptoms",
        "diarrhea_nausea_vomiting": "symptoms",
        "unexplained_bleeding": "symptoms",
        "temperature": "symptoms", "temperature_celsius": "symptoms",
        "other_symptoms": "symptoms",
        # déclaration
        "signed_place": "declaration", "signed_at": "declaration",
        "declared_at": "declaration", "truthful": "declaration",
        "truthful_declaration": "declaration", "signature": "declaration",
        "signature_data_url": "declaration", "declarant_full_name": "declaration",
    }

    def _build_legacy_payload(self, answers: dict, signature_data_url: str) -> dict:
        """Convertit answers={code: value} → structure attendue par
        PublicTravelerSubmissionSerializer.

        On regroupe par section déduite, on normalise les bools, et on
        synthétise les blocs obligatoires (voyage, identite, etc.).
        """
        payload: dict = {
            "voyage": {}, "identite": {}, "historique": [],
            "confinement": {}, "exposure": {}, "symptoms": {},
            "declaration": {},
        }
        for code, value in (answers or {}).items():
            section = self._INFER_BY_FIELD.get(code)
            if section is None:
                # Pas mappé → on l'ignore plutôt que de planter. Trace pour
                # le QA mais aucun PII en clair (juste le code du champ).
                logger.debug("mobile.submission unknown field code=%s", code)
                continue
            target = payload[section]
            if section == "confinement" and code == "geoloc":
                # Géoloc envoyée sous forme "lat,lng" ou {"lat":..,"lng":..}
                lat, lng = None, None
                if isinstance(value, dict):
                    lat = value.get("lat") or value.get("latitude")
                    lng = value.get("lng") or value.get("longitude")
                elif isinstance(value, str) and "," in value:
                    parts = value.split(",", 1)
                    try:
                        lat = float(parts[0].strip())
                        lng = float(parts[1].strip())
                    except ValueError:
                        lat = lng = None
                if lat is not None and lng is not None:
                    target["latitude"] = lat
                    target["longitude"] = lng
                continue
            target[code] = value

        # Signature manuscrite : on la pousse explicitement dans declaration
        if signature_data_url:
            payload["declaration"]["signature_data_url"] = signature_data_url
        # Alias truthful → truthful_declaration (clé serializer attendue)
        decl = payload["declaration"]
        if "truthful" in decl and "truthful_declaration" not in decl:
            decl["truthful_declaration"] = bool(decl.pop("truthful"))
        if "signed_at" in decl and "declared_at" not in decl:
            decl["declared_at"] = decl["signed_at"]
        return payload

    def post(self, request, code: str):
        from apps.ebola.public_views import PublicTravelerRegisterView

        # Charge utile cliente (JSON pur — pas multipart, on ne supporte pas
        # encore l'upload binaire dans cet endpoint mobile ; le passeport
        # pourra être uploadé séparément via /upload-passport/ après pass).
        answers = request.data.get("answers") or {}
        if not isinstance(answers, dict):
            return Response(
                {"detail": "Le champ 'answers' doit être un objet { code: valeur }."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        signature = request.data.get("signature") or ""

        legacy_payload = self._build_legacy_payload(answers, signature)

        # On délègue à PublicTravelerRegisterView.post() en lui passant la
        # même request DRF mais avec un `_full_data` remplacé. C'est la
        # forme la moins fragile pour réutiliser la logique transactionnelle
        # existante (création Traveler + EbolaInvestigation + HealthPass +
        # scoring + audit) sans dupliquer ~200 lignes.
        original_full = getattr(request, "_full_data", None)
        original_data_cached = request.__dict__.get("_data", None)
        try:
            request._full_data = legacy_payload  # noqa: SLF001
            # Invalide le cache lazy de DRF (request.data lit _full_data au
            # premier accès puis cache dans _data).
            request.__dict__.pop("_data", None)
            handler = PublicTravelerRegisterView()
            handler.setup(request._request)  # noqa: SLF001
            response = handler.post(request)
        finally:
            # Hygiène : restaure le payload original sur la requête.
            if original_full is not None:
                request._full_data = original_full  # noqa: SLF001
            if original_data_cached is not None:
                request.__dict__["_data"] = original_data_cached
        return response
