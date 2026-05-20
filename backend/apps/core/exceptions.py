"""Handler d'exceptions API uniforme.

Toutes les erreurs renvoient un objet :
{
  "error": {"code": "..", "message": "..", "details": {...}, "request_id": "..."}
}
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


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    request_id = str(uuid.uuid4())
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

    payload = {
        "error": {
            "code": code,
            "message": str(detail.get("detail", "")) or "Erreur de requête.",
            "details": detail,
            "request_id": request_id,
        }
    }
    response.data = payload
    return response
