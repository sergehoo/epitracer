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

    def post(self, request, *args, **kwargs):
        """Override pour :
          - Tracer les échecs login (compteur + lock auto après 5 essais)
          - Auto-envoyer le code OTP email à la 1ère étape (password OK mais
            mfa_code manquant → on génère et envoie le code immédiatement)
        """
        from django.contrib.auth import get_user_model
        from django.utils import timezone
        from datetime import timedelta

        User = get_user_model()
        email = (request.data.get("email") or "").strip().lower()

        try:
            response = super().post(request, *args, **kwargs)
        except Exception as exc:
            # Vérifie si l'erreur indique "MFA requise" → envoyer auto le code
            from rest_framework.exceptions import ValidationError
            if isinstance(exc, ValidationError) and isinstance(exc.detail, dict):
                if exc.detail.get("mfa_required"):
                    user = User.objects.filter(email=email).first()
                    if user and user.mfa_enabled:
                        # Génère + envoie le code OTP — best-effort
                        from apps.accounts.services.email_otp import send_otp_email
                        try:
                            send_otp_email(user, request=request)
                        except Exception:
                            pass
                    # Re-lever l'erreur pour que le frontend voit mfa_required
                    raise exc

                # Échec password → incrémente compteur + lock après 5
                if "detail" in exc.detail or "non_field_errors" in exc.detail:
                    user = User.objects.filter(email=email).first()
                    if user and not user.is_locked:
                        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
                        if user.failed_login_attempts >= 5:
                            user.locked_until = timezone.now() + timedelta(minutes=15)
                            user.failed_login_attempts = 0
                            user.save(update_fields=[
                                "failed_login_attempts", "locked_until", "updated_at",
                            ])
                        else:
                            user.save(update_fields=["failed_login_attempts", "updated_at"])
            raise

        return response


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
        """Réinit admin : génère un mot de passe temporaire ET un lien tokenisé.

        - Le mot de passe temporaire est renvoyé immédiatement (compat
          historique : l'admin peut le copier et le donner à l'agent en main
          propre s'il ne peut pas attendre l'email).
        - En parallèle, un email avec lien sécurisé tokenisé est envoyé
          depuis inhp@veillesanitaire.com via Celery.
        """
        u = self.get_object()
        new_pwd = secrets.token_urlsafe(12)
        u.set_password(new_pwd)
        u.save(update_fields=["password"])

        # Génère + envoie l'email tokenisé (best-effort, ne bloque pas la réponse)
        try:
            from apps.notifications.services.email_router import generate_password_reset_token
            from apps.notifications.tasks_email import send_password_reset_email
            raw_token, _ = generate_password_reset_token(u, request=request)
            send_password_reset_email.delay(u.pk, raw_token)
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger("epidemitracker.accounts").warning(
                "Envoi email reset password échoué (user_id=%s)", u.pk, exc_info=True,
            )

        return Response({
            "detail": "Mot de passe réinitialisé. Un email avec lien sécurisé "
                      "a également été envoyé à l'utilisateur.",
            "temporary_password": new_pwd,
        })


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


# ===========================================================================
# MFA EMAIL — endpoints
# ===========================================================================

class MfaEmailEnableView(APIView):
    """POST /auth/mfa/email/enable/ — active la MFA email pour soi-même."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.mfa_enabled = True
        request.user.save(update_fields=["mfa_enabled"])
        return Response({
            "ok": True,
            "mfa_enabled": True,
            "detail": "MFA email activée. Vous recevrez un code à chaque connexion.",
        })


class MfaEmailDisableView(APIView):
    """POST /auth/mfa/email/disable/ — désactive la MFA email pour soi-même."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.mfa_enforced:
            return Response(
                {"detail": "MFA imposée par l'administrateur — désactivation refusée."},
                status=403,
            )
        request.user.mfa_enabled = False
        request.user.save(update_fields=["mfa_enabled"])
        return Response({"ok": True, "mfa_enabled": False})


class MfaEmailResendView(APIView):
    """POST /auth/mfa/email/resend/ — renvoie un nouveau code OTP.

    Public (pas auth). Body: {"email": "user@..."}. Pas de leak si email inexistant.
    Rate limit pour éviter le spam.
    """
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mfa_resend"  # à configurer côté settings : 6/min/IP par ex.

    def post(self, request):
        from django.contrib.auth import get_user_model
        from apps.accounts.services.email_otp import send_otp_email

        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return Response({"detail": "Email requis."}, status=400)

        User = get_user_model()
        user = User.objects.filter(email=email, is_active=True).first()
        if user and user.mfa_enabled:
            send_otp_email(user, request=request)
        # Réponse identique pour éviter de leaker l'existence de l'email
        return Response({"ok": True, "detail": "Si un compte avec MFA existe, un code a été envoyé."})


# ===========================================================================
# PASSWORD RESET PUBLIC — request + confirm
# ===========================================================================

class PasswordResetRequestView(APIView):
    """POST /auth/password-reset/request/ — demande publique de reset par email."""
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        from django.contrib.auth import get_user_model
        from apps.notifications.services.email_router import generate_password_reset_token
        from apps.notifications.tasks_email import send_password_reset_email

        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return Response({"detail": "Email requis."}, status=400)

        User = get_user_model()
        user = User.objects.filter(email=email, is_active=True).first()
        if user:
            try:
                raw_token, _ = generate_password_reset_token(user, request=request)
                send_password_reset_email.delay(user.pk, raw_token)
            except Exception:
                pass
        # Réponse identique dans tous les cas (anti-énumération)
        return Response({
            "ok": True,
            "detail": "Si un compte existe avec cet email, un lien a été envoyé.",
        })


class PasswordResetConfirmView(APIView):
    """POST /auth/password-reset/confirm/ — soumission du nouveau password via token."""
    permission_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError as DjValidationError
        from apps.notifications.services.email_router import consume_password_reset_token

        raw_token = (request.data.get("token") or "").strip()
        new_password = (request.data.get("new_password") or "").strip()

        if not raw_token or not new_password:
            return Response({"detail": "Token et nouveau mot de passe requis."}, status=400)

        user = consume_password_reset_token(raw_token)
        if not user:
            return Response({"detail": "Token invalide ou expiré."}, status=400)

        try:
            validate_password(new_password, user=user)
        except DjValidationError as exc:
            return Response({"detail": " ".join(exc.messages)}, status=400)

        user.set_password(new_password)
        # Reset les compteurs sécurité
        user.must_change_password = False
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_password_change = timezone.now()
        user.save(update_fields=[
            "password", "must_change_password", "failed_login_attempts",
            "locked_until", "last_password_change",
        ])
        return Response({"ok": True, "detail": "Mot de passe réinitialisé."})
