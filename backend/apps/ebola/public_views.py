"""Endpoints PUBLICS pour le portail voyageurs (sans authentification).

- POST /api/v1/ebola/public/register/
    Enregistre une fiche passager INHP complète et délivre immédiatement :
      - un voyageur (Traveler)
      - une enquête Ebola scorée
      - un Health Pass QR + PDF (lien public temporaire)

- GET /api/v1/ebola/public/pass/<public_id>/
    Consultation publique du statut du voyageur + lien PDF + QR token.
"""
from __future__ import annotations

from datetime import datetime

from django.contrib.gis.geos import Point
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.audit.services import audit
from apps.diseases.models import Disease
from apps.geo.models import Country, EntryPoint
from apps.health_pass.models import HealthPass
from apps.health_pass.services import issue_pass_for_ebola_investigation
from apps.travelers.models import Traveler, TravelHistoryEntry

from .models import EbolaDeclaration, EbolaExposureAssessment, EbolaInvestigation, EbolaSymptomReport
from .serializers import (
    EbolaInvestigationSerializer,
    PublicTravelerSubmissionSerializer,
)
from .services import apply_risk_outcome


def _parse_decimal(v):
    try:
        return float(v) if v not in (None, "", "null") else None
    except (TypeError, ValueError):
        return None


def _parse_date(v):
    if not v:
        return None
    if isinstance(v, datetime):
        return v.date()
    try:
        return datetime.fromisoformat(str(v)).date()
    except ValueError:
        return None


def _parse_datetime(v):
    if not v:
        return None
    try:
        s = str(v)
        if s.endswith("Z"):
            s = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except ValueError:
        return None


