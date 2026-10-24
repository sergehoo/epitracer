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
from apps.core.validators import validate_uploaded_file
from apps.diseases.models import Disease
from apps.geo.models import EntryPoint
from apps.geo.services import alert_on_arrival_from_risk_country, resolve_country
from apps.health_pass.models import HealthPass
from apps.health_pass.services import issue_pass_for_registration
from apps.medical.models import ScreeningDecision, ScreeningReviewStatus
from apps.medical.screening import apply_screenings
from apps.travelers.models import Traveler, TravelHistoryEntry

from . import registration_dedup as dedup
from .models import (
    EbolaDeclaration,
    EbolaExposureAssessment,
    EbolaInvestigation,
    EbolaSymptomReport,
)
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


def _rate_limited(request, rule: str, identity: str, *, phone: str = "") -> Response | None:
    from apps.core import ratelimit
    from apps.notifications.services.security import SecurityEventKind, log_security_event

    result = ratelimit.hit(rule, identity)
    if result.allowed:
        return None
    ip = ratelimit.client_ip(request)
    log_security_event(
        SecurityEventKind.RATE_LIMITED,
        source="public_registration",
        ip=ip,
        phone=phone,
        details={"rule": rule, "count": result.count, "limit": result.limit},
        dedupe=f"registration:{rule}:{identity}",
    )
    resp = Response(
        {
            "detail": (
                "Trop d'inscriptions depuis cette connexion ou pour ce numéro. Réessayez plus tard."
            )
        },
        status=status.HTTP_429_TOO_MANY_REQUESTS,
    )
    resp["Retry-After"] = str(result.retry_after)
    return resp


