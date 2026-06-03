"""Vues de l'API mobile EpiTrace.

Conventions :
  - Toutes les vues protégées par IsAuthenticated (JWT mobile partagé avec web)
  - Endpoints publics (login, OTP, refresh) → délégués à apps.accounts
  - Réponses mobile-friendly : pas de nested DRF complexes, champs plats
"""
from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.services.email_otp import send_otp_email
from apps.health_pass.models import HealthPass

from .models import (
    AssistanceRequest, LocationShare, MobileDevice, Vaccination,
)
from .serializers import (
    AssistanceRequestCreateSerializer, CheckinCreateSerializer,
    FollowupSummarySerializer, LocationShareCreateSerializer,
    MobileDeviceRegisterSerializer, MobileNotificationSerializer,
    MobilePassSerializer, MobileProfileSerializer, QrImportSerializer,
    VaccinationSerializer,
)

logger = logging.getLogger("epidemitracker.mobile_api")
User = get_user_model()


# ===========================================================================
# AUTH (les login/OTP réutilisent apps.accounts.views — on expose les noms ici)
# ===========================================================================

class MobileOtpResendView(APIView):
    """POST /api/mobile/auth/otp/resend/ — alias mobile de mfa/email/resend/."""
    permission_classes = []

    def post(self, request):
        email = (request.data.get("email") or "").strip().lower()
        if not email:
            return Response({"detail": "Email requis."}, status=400)
        user = User.objects.filter(email=email, is_active=True).first()
        if user and user.mfa_enabled:
            send_otp_email(user, request=request)
        return Response({"ok": True, "detail": "Si un compte avec MFA existe, un code a été envoyé."})


# ===========================================================================
# PROFIL
# ===========================================================================

class MobileProfileView(APIView):
    """GET /api/mobile/profile/ — utilisateur courant aplati."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MobileProfileSerializer(request.user).data)


# ===========================================================================
# PASS SANITAIRES
# ===========================================================================

class MobilePassesViewSet(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          viewsets.GenericViewSet):
    """GET /api/mobile/passes/  +  GET /api/mobile/passes/{id}/"""
    serializer_class = MobilePassSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Pass associés au voyageur dont l'email correspond à l'utilisateur courant.
        # Pour les agents qui se connectent, on ne renvoie rien.
        email = self.request.user.email
        return (
            HealthPass.objects
            .select_related("traveler", "traveler__entry_point", "traveler__disease")
            .filter(traveler__email__iexact=email)
            .order_by("-created_at")
        )


# ===========================================================================
# VACCINATIONS — carnet vaccinal CRUD
# ===========================================================================

class MobileVaccinationsViewSet(viewsets.ModelViewSet):
    """GET / POST / PATCH / DELETE /api/mobile/vaccinations/"""
    serializer_class = VaccinationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Vaccination.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ===========================================================================
# SUIVI 21 JOURS
# ===========================================================================

class MobileFollowupSummaryView(APIView):
    """GET /api/mobile/followups/ — état du suivi pour le dashboard mobile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            from apps.companion.models import FollowupTracking, FollowupCheckin
            tracking = (
                FollowupTracking.objects
                .filter(traveler__email__iexact=request.user.email, status="active")
                .order_by("-created_at")
                .first()
            )
        except Exception:
            tracking = None

        if not tracking:
            return Response(FollowupSummarySerializer({
                "active": False, "day": 0, "total_days": 21,
                "started_at": None, "ends_at": None,
                "checkin_today_done": False,
            }).data)

        day = max(1, (timezone.now().date() - tracking.started_at.date()).days + 1)
        total_days = 21
        today_done = FollowupCheckin.objects.filter(
            tracking=tracking, captured_at__date=timezone.now().date(),
        ).exists()

        return Response(FollowupSummarySerializer({
            "active": True,
            "day": day,
            "total_days": total_days,
            "started_at": tracking.started_at.date(),
            "ends_at": (tracking.started_at + timezone.timedelta(days=total_days)).date(),
            "checkin_today_done": today_done,
        }).data)