class PublicTravelerRegisterView(APIView):
    """Enregistrement public d'une fiche passager Ebola."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "anon"

    @extend_schema(
        request=PublicTravelerSubmissionSerializer,
        responses={201: OpenApiResponse(description="Voyageur enregistré, pass délivré.")},
        summary="Enregistrement public voyageur (fiche INHP Ebola)",
        description="Soumission publique stricte conforme à la fiche officielle INHP. "
                    "Crée le voyageur, ouvre une enquête Ebola, calcule le score, génère le pass.",
    )
    def post(self, request):
        ser = PublicTravelerSubmissionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        voyage = data.get("voyage", {})
        identite = data.get("identite", {})
        confinement = data.get("confinement", {})
        exposure = data.get("exposure", {})
        symptoms = data.get("symptoms", {})
        declaration = data.get("declaration", {})

        with transaction.atomic():
            # --- Section 1 : voyage ---
            entry_point = None
            if voyage.get("entry_point_code"):
                entry_point = EntryPoint.objects.filter(code=voyage["entry_point_code"]).first()
            elif voyage.get("entry_point_id"):
                entry_point = EntryPoint.objects.filter(pk=voyage["entry_point_id"]).first()

            # --- Section 2 : identité ---
            nationality = None
            if identite.get("nationality_code"):
                nationality = Country.objects.filter(code=identite["nationality_code"]).first()
            id_country = None
            if identite.get("id_document_country_code"):
                id_country = Country.objects.filter(code=identite["id_document_country_code"]).first()

            # --- Section 4 : confinement (avec géolocalisation optionnelle) ---
            location = None
            if confinement.get("latitude") and confinement.get("longitude"):
                try:
                    location = Point(
                        float(confinement["longitude"]),
                        float(confinement["latitude"]),
                        srid=4326,
                    )
                except (TypeError, ValueError):
                    location = None

            traveler = Traveler.objects.create(
                # Section 1
                arrival_date=_parse_date(voyage.get("arrival_date")),
                arrival_time=voyage.get("arrival_time") or None,
                transport_mode=voyage.get("transport_mode", "") or "",
                flight_or_voyage_number=voyage.get("flight_or_voyage_number", "") or "",
                seat_number=voyage.get("seat_number", "") or "",
                entry_point=entry_point,
                # Section 2
                last_name=(identite.get("last_name") or "").strip(),
                first_name=(identite.get("first_name") or "").strip(),
                middle_name=(identite.get("middle_name") or "").strip(),
                age=identite.get("age") or None,
                age_unit=identite.get("age_unit") or "years",
                date_of_birth=_parse_date(identite.get("date_of_birth")),
                gender=identite.get("gender", "") or "",
                profession=identite.get("profession", "") or "",
                id_document_type=identite.get("id_document_type", "passport") or "passport",
                id_document_number=(identite.get("id_document_number") or "").strip(),
                id_document_country=id_country,
                nationality=nationality,
                phone_mobile=(identite.get("phone_mobile") or "").strip(),
                email=(identite.get("email") or "").strip(),
                postal_address=(identite.get("postal_address") or "").strip(),
                # Section 4
                confinement_city=(confinement.get("city") or "").strip(),
                confinement_commune=(confinement.get("commune") or "").strip(),
                confinement_neighborhood=(confinement.get("neighborhood") or "").strip(),
                confinement_street_number=(confinement.get("street_number") or "").strip(),
                confinement_lot=(confinement.get("lot") or "").strip(),
                confinement_hotel=(confinement.get("hotel") or "").strip(),
                confinement_room_number=(confinement.get("room_number") or "").strip(),
                emergency_phone_ci=(confinement.get("emergency_phone_ci") or "").strip(),
                confinement_location=location,
                # Déclaration de la section 7
                consented_data_processing=bool(declaration.get("truthful_declaration")),
                signed_at=_parse_datetime(declaration.get("declared_at")) or timezone.now(),
                signed_place=(declaration.get("signed_place") or "").strip(),
            )

            # --- Section 3 : historique des déplacements ---
            for item in data.get("historique", []) or []:
                country = Country.objects.filter(code=item.get("country_code")).first()
                if country is None:
                    continue
                TravelHistoryEntry.objects.create(
                    traveler=traveler,
                    role=item.get("role", "visited"),
                    country=country,
                    city=item.get("city", "") or "",
                    residence_address=item.get("residence_address", "") or "",
                    hotel=item.get("hotel", "") or "",
                    room_number=item.get("room_number", "") or "",
                    arrival_date=item.get("arrival_date"),
                    departure_date=item.get("departure_date"),
                    duration_text=item.get("duration_text", "") or "",
                )

            # --- Enquête Ebola ---
            investigation = EbolaInvestigation.objects.create(
                traveler=traveler,
                entry_point=entry_point,
                status="new",
                notes="Soumis depuis le portail voyageurs public.",
            )

            # --- Section 5 : exposition ---
            EbolaExposureAssessment.objects.create(
                investigation=investigation,
                visited_ebola_zone=bool(exposure.get("visited_ebola_zone")),
                visited_ebola_zone_details=(exposure.get("visited_ebola_zone_details") or "").strip(),
                contact_with_case=bool(exposure.get("contact_with_case")),
                attended_funeral_or_touched_corpse=bool(
                    exposure.get("attended_funeral_or_touched_corpse")
                ),
                visited_ebola_healthcare_facility=bool(
                    exposure.get("visited_ebola_healthcare_facility")
                ),
            )

            # --- Section 6 : symptômes ---
            EbolaSymptomReport.objects.create(
                investigation=investigation,
                reported_at=timezone.now(),
                temperature_celsius=_parse_decimal(symptoms.get("temperature_celsius")),
                fever=bool(symptoms.get("fever")),
                intense_fatigue=bool(symptoms.get("intense_fatigue")),
                muscle_joint_pain=bool(symptoms.get("muscle_joint_pain")),
                severe_headache=bool(symptoms.get("severe_headache")),
                sore_throat_or_abdominal=bool(symptoms.get("sore_throat_or_abdominal")),
                diarrhea_nausea_vomiting=bool(symptoms.get("diarrhea_nausea_vomiting")),
                unexplained_bleeding=bool(symptoms.get("unexplained_bleeding")),
                other_symptoms=(symptoms.get("other_symptoms") or "").strip(),
            )

            # --- Section 7 : déclaration ---
            EbolaDeclaration.objects.create(
                investigation=investigation,
                declared_at=_parse_datetime(declaration.get("declared_at")) or timezone.now(),
                declarant_full_name=(declaration.get("declarant_full_name") or traveler.full_name).strip(),
                signed_place=(declaration.get("signed_place") or "").strip(),
                truthful_declaration=bool(declaration.get("truthful_declaration")),
                consent_data_processing=True,
                consent_health_followup=True,
                consent_quarantine_if_needed=True,
            )

            # --- Scoring + workflow ---
            apply_risk_outcome(investigation)

            # --- Health Pass délivré immédiatement ---
            hp = issue_pass_for_ebola_investigation(investigation)

            audit(
                request, action="create",
                summary=f"Auto-enregistrement portail public — {traveler.public_id} → {investigation.case_number}",
                target=investigation,
                payload={"score": investigation.risk_score, "level": investigation.risk_level},
            )

        return Response({
            "traveler": {
                "public_id": traveler.public_id,
                "uuid": str(traveler.uuid),
                "full_name": traveler.full_name,
                "current_health_status": traveler.current_health_status,
            },
            "investigation": EbolaInvestigationSerializer(investigation).data,
            "pass": {
                "pass_number": hp.pass_number,
                "uuid": str(hp.uuid),
                "status": hp.status,
                "expires_at": hp.expires_at,
                "qr_url": hp.qr_image.url if hp.qr_image else None,
                "pdf_url": hp.pdf_file.url if hp.pdf_file else None,
                "qr_token": _safe_qr_token(hp),
            },
            "instructions": _public_instructions(investigation),
        }, status=status.HTTP_201_CREATED)


def _safe_qr_token(hp: HealthPass) -> str:
    """Reconstruit le token QR à partir des données stockées."""
    # On régénère le token signé à la volée pour l'afficher côté front.
    from apps.health_pass.crypto import PREFIX, _b64u_encode, sign_payload
    if hp.payload and hp.signature_b64:
        import json
        payload_json = json.dumps(hp.payload, separators=(",", ":"), sort_keys=True).encode()
        return f"{PREFIX}.{_b64u_encode(payload_json)}.{hp.signature_b64}"
    token, _ = sign_payload(hp.payload or {})
    return token


def _public_instructions(investigation: EbolaInvestigation) -> dict:
    """Texte d'instruction adapté au niveau de risque."""
    level = investigation.risk_level
    base = {
        "surveillance_days": 21,
        "phones": {
            "samu": "185",
            "allo_sante": "143",
            "secours": "101",
            "inhp_lines": ["27 21 25 35 10", "27 21 25 97 46"],
        },
        "presented_pass": True,
    }
    if level == "critical":
        base["message"] = (
            "Vos réponses présentent des signes potentiellement compatibles avec une infection. "
            "Restez sur place, ne quittez pas la zone et appelez immédiatement le SAMU (185)."
        )
    elif level == "high":
        base["message"] = (
            "Votre situation nécessite une mise en quarantaine de 21 jours et un suivi médical strict. "
            "Un agent vous contactera. Restez à l'adresse de confinement indiquée."
        )
    elif level == "moderate":
        base["message"] = (
            "Vous êtes placé sous surveillance sanitaire (21 jours). Mesurez votre température chaque jour "
            "et signalez tout symptôme via les numéros d'urgence."
        )
    else:
        base["message"] = (
            "Aucun risque significatif détecté. Surveillance simple de 21 jours. "
            "Contactez les services de santé en cas d'apparition de symptômes."
        )
    return base


