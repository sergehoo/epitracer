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

import base64
import hashlib
import re
from datetime import datetime

from django.contrib.gis.geos import Point
from django.core.files.base import ContentFile
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


_DATA_URL_RE = re.compile(r"^data:image/(?P<ext>png|jpeg|jpg|webp);base64,(?P<b64>.+)$", re.S)


def _trim(value, max_len: int) -> str:
    """Strip + tronque à la longueur max du champ DB.

    Protège l'INSERT contre `StringDataRightTruncation` quand un voyageur
    tape un texte plus long que la colonne CharField correspondante.
    """
    if value is None:
        return ""
    return str(value).strip()[:max_len]


def _decode_signature(data_url: str, public_id: str) -> tuple[ContentFile | None, str]:
    """Décode une signature data:URL (PNG/JPEG base64) en ContentFile + hash sha256.

    Retourne (file, hash_hex). Si data_url est invalide, (None, '').
    Limite la taille à 2 Mo (assez large pour une signature).
    """
    if not data_url:
        return None, ""
    m = _DATA_URL_RE.match(data_url.strip())
    if not m:
        return None, ""
    try:
        raw = base64.b64decode(m.group("b64"), validate=True)
    except Exception:
        return None, ""
    if len(raw) > 2 * 1024 * 1024:
        return None, ""
    ext = m.group("ext").replace("jpeg", "jpg")
    digest = hashlib.sha256(raw).hexdigest()
    return ContentFile(raw, name=f"signature_{public_id}.{ext}"), digest


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

            # Truncation défensive alignée sur les max_length du modèle Traveler,
            # pour ne plus jamais lever StringDataRightTruncation côté DB.
            traveler = Traveler.objects.create(
                # Section 1
                arrival_date=_parse_date(voyage.get("arrival_date")),
                arrival_time=voyage.get("arrival_time") or None,
                transport_mode=_trim(voyage.get("transport_mode"), 20),
                flight_or_voyage_number=_trim(voyage.get("flight_or_voyage_number"), 60),
                seat_number=_trim(voyage.get("seat_number"), 20),
                entry_point=entry_point,
                # Section 2
                last_name=_trim(identite.get("last_name"), 120),
                first_name=_trim(identite.get("first_name"), 120),
                middle_name=_trim(identite.get("middle_name"), 120),
                age=identite.get("age") or None,
                age_unit=_trim(identite.get("age_unit"), 10) or "years",
                date_of_birth=_parse_date(identite.get("date_of_birth")),
                gender=_trim(identite.get("gender"), 2),
                profession=_trim(identite.get("profession"), 160),
                id_document_type=_trim(identite.get("id_document_type"), 20) or "passport",
                id_document_number=_trim(identite.get("id_document_number"), 60),
                id_document_country=id_country,
                nationality=nationality,
                phone_mobile=_trim(identite.get("phone_mobile"), 32),
                email=_trim(identite.get("email"), 254),
                postal_address=_trim(identite.get("postal_address"), 300),
                # Section 4
                confinement_city=_trim(confinement.get("city"), 120),
                confinement_commune=_trim(confinement.get("commune"), 120),
                confinement_neighborhood=_trim(confinement.get("neighborhood"), 160),
                confinement_street_number=_trim(confinement.get("street_number"), 120),
                confinement_lot=_trim(confinement.get("lot"), 120),
                confinement_hotel=_trim(confinement.get("hotel"), 200),
                confinement_room_number=_trim(confinement.get("room_number"), 120),
                emergency_phone_ci=_trim(confinement.get("emergency_phone_ci"), 32),
                whatsapp_phone=_trim(confinement.get("whatsapp_phone"), 32),
                confinement_location=location,
                # Déclaration de la section 7
                consented_data_processing=bool(declaration.get("truthful_declaration")),
                signed_at=_parse_datetime(declaration.get("declared_at")) or timezone.now(),
                signed_place=_trim(declaration.get("signed_place"), 120),
            )

            # --- Section 3 : historique des déplacements ---
            for item in data.get("historique", []) or []:
                country = Country.objects.filter(code=item.get("country_code")).first()
                if country is None:
                    continue
                TravelHistoryEntry.objects.create(
                    traveler=traveler,
                    role=_trim(item.get("role"), 10) or "visited",
                    country=country,
                    province=_trim(item.get("province"), 160),
                    city=_trim(item.get("city"), 120),
                    residence_address=_trim(item.get("residence_address"), 300),
                    hotel=_trim(item.get("hotel"), 200),
                    room_number=_trim(item.get("room_number"), 120),
                    arrival_date=item.get("arrival_date"),
                    departure_date=item.get("departure_date"),
                    duration_text=_trim(item.get("duration_text"), 120),
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

            # --- Section 7 : déclaration (avec signature manuscrite scannée) ---
            sig_file, sig_hash = _decode_signature(
                declaration.get("signature_data_url", ""), traveler.public_id,
            )
            decl_obj = EbolaDeclaration.objects.create(
                investigation=investigation,
                declared_at=_parse_datetime(declaration.get("declared_at")) or timezone.now(),
                declarant_full_name=(declaration.get("declarant_full_name") or traveler.full_name).strip(),
                signed_place=(declaration.get("signed_place") or "").strip(),
                truthful_declaration=bool(declaration.get("truthful_declaration")),
                consent_data_processing=True,
                consent_health_followup=True,
                consent_quarantine_if_needed=True,
                signature_hash=sig_hash,
            )
            if sig_file is not None:
                decl_obj.signature.save(sig_file.name, sig_file, save=True)
                # On répercute aussi côté Traveler pour exports rapides
                traveler.consent_signature.save(sig_file.name, sig_file, save=False)
                traveler.save(update_fields=["consent_signature"])

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
            "inhp_lines": ["143"],
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
                "has_passport": bool(traveler.passport_document),
            },
            "investigation": EbolaInvestigationSerializer(last_inv).data if last_inv else None,
            "pass": None,
            "downloads": {
                "pass_pdf": f"/api/v1/ebola/public/pass/{public_id}/pdf/",
                "official_form_pdf": f"/api/v1/ebola/public/pass/{public_id}/official-form.pdf",
            },
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


