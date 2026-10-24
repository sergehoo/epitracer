"""API du portail : lecture publique des contenus publiés + gestion des annonces."""

from __future__ import annotations

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import exceptions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole, IsAuthenticatedAndActive
from apps.diseases.models import Disease, PublicAlertLevel
from apps.medical.screening import (
    COMMON_SYMPTOM_CODES,
    COMMON_SYMPTOM_FIELDS,
    EBOLA_CODE,
    screening_diseases,
)

from .models import NoticeKind, PublicNotice
from .serializers import (
    PublicDiseaseDetailSerializer,
    PublicDiseaseListSerializer,
    PublicNoticeAdminSerializer,
    PublicNoticeSerializer,
    ScreeningDiseaseSerializer,
)
from .services import archive_notice, publish_notice

PUBLISHER_ROLES = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]


def published_diseases():
    return Disease.objects.filter(is_published=True).exclude(slug="")


def run_service(fn, *args):
    try:
        return fn(*args)
    except DjangoPermissionDenied as exc:
        raise exceptions.PermissionDenied(str(exc)) from exc
    except DjangoValidationError as exc:
        raise serializers.ValidationError(
            getattr(exc, "message_dict", None) or exc.messages
        ) from exc


# ------------------------------------------------------------------- public


class PublicDiseaseListView(APIView):
    """GET /public/diseases/ — maladies publiées.

    Filtres : ?q=, ?active=true, ?alert_level=, ?transmission=.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        qs = published_diseases()
        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(short_name__icontains=q) | Q(description__icontains=q)
            )
        if (request.query_params.get("active") or "").lower() == "true":
            qs = qs.filter(is_active=True)
        level = request.query_params.get("alert_level")
        if level in PublicAlertLevel.values:
            qs = qs.filter(public_alert_level=level)
        transmission = request.query_params.get("transmission")
        if transmission:
            qs = qs.filter(transmission_modes__contains=[transmission])
        qs = qs.select_related("followup_protocol").order_by("-is_active", "name")
        return Response(
            PublicDiseaseListSerializer(qs, many=True, context={"request": request}).data
        )


class PublicDiseaseDetailView(APIView):
    """GET /public/diseases/<slug>/ — fiche détaillée d'une maladie publiée."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request, slug: str):
        disease = get_object_or_404(
            published_diseases().select_related("followup_protocol").prefetch_related("symptoms"),
            slug=slug,
        )
        return Response(PublicDiseaseDetailSerializer(disease, context={"request": request}).data)


class PublicNoticeListView(APIView):
    """GET /public/notices/ — alertes et recommandations publiées (?kind=, ?disease=<slug>)."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        qs = PublicNotice.objects.visible().select_related("disease").prefetch_related("countries")
        kind = request.query_params.get("kind")
        if kind in NoticeKind.values:
            qs = qs.filter(kind=kind)
        slug = request.query_params.get("disease")
        if slug:
            qs = qs.filter(disease__slug=slug, disease__is_published=True)
        return Response(
            PublicNoticeSerializer(qs[:50], many=True, context={"request": request}).data
        )


class RegistrationConfigView(APIView):
    """GET /public/registration-config/ — questionnaire : tronc commun + questions par maladie.

    Ne contient que des libellés de questions (aucun contenu de fiche en
    brouillon) pour les maladies sous surveillance active.
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        diseases = [d for d in screening_diseases() if d.code != EBOLA_CODE]
        ebola_active = screening_diseases().filter(code=EBOLA_CODE).exists()
        # Symptômes supplémentaires : union dédoublonnée, hors tronc commun.
        extra: dict[str, str] = {}
        for d in diseases:
            for s in sorted(d.symptoms.all(), key=lambda s: (s.order, s.label)):
                if s.code not in COMMON_SYMPTOM_CODES and s.code not in extra:
                    extra[s.code] = s.label
        return Response({
            "ebola_questionnaire": ebola_active,
            "common_symptom_fields": COMMON_SYMPTOM_FIELDS,
            "extra_symptoms": [{"code": c, "label": label} for c, label in extra.items()],
            "diseases": ScreeningDiseaseSerializer(diseases, many=True).data,
        })


# -------------------------------------------------------------------- admin


class PublicNoticeAdminViewSet(viewsets.ModelViewSet):
    """Gestion des annonces publiques (brouillon → publication → archivage)."""

    queryset = PublicNotice.objects.select_related("disease", "published_by").prefetch_related(
        "countries",
    )
    serializer_class = PublicNoticeAdminSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"
    filterset_fields = ["kind", "status", "alert_level"]
    search_fields = ["title", "summary"]

    def get_permissions(self):
        if self.action not in {"list", "retrieve"}:
            self.required_roles = PUBLISHER_ROLES
            return [IsAuthenticatedAndActive(), HasRole()]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def publish(self, request, uuid=None):
        notice = run_service(publish_notice, self.get_object(), request.user)
        return Response(self.get_serializer(notice).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, uuid=None):
        notice = run_service(archive_notice, self.get_object(), request.user)
        return Response(self.get_serializer(notice).data)
