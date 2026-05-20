"""Middleware d'audit : attache l'IP/UA/request_id à la requête pour les écritures."""
from __future__ import annotations

import uuid


class AuditContextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.audit_request_id = str(uuid.uuid4())
        request.audit_ip = (
            request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR")
        )
        request.audit_user_agent = request.META.get("HTTP_USER_AGENT", "")[:400]
        response = self.get_response(request)
        response["X-Request-ID"] = request.audit_request_id
        return response
