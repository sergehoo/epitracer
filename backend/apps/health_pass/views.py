from django.http import FileResponse, Http404, HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import RoleCode
from apps.audit.services import audit
from apps.core.permissions import HasRole, IsAuthenticatedAndActive
from apps.diseases.models import Disease
from apps.travelers.models import Traveler

from .crypto import public_key_pem, public_kid
from .models import HealthPass, PassBlacklistEntry, PassVerificationLog
from .serializers import (
    HealthPassIssueSerializer,
    HealthPassSerializer,
    PassBlacklistSerializer,
    PassVerificationLogSerializer,
    QRVerifyRequestSerializer,
)
from .services import issue_pass, revoke_pass, verify_pass


class HealthPassViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HealthPass.objects.select_related("traveler", "disease").all()
    serializer_class = HealthPassSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
        RoleCode.DISTRICT, RoleCode.ENTRY_POINT,
        RoleCode.BORDER_AGENT, RoleCode.FIELD_AGENT, RoleCode.OBSERVER,
    ]
    lookup_field = "pass_number"
    filterset_fields = ["status", "risk_level", "disease", "traveler"]
    search_fields = ["pass_number", "traveler__public_id", "traveler__last_name"]

    @extend_schema(request=HealthPassIssueSerializer, responses=HealthPassSerializer)
    @action(detail=False, methods=["post"], url_path="issue")
    def issue(self, request):
        ser = HealthPassIssueSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        traveler = Traveler.objects.get(pk=ser.validated_data["traveler"])
        disease = Disease.objects.get(code=ser.validated_data["disease_code"])
        hp = issue_pass(
            traveler=traveler,
            disease=disease,
            risk_level=ser.validated_data.get("risk_level", "low"),
            risk_score=ser.validated_data.get("risk_score", 0),
            investigation_ref=ser.validated_data.get("investigation_ref", ""),
            ttl_days=ser.validated_data.get("ttl_days"),
        )
        audit(request, action="qr_generate", summary=f"Émission pass {hp.pass_number}", target=hp)
        return Response(HealthPassSerializer(hp).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, pass_number=None):
        hp = self.get_object()
        reason = request.data.get("reason", "")
        revoke_pass(hp, user=request.user, reason=reason)
        audit(request, action="qr_revoke", summary=f"Révocation pass {hp.pass_number}", target=hp,
              payload={"reason": reason})
        return Response(HealthPassSerializer(hp).data)

    @action(detail=True, methods=["get"], url_path="pdf")
    def download_pdf(self, request, pass_number=None):
        hp = self.get_object()
        if not hp.pdf_file:
            raise Http404("PDF non disponible.")
        return FileResponse(open(hp.pdf_file.path, "rb"), as_attachment=True, filename=f"{hp.pass_number}.pdf")


class QRVerifyView(APIView):
    """Endpoint public (rate-limité) pour vérifier un QR depuis n'importe quel scanner."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "qr_verify"

    @extend_schema(request=QRVerifyRequestSerializer, responses=OpenApiResponse(description="Résultat vérif"))
    def post(self, request):
        ser = QRVerifyRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        from apps.geo.models import EntryPoint

        ep = None
        if ser.validated_data.get("entry_point"):
            ep = EntryPoint.objects.filter(pk=ser.validated_data["entry_point"]).first()
        result = verify_pass(
            ser.validated_data["token"],
            entry_point=ep,
            user=request.user if request.user.is_authenticated else None,
            online=ser.validated_data.get("online", True),
        )
        audit(request, action="qr_verify", summary=f"Vérification QR ({result.get('reason') or 'ok'})",
              payload={"is_valid": result["is_valid"], "reason": result.get("reason")})
        return Response(result)


class PublicKeyView(APIView):
    """Expose la clé publique Ed25519 (PEM) pour les vérifications offline tierces."""

    permission_classes = [AllowAny]

    def get(self, request):
        return HttpResponse(public_key_pem(), content_type="application/x-pem-file",
                            headers={"X-Pass-Kid": public_kid()})


class PassBlacklistViewSet(viewsets.ModelViewSet):
    queryset = PassBlacklistEntry.objects.select_related("added_by").all()
    serializer_class = PassBlacklistSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)


class PassVerificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PassVerificationLog.objects.select_related("pass_obj", "verified_by", "entry_point").all()[:5000]
    serializer_class = PassVerificationLogSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
        RoleCode.DISTRICT, RoleCode.ENTRY_POINT, RoleCode.OBSERVER,
    ]
    filterset_fields = ["is_valid", "entry_point", "pass_number"]
