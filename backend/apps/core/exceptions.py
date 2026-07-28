"""Handler d'exceptions API uniforme.

Format de réponse (toutes les erreurs) :
    {
      "error": {
        "code": "invalid",
        "message": "Adresse email : Saisissez une adresse e-mail valide.",
        "details": {"email": ["Saisissez une adresse e-mail valide."]},
        "request_id": "..."
      }
    }

Le `message` est calculé pour être **actionnable pour l'utilisateur final** :
  - Erreur simple (ex. 403, 404) → texte du detail DRF
  - ValidationError 1 champ → "Nom du champ : message"
  - ValidationError N champs → "3 champs invalides : email, phone_number, ..."
"""
from __future__ import annotations

import logging
import uuid

from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("epidemitracker")


class DomainError(APIException):
    """Base pour les erreurs métier d'EpidemiTracker."""

    status_code = 400
    default_detail = "Erreur métier."
    default_code = "domain_error"


# ---------------------------------------------------------------------------
# Traduction humaine des noms de champs techniques → labels UI
# ---------------------------------------------------------------------------
FIELD_LABELS = {
    "email": "Adresse email",
    "phone_number": "Téléphone",
    "phone_mobile": "Téléphone",
    "whatsapp_phone": "WhatsApp",
    "full_name": "Nom complet",
    "first_name": "Prénom",
    "last_name": "Nom",
    "password": "Mot de passe",
    "recipient": "Destinataire",
    "channel": "Canal",
    "traveler": "Voyageur",
    "consent_date": "Date de consentement",
    "consent_evidence": "Preuve de consentement",
    "preferred_channel": "Canal préféré",
    "district": "District",
    "organization": "Organisation",
    "job_title": "Fonction",
    "birth_date": "Date de naissance",
    "arrival_date": "Date d'arrivée",
    "period_start": "Début de période",
    "period_end": "Fin de période",
    "language": "Langue",
    "body": "Message",
    "subject": "Objet",
    "template_code": "Modèle",
    "csv_file": "Fichier CSV",
    "non_field_errors": "",
    "detail": "",
}


def _humanize_field(key: str) -> str:
    """`email` → 'Adresse email'  ·  `unknown_field` → 'Unknown field'."""
    if key in FIELD_LABELS:
        return FIELD_LABELS[key]
    return key.replace("_", " ").capitalize()


def _extract_first_message(value) -> str:
    """Extrait le 1er message d'erreur d'une valeur DRF (str | list | dict)."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list) and value:
        return _extract_first_message(value[0])
    if isinstance(value, dict) and value:
        # Prend la 1ère erreur imbriquée
        first_key = next(iter(value))
        return _extract_first_message(value[first_key])
    return str(value or "")


def _build_message(detail: dict) -> str:
    """Construit un message actionnable à partir de la structure detail DRF.

    Priorités :
      1. detail est {"detail": "message"} → renvoie 'message'
      2. detail est {"non_field_errors": [...]} → renvoie le 1er message
      3. detail contient 1 seul champ → 'Label : premier message'
      4. detail contient N champs → 'N champs invalides : a, b, c'
    """
    if not isinstance(detail, dict) or not detail:
        return "Erreur de requête."

    # Cas 1 : erreur simple (Http404, PermissionDenied, throttling, etc.)
    if "detail" in detail:
        msg = _extract_first_message(detail["detail"])
        if msg:
            return msg

    # Cas 2 : non_field_errors (validation cross-field)
    if "non_field_errors" in detail:
        msg = _extract_first_message(detail["non_field_errors"])
        if msg:
            return msg

    # Filtre les métadonnées éventuelles (pas des champs à afficher)
    field_errors = {
        k: v for k, v in detail.items()
        if k not in ("detail", "non_field_errors", "code")
    }
    if not field_errors:
        # Fallback si rien d'exploitable
        return "Erreur de requête."

    # Cas 3 : un seul champ
    if len(field_errors) == 1:
        field, value = next(iter(field_errors.items()))
        first = _extract_first_message(value)
        label = _humanize_field(field)
        if label:
            return f"{label} : {first}" if first else f"{label} invalide."
        return first or "Erreur de validation."

    # Cas 4 : plusieurs champs
    labels = [_humanize_field(k) or k for k in field_errors.keys()]
    labels_display = ", ".join(labels[:5])
    if len(labels) > 5:
        labels_display += f" (+{len(labels) - 5} autres)"
    return f"{len(field_errors)} champs invalides : {labels_display}"


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request_id = str(uuid.uuid4())

    # Récupère l'ID de requête depuis le middleware s'il est présent
    request = context.get("request") if isinstance(context, dict) else None
    if request is not None:
        header_rid = request.META.get("HTTP_X_REQUEST_ID", "").strip()
        if header_rid:
            request_id = header_rid

    if response is None:
        logger.exception("Unhandled exception", extra={"request_id": request_id})
        return Response(
            {
                "error": {
                    "code": "internal_error",
                    "message": "Erreur interne du serveur.",
                    "request_id": request_id,
                }
            },
            status=500,
        )

    code = getattr(exc, "default_code", "error")
    detail = response.data if isinstance(response.data, dict) else {"detail": response.data}
    message = _build_message(detail)

    payload = {
        "error": {
            "code": code,
            "message": message,
            "details": detail,
            "request_id": request_id,
        }
    }
    response.data = payload
    return response