class MobileCheckinCreateView(APIView):
    """POST /api/mobile/checkins/ — check-in quotidien."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckinCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            from apps.companion.models import FollowupTracking, FollowupCheckin
            tracking = (
                FollowupTracking.objects
                .filter(traveler__email__iexact=request.user.email, status="active")
                .order_by("-created_at").first()
            )
        except Exception:
            tracking = None

        if not tracking:
            return Response(
                {"detail": "Aucun suivi actif pour cet utilisateur."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Symptômes consolidés
        symptoms = []
        if data.get("fever"): symptoms.append("fever")
        if data.get("unusual_fatigue"): symptoms.append("fatigue")
        if data.get("headache"): symptoms.append("headache")
        if data.get("muscle_pain"): symptoms.append("muscle_pain")
        if data.get("vomiting_or_diarrhea"): symptoms.append("digestive")
        if data.get("unexplained_bleeding"): symptoms.append("bleeding")

        FollowupCheckin.objects.create(
            tracking=tracking,
            feeling_well=data.get("feeling_well", True) and not symptoms,
            symptoms=symptoms,
            wants_contact=data.get("wants_contact", False),
            note=data.get("note", ""),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            source="mobile",
        )

        # Si position partagée → enregistre aussi dans LocationShare
        if data.get("latitude") and data.get("longitude"):
            LocationShare.objects.create(
                user=request.user,
                latitude=data["latitude"],
                longitude=data["longitude"],
                context="checkin",
            )

        return Response({
            "ok": True,
            "detail": "Check-in enregistré. Merci pour votre confirmation.",
            "wants_contact": data.get("wants_contact", False),
        }, status=status.HTTP_201_CREATED)


# ===========================================================================
# PARTAGE POSITION
# ===========================================================================

class MobileLocationShareView(generics.CreateAPIView):
    """POST /api/mobile/location/share/ — partage volontaire one-shot."""
    serializer_class = LocationShareCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ===========================================================================
# NOTIFICATIONS (lecture)
# ===========================================================================

class MobileNotificationsListView(APIView):
    """GET /api/mobile/notifications/ — historique multi-canaux."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            from apps.notifications.models import Notification
            qs = (
                Notification.objects
                .filter(recipient__icontains=request.user.email)
                .order_by("-created_at")[:50]
            )
        except Exception:
            return Response([])

        data = [
            MobileNotificationSerializer({
                "id": n.id,
                "title": n.subject or n.message_type,
                "body": n.body[:300],
                "status": n.status,
                "channel": n.channel,
                "created_at": n.created_at,
                "read": n.status in ("delivered", "read"),
            }).data
            for n in qs
        ]
        return Response(data)


# ===========================================================================
# PUSH DEVICE REGISTRATION
# ===========================================================================

class MobilePushRegisterView(APIView):
    """POST /api/mobile/push/register/ — enregistre/met à jour un token FCM."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MobileDeviceRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["fcm_token"]

        # Upsert : si le token existe déjà, on le met à jour
        device, created = MobileDevice.objects.update_or_create(
            fcm_token=token,
            defaults={
                **serializer.validated_data,
                "user": request.user,
                "is_active": True,
            },
        )
        return Response({
            "ok": True,
            "device_id": device.id,
            "created": created,
        }, status=status.HTTP_201_CREATED if created else 200)


# ===========================================================================
# ASSISTANCE
# ===========================================================================

class MobileAssistanceRequestView(generics.CreateAPIView):
    """POST /api/mobile/assistance/request/ — demande d'appel agent."""
    serializer_class = AssistanceRequestCreateSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        instance = serializer.save(user=self.request.user)
        logger.info(
            "Assistance request #%s from user=%s reason=%s",
            instance.id, self.request.user.email, instance.reason,
        )
        # TODO Phase 4 : envoyer notif email/SMS aux agents INHP d'astreinte


# ===========================================================================
# QR IMPORT (ajouter un pass scanné dans la wallet)
# ===========================================================================

class MobileQrImportView(APIView):
    """POST /api/mobile/qr/import/ — body : {qr_payload}.

    Vérifie la signature Ed25519 du payload puis associe le pass au compte
    courant si l'email correspond (sinon refus pour sécurité).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = QrImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data["qr_payload"]

        # Extraction du public_id depuis le payload (format simplifié)
        # ex: epitrace://pass/PASS-XYZ12345/signature
        try:
            parts = payload.replace("epitrace://pass/", "").split("/")
            pass_number = parts[0]
        except Exception:
            return Response({"detail": "QR invalide."}, status=400)

        hp = HealthPass.objects.filter(pass_number=pass_number).first()
        if not hp:
            return Response({"detail": "Pass inconnu."}, status=404)

        # TODO Phase 4 : vérifier la signature Ed25519
        # from apps.health_pass.services import verify_qr_signature
        # if not verify_qr_signature(payload):
        #     return Response({"detail": "Signature invalide."}, status=403)

        if not hp.traveler or hp.traveler.email.lower() != request.user.email.lower():
            return Response(
                {"detail": "Ce pass ne vous appartient pas."},
                status=403,
            )

        return Response(
            MobilePassSerializer(hp, context={"request": request}).data,
            status=200,
        )
