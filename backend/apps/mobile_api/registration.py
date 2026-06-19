"""Endpoints publics pour le flow d'enregistrement voyageur mobile.

L'app mobile a besoin de connaître la liste des formulaires d'enquête actifs
(Ebola, etc.) AVANT que l'utilisateur soit authentifié. Cette vue expose un
résumé léger : id, code, titre, maladie associée, description, lien web.

Aucun PII n'est exposé ici — uniquement des métadonnées de formulaires
publiables.
"""
from __future__ import annotations

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView


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
            web_url = f"{public_base}/voyageur/inscription"
            if f.code:
                web_url = f"{public_base}/voyageur/inscription?form={f.code}"

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
                "web_url": f"{public_base}/voyageur/inscription",
            })

        return Response({"results": out, "count": len(out)})