def _registration_guard(request) -> Response | None:
    """Anti inscriptions massives (vecteur de SMS pumping : chaque fiche suivie
    reçoit des rappels SMS) : Turnstile, puis limites par IP, globale et par
    numéro de téléphone déclaré."""
    from apps.core import ratelimit, turnstile

    captcha = turnstile.check_request(request, "public_registration")
    if not captcha.ok:
        return Response(
            {"detail": turnstile.failure_message(captcha)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return (
        _rate_limited(request, "registration_ip", ratelimit.client_ip(request))
        or _rate_limited(request, "registration_endpoint", "all")
        or _registration_phone_limit(request)
    )


def _registration_phone_limit(request) -> Response | None:
    """Limite le nombre de fiches par numéro de téléphone et par jour."""
    from apps.notifications.services.router import PhoneValidationError, normalize_phone_number

    identite = request.data.get("identite") if hasattr(request.data, "get") else None
    raw = (identite or {}).get("phone_mobile") if isinstance(identite, dict) else ""
    if not raw:
        return None
    try:
        phone = normalize_phone_number(str(raw))
    except PhoneValidationError:
        return None
    return _rate_limited(request, "registration_phone", phone, phone=phone)


class PublicTravelerRegisterView(APIView):
    """Enregistrement public d'une fiche passager Ebola."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    # task #213 — scope dédié 5/min/IP (cf. settings DEFAULT_THROTTLE_RATES).
    # On bascule de "anon" (60/min) vers "public_registration" pour resserrer
    # l'angle d'attaque sur cet endpoint très exposé (formulaire grand public).
    throttle_scope = "public_registration"

    @extend_schema(
        request=PublicTravelerSubmissionSerializer,
        responses={201: OpenApiResponse(description="Voyageur enregistré, pass délivré.")},
        summary="Enregistrement public voyageur (fiche INHP Ebola)",
        description="Soumission publique stricte conforme à la fiche officielle INHP. "
        "Crée le voyageur, ouvre une enquête Ebola, calcule le score, génère le pass.",
    )
    def post(self, request):
        key = dedup.idempotency_key(request)  # 400 si l'en-tête est malformé
        # Retry après timeout ou coupure réseau : la fiche existe déjà. Ni garde
        # anti-robot ni quota : rien n'est créé, aucun SMS supplémentaire.
        known = dedup.traveler_for_key(key)
        if known is not None:
            return _already_registered(request, known)

        blocked = _registration_guard(request)
        if blocked is not None:
            return blocked
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
            claim, duplicate = _claim_registration(request, key, identite, voyage)
            if duplicate is not None:
                return duplicate

            # --- Section 1 : voyage ---
            entry_point = None
            if voyage.get("entry_point_code"):
                entry_point = EntryPoint.objects.filter(code=voyage["entry_point_code"]).first()
            elif voyage.get("entry_point_id"):
                entry_point = EntryPoint.objects.filter(pk=voyage["entry_point_id"]).first()

            # --- Section 2 : identité ---
            nationality = resolve_country(identite.get("nationality_code"))
            id_country = resolve_country(identite.get("id_document_country_code"))

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
                planned_departure_date=_parse_date(voyage.get("planned_departure_date")),
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
            dedup.bind_key(claim, traveler)

            # --- Section 3 : historique des déplacements ---
            for item in data.get("historique", []) or []:
                country = resolve_country(item.get("country_code"))
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

            # --- Section 7 : signature, conservée sur le voyageur quelle que soit la maladie ---
            sig_file, sig_hash = _decode_signature(
                declaration.get("signature_data_url", ""),
                traveler.public_id,
            )
            if sig_file is not None:
                traveler.consent_signature.save(sig_file.name, sig_file, save=False)
                traveler.save(update_fields=["consent_signature"])

            # --- Fiche INHP Ebola (sections 5 et 6) : seulement si Ebola est sous surveillance ---
            investigation = None
            if Disease.objects.filter(code="EBOLA", is_active=True).exists():
                investigation = _create_ebola_investigation(
                    traveler,
                    entry_point,
                    exposure,
                    symptoms,
                    declaration,
                    sig_file,
                    sig_hash,
                )

            # --- Autres maladies : qualification par règles, un suivi par maladie ---
            qualification = apply_screenings(
                traveler,
                data.get("screenings") or [],
                symptom_codes=data.get("symptom_codes") or [],
                common_symptoms=symptoms,
            )
            followups = [q for q in qualification if q["decision"] == ScreeningDecision.FOLLOWUP]
            _update_health_status(traveler, investigation, followups)

            # --- Pass : dépend de l'enregistrement, jamais d'une maladie ---
            level, score = _registration_risk(investigation, qualification)
            hp = issue_pass_for_registration(
                traveler,
                risk_level=level,
                risk_score=score,
                reference=investigation.case_number if investigation else traveler.public_id,
            )

            audit(
                request,
                action="create",
                summary=f"Auto-enregistrement portail public — {traveler.public_id} → {hp.pass_number}",
                target=investigation or traveler,
                payload={
                    "level": level,
                    "score": score,
                    "followups": [f["disease_code"] for f in followups],
                },
            )

        # Règle de surveillance : pays de provenance/transit à risque élevé ou critique.
        alert_on_arrival_from_risk_country(traveler)

        return Response(
            _registration_payload(
                traveler,
                investigation,
                hp,
                level,
                followups,
                review_pending=any(q["review_pending"] for q in qualification),
            ),
            status=status.HTTP_201_CREATED,
        )


def _claim_registration(request, key: str, identite: dict, voyage: dict):
    """Anti-doublon, dans la transaction d'inscription.

    Réserve la clé d'idempotence, puis cherche une fiche déjà délivrée : même
    clé validée entre-temps (retry concurrent), ou même pièce + même arrivée +
    même contact. Retourne (réservation, réponse) ; une réponse non nulle
    renvoie la fiche existante.
    """
    claim = dedup.claim_key(key) if key else None
    if key and claim is None:
        return None, _already_registered(request, dedup.traveler_for_key(key))
    arrival = _parse_date(voyage.get("arrival_date"))
    dedup.lock_identity(identite, arrival)
    existing = dedup.existing_registration(identite, arrival)
    if existing is not None:
        dedup.bind_key(claim, existing)
        return claim, _already_registered(request, existing)
    return claim, None


def _registration_payload(
    traveler,
    investigation,
    hp,
    level,
    followups,
    *,
    review_pending,
) -> dict:
    return {
        "traveler": {
            "public_id": traveler.public_id,
            "uuid": str(traveler.uuid),
            "full_name": traveler.full_name,
            "current_health_status": traveler.current_health_status,
        },
        "investigation": (
            EbolaInvestigationSerializer(investigation).data if investigation else None
        ),
        "pass": (
            {
                "pass_number": hp.pass_number,
                "uuid": str(hp.uuid),
                "status": hp.status,
                "expires_at": hp.expires_at,
                "qr_url": hp.qr_image.url if hp.qr_image else None,
                "pdf_url": hp.pdf_file.url if hp.pdf_file else None,
                "qr_token": _safe_qr_token(hp),
            }
            if hp
            else None
        ),
        "instructions": _public_instructions(level, followups),
        "followups": followups,
        # Un agent vérifiera certaines réponses : le voyageur est simplement prévenu.
        "review_pending": review_pending,
    }


def _already_registered(request, traveler) -> Response:
    """Soumission déjà traitée (retry réseau, double envoi, brouillon resoumis) :
    la fiche existante est renvoyée telle quelle ; rien n'est créé ni modifié."""
    from apps.quarantine.services import followup_duration_days

    if traveler is None:
        return Response(
            {"detail": "Cette fiche a déjà été soumise. Consultez votre pass ou appelez le 143."},
            status=status.HTTP_409_CONFLICT,
        )
    hp = traveler.health_passes.order_by("-created_at").first()
    investigation = traveler.ebola_investigations.order_by("-created_at").first()
    screenings = list(traveler.health_screenings.select_related("disease").order_by("created_at"))
    followups = [
        {
            "disease_code": s.disease.code,
            "disease_name": s.disease.name,
            "decision": s.decision,
            "review_pending": s.review_status == ScreeningReviewStatus.PENDING,
            "duration_days": followup_duration_days(s.disease),
            "reasons": s.reasons,
        }
        for s in screenings
        if s.decision == ScreeningDecision.FOLLOWUP
    ]
    audit(
        request,
        action="read",
        summary=f"Soumission en double — fiche existante renvoyée {traveler.public_id}",
        target=traveler,
    )
    data = _registration_payload(
        traveler,
        investigation,
        hp,
        hp.risk_level if hp else "low",
        followups,
        review_pending=any(s.review_status == ScreeningReviewStatus.PENDING for s in screenings),
    )
    data["already_registered"] = True
    return Response(data, status=status.HTTP_200_OK)


def _create_ebola_investigation(
    traveler, entry_point, exposure, symptoms, declaration, sig_file, sig_hash
):
    """Fiche passager INHP Ebola : enquête, exposition, symptômes, déclaration, score."""
    investigation = EbolaInvestigation.objects.create(
        traveler=traveler,
        entry_point=entry_point,
        status="new",
        notes="Soumis depuis le portail voyageurs public.",
    )
    EbolaExposureAssessment.objects.create(
        investigation=investigation,
        visited_ebola_zone=bool(exposure.get("visited_ebola_zone")),
        visited_ebola_zone_details=(exposure.get("visited_ebola_zone_details") or "").strip(),
        contact_with_case=bool(exposure.get("contact_with_case")),
        attended_funeral_or_touched_corpse=bool(exposure.get("attended_funeral_or_touched_corpse")),
        visited_ebola_healthcare_facility=bool(exposure.get("visited_ebola_healthcare_facility")),
    )
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
    apply_risk_outcome(investigation)
    return investigation


_RISK_ORDER = ("low", "moderate", "high", "critical")


def _registration_risk(investigation, qualification: list[dict]) -> tuple[str, int]:
    """Niveau affiché sur le pass : score Ebola s'il existe, « modéré » si un suivi est ouvert."""
    level = investigation.risk_level if investigation else "low"
    score = investigation.risk_score if investigation else 0
    if any(q["decision"] == ScreeningDecision.FOLLOWUP for q in qualification):
        if _RISK_ORDER.index(level) < _RISK_ORDER.index("moderate"):
            level = "moderate"
    return level, score


def _update_health_status(traveler, investigation, followups: list[dict]) -> None:
    """Sans fiche Ebola, le statut reflète les suivis ouverts ; on n'abaisse jamais un statut Ebola."""
    if investigation is None:
        traveler.current_health_status = "monitoring" if followups else "cleared"
    elif followups and traveler.current_health_status == "cleared":
        traveler.current_health_status = "monitoring"
    else:
        return
    traveler.save(update_fields=["current_health_status"])


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


def _public_instructions(level: str, followups: list[dict] | None = None) -> dict:
    """Texte d'instruction adapté au niveau de risque et aux suivis ouverts."""
    durations = [f["duration_days"] for f in followups or [] if f.get("duration_days")]
    base = {
        "surveillance_days": max(durations) if durations else 21,
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
        diseases = ", ".join(f["disease_name"] for f in followups or [])
        base["message"] = (
            f"Vous êtes placé sous surveillance sanitaire ({base['surveillance_days']} jours"
            f"{' — ' + diseases if diseases else ''}). Mesurez votre température chaque jour "
            "et signalez tout symptôme via les numéros d'urgence."
        )
    else:
        base["message"] = (
            "Aucun risque significatif détecté. Contactez les services de santé (143) "
            "en cas d'apparition de symptômes."
        )
    return base


class PublicPassConsultView(APIView):
    """Consultation publique du statut + pass d'un voyageur par son public_id.

    SÉCURITÉ : rate-limit `qr_verify_public` (30/min/IP) pour éviter
    l'énumération du public_id. Combiné aux 12+ chars aléatoires du
    public_id (~70 bits entropie), un attaquant ne peut pas brute-forcer
    le namespace en un temps raisonnable.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "qr_verify_public"

    def get(self, request, public_id: str):
        traveler = get_object_or_404(Traveler, public_id=public_id)
        hp = HealthPass.objects.filter(traveler=traveler).order_by("-created_at").first()
        last_inv = (
            EbolaInvestigation.objects.filter(traveler=traveler).order_by("-created_at").first()
        )
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
            # Un dossier de suivi par maladie, pour la même identité de voyageur.
            "followups": [
                {
                    "disease_name": q.disease.name,
                    "disease_slug": q.disease.slug if q.disease.is_published else "",
                    "status": q.status,
                    "started_on": q.started_on,
                    "expected_end_on": q.expected_end_on,
                }
                for q in traveler.quarantines.select_related("disease").order_by("started_on")
            ],
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
        audit(
            request,
            action="export",
            summary=f"Téléchargement public pass {hp.pass_number}",
            target=hp,
        )
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
        audit(
            request,
            action="export",
            summary=f"Téléchargement fiche officielle INHP {traveler.public_id}",
            target=traveler,
        )
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
    # task #213 — endpoint exposé, on cap à 5/min/IP comme le register.
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "public_registration"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from rest_framework.parsers import FormParser, MultiPartParser

        self.parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Joindre une copie du passeport / document de voyage",
        description=(
            "Champ : `passport_document` (PDF/JPG/PNG/WebP). "
            "Taille max : `settings.MAX_UPLOAD_SIZE_MB` (5 Mo par défaut). "
            "Validation par magic bytes — un fichier renommé sera rejeté."
        ),
        responses={
            200: OpenApiResponse(description="Document enregistré."),
            400: OpenApiResponse(description="Fichier absent ou format non supporté."),
        },
    )
    def post(self, request, public_id: str):
        from django.core.exceptions import ValidationError as DjangoValidationError

        traveler = get_object_or_404(Traveler, public_id=public_id)
        file = request.FILES.get("passport_document")
        if file is None:
            return Response(
                {"detail": "Aucun fichier transmis (champ 'passport_document')."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # task #213 — Magic bytes + taille + MIME via validator centralisé.
        # Renvoie un 400 explicite si le fichier est un .exe renommé ou un
        # texte clair, même si le client a fourni un Content-Type valide.
        try:
            detected_mime = validate_uploaded_file(file)
        except DjangoValidationError as exc:
            # Aucun PII dans le message (le validator évite déjà de logger le nom).
            detail = (
                exc.messages[0]
                if getattr(exc, "messages", None)
                else "Format de fichier non supporté."
            )
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)

        traveler.passport_document = file
        traveler.passport_uploaded_at = timezone.now()
        traveler.save(update_fields=["passport_document", "passport_uploaded_at"])
        audit(
            request,
            action="update",
            summary=f"Upload passeport public {traveler.public_id}",
            target=traveler,
            # On audite la taille + le MIME effectivement détecté (PAS le
            # Content-Type déclaré, qui peut être falsifié).
            payload={"size": file.size, "detected_mime": detected_mime},
        )
        return Response(
            {
                "detail": "Document de voyage enregistré.",
                "public_id": traveler.public_id,
                "url": traveler.passport_document.url,
                "uploaded_at": traveler.passport_uploaded_at,
            }
        )