class PublicPassConsultView(APIView):
    """Consultation publique du statut + pass d'un voyageur par son public_id."""

    permission_classes = [AllowAny]

    def get(self, request, public_id: str):
        traveler = get_object_or_404(Traveler, public_id=public_id)
        hp = HealthPass.objects.filter(traveler=traveler).order_by("-created_at").first()
        last_inv = EbolaInvestigation.objects.filter(traveler=traveler).order_by("-created_at").first()
        data = {
            "traveler": {
                "public_id": traveler.public_id,
                "full_name": traveler.full_name,
                "current_health_status": traveler.current_health_status,
                "arrival_date": traveler.arrival_date,
                "entry_point": traveler.entry_point.name if traveler.entry_point_id else None,
            },
            "investigation": EbolaInvestigationSerializer(last_inv).data if last_inv else None,
            "pass": None,
        }
        if hp:
            data["pass"] = {
                "pass_number": hp.pass_number,
                "uuid": str(hp.uuid),
                "status": hp.status,
                "risk_level": hp.risk_level,
                "risk_score": hp.risk_score,
                "issued_at": hp.issued_at,
                "expires_at": hp.expires_at,
                "qr_url": hp.qr_image.url if hp.qr_image else None,
                "pdf_url": hp.pdf_file.url if hp.pdf_file else None,
                "qr_token": _safe_qr_token(hp),
            }
        return Response(data)