# ============================================================================
#                   Téléchargement public — pass + fiche officielle
# ============================================================================
from django.http import FileResponse, HttpResponse  # noqa: E402

from apps.health_pass.services import render_official_form_pdf  # noqa: E402


class PublicPassPdfView(APIView):
    """Télécharge le PDF du pass sanitaire (sans auth, lié au public_id)."""

    permission_classes = [AllowAny]

    def get(self, request, public_id: str):
        traveler = get_object_or_404(Traveler, public_id=public_id)
        hp = HealthPass.objects.filter(traveler=traveler).order_by("-created_at").first()
        if not hp or not hp.pdf_file:
            return Response({"detail": "Pass PDF indisponible."}, status=404)
        audit(request, action="export",
              summary=f"Téléchargement public pass {hp.pass_number}", target=hp)
        return FileResponse(
            open(hp.pdf_file.path, "rb"),
            as_attachment=True,
            filename=f"PassSanitaire_{traveler.public_id}.pdf",
            content_type="application/pdf",
        )


class PublicOfficialFormPdfView(APIView):
    """Génère et télécharge la FICHE OFFICIELLE INHP pré-remplie en PDF."""

    permission_classes = [AllowAny]

    def get(self, request, public_id: str):
        traveler = get_object_or_404(Traveler, public_id=public_id)
        pdf_bytes = render_official_form_pdf(traveler)
        audit(request, action="export",
              summary=f"Téléchargement fiche officielle INHP {traveler.public_id}",
              target=traveler)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="FicheINHP_{traveler.public_id}.pdf"'
        )
        return response


# ============================================================================
#               Upload public du passeport / document de voyage
# ============================================================================
class PublicPassportUploadView(APIView):
    """Permet à un voyageur de joindre/remplacer sa copie de document de voyage.

    POST /api/v1/ebola/public/upload-passport/<public_id>/
        multipart/form-data : passport_document=<fichier>

    Accepte PDF / JPG / PNG, taille max 8 Mo.
    """

    permission_classes = [AllowAny]
    parser_classes = []  # injectés explicitement ci-dessous

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from rest_framework.parsers import FormParser, MultiPartParser
        self.parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Joindre une copie du passeport / document de voyage",
        description="Champ : `passport_document` (PDF/JPG/PNG, 8 Mo max).",
        responses={200: OpenApiResponse(description="Document enregistré.")},
    )
    def post(self, request, public_id: str):
        traveler = get_object_or_404(Traveler, public_id=public_id)
        file = request.FILES.get("passport_document")
        if file is None:
            return Response({"detail": "Aucun fichier transmis (champ 'passport_document')."}, status=400)
        # Validation basique
        max_bytes = 8 * 1024 * 1024
        if file.size > max_bytes:
            return Response({"detail": "Fichier trop volumineux (max 8 Mo)."}, status=413)
        allowed_ct = ("application/pdf", "image/jpeg", "image/png")
        if file.content_type not in allowed_ct:
            return Response(
                {"detail": "Format invalide. Acceptés : PDF, JPG, PNG."},
                status=415,
            )
        traveler.passport_document = file
        traveler.passport_uploaded_at = timezone.now()
        traveler.save(update_fields=["passport_document", "passport_uploaded_at"])
        audit(request, action="update",
              summary=f"Upload passeport public {traveler.public_id}",
              target=traveler, payload={"size": file.size, "ct": file.content_type})
        return Response({
            "detail": "Document de voyage enregistré.",
            "public_id": traveler.public_id,
            "url": traveler.passport_document.url,
            "uploaded_at": traveler.passport_uploaded_at,
        })
