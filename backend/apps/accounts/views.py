from __future__ import annotations

import secrets

from django.contrib.auth import get_user_model
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status, viewsets, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.core.permissions import HasRole, IsAuthenticatedAndActive

from .models import LoginEvent, Organization, Role, RoleAssignment, RoleCode
from .serializers import (
    ChangePasswordSerializer,
    EpidemiTokenObtainPairSerializer,
    MFASetupSerializer,
    MFAVerifySerializer,
    OrganizationSerializer,
    RoleAssignmentSerializer,
    RoleSerializer,
    UserCreateSerializer,
    UserSerializer,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# JWT login (avec MFA)
# ---------------------------------------------------------------------------
class EpidemiTokenObtainPairView(TokenObtainPairView):
    serializer_class = EpidemiTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


# ---------------------------------------------------------------------------
# Me
# ---------------------------------------------------------------------------
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=UserSerializer)
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=ChangePasswordSerializer, responses=OpenApiResponse(description="OK"))
    def post(self, request):
        s = ChangePasswordSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        request.user.set_password(s.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Mot de passe modifié."})


# ---------------------------------------------------------------------------
# MFA (TOTP)
# ---------------------------------------------------------------------------
class MFASetupView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=MFASetupSerializer)
    def post(self, request):
        user = request.user
        # On supprime tout device non confirmé existant pour repartir propre
        TOTPDevice.objects.filter(user=user, confirmed=False).delete()
        device = TOTPDevice.objects.create(
            user=user, name=f"epidemi-{user.email}", confirmed=False
        )
        return Response(
            {"otpauth_url": device.config_url, "secret": device.bin_key.hex()}
        )


class MFAVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=MFAVerifySerializer, responses=OpenApiResponse(description="OK"))
    def post(self, request):
        s = MFAVerifySerializer(data=request.data)
        s.is_valid(raise_exception=True)
        device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
        if not device:
            return Response({"detail": "Aucun device TOTP en attente."}, status=400)
        if not device.verify_token(s.validated_data["code"]):
            return Response({"detail": "Code invalide."}, status=400)
        device.confirmed = True
        device.save(update_fields=["confirmed"])
        request.user.mfa_enabled = True
        request.user.save(update_fields=["mfa_enabled"])
        return Response({"detail": "MFA activée."})


class MFADisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        TOTPDevice.objects.filter(user=request.user).delete()
        request.user.mfa_enabled = False
        request.user.save(update_fields=["mfa_enabled"])
        return Response({"detail": "MFA désactivée."})


# ---------------------------------------------------------------------------
# Admin RBAC
# ---------------------------------------------------------------------------
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]
    search_fields = ["email", "first_name", "last_name", "phone"]
    filterset_fields = ["is_active", "is_locked", "mfa_enabled"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        return UserSerializer

    @action(detail=True, methods=["post"])
    def lock(self, request, pk=None):
        u = self.get_object()
        u.is_locked = True
        u.save(update_fields=["is_locked"])
        return Response({"detail": "Utilisateur verrouillé."})

    @action(detail=True, methods=["post"])
    def unlock(self, request, pk=None):
        u = self.get_object()
        u.is_locked = False
        u.save(update_fields=["is_locked"])
        return Response({"detail": "Utilisateur déverrouillé."})

    @action(detail=True, methods=["post"])
    def reset_password(self, request, pk=None):
        u = self.get_object()
        new_pwd = secrets.token_urlsafe(12)
        u.set_password(new_pwd)
        u.save(update_fields=["password"])
        return Response({"detail": "Mot de passe réinitialisé.", "temporary_password": new_pwd})


class RoleViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Role.objects.all().order_by("code")
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all().order_by("name")
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY]
    search_fields = ["name", "code"]
    filterset_fields = ["type", "parent"]


class RoleAssignmentViewSet(viewsets.ModelViewSet):
    queryset = RoleAssignment.objects.select_related("user", "role", "organization").all()
    serializer_class = RoleAssignmentSerializer
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]
    filterset_fields = ["user", "role", "organization", "is_active"]

    def perform_create(self, serializer):
        serializer.save(granted_by=self.request.user)


class LoginEventListView(APIView):
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY]

    def get(self, request):
        qs = LoginEvent.objects.order_by("-created_at")[:200]
        return Response([
            {
                "created_at": e.created_at,
                "email": e.email_attempted,
                "ip": e.ip_address,
                "ua": e.user_agent,
                "success": e.success,
                "failure_reason": e.failure_reason,
            }
            for e in qs
        ])
