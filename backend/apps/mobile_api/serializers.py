"""Serializers DRF dédiés à l'API mobile.

Tous les champs sont aplatis (snake_case → snake_case, pas de nested complexes)
pour faciliter le mapping côté Flutter avec freezed + json_serializable.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import User
from apps.health_pass.models import HealthPass

from .models import (
    AssistanceRequest, LocationShare, MobileDevice, Vaccination,
)


# ---------------------------------------------------------------------------
# Profil utilisateur courant
# ---------------------------------------------------------------------------
class MobileProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    has_active_followup = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "uuid", "email", "full_name", "first_name", "last_name",
            "phone", "mfa_enabled", "has_active_followup",
        ]
        read_only_fields = fields

    def get_full_name(self, obj) -> str:
        return obj.display_name

    def get_has_active_followup(self, obj) -> bool:
        # Heuristique : si on a un traveler lié avec un followup non clos
        try:
            from apps.companion.models import FollowupTracking
            return FollowupTracking.objects.filter(
                traveler__email=obj.email, status="active",
            ).exists()
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Pass sanitaires
# ---------------------------------------------------------------------------
class MobilePassSerializer(serializers.ModelSerializer):
    """Pass aplati pour mobile — inclut le payload QR signé."""
    disease_code = serializers.SerializerMethodField()
    disease_name = serializers.SerializerMethodField()
    traveler_full_name = serializers.SerializerMethodField()
    entry_point_name = serializers.SerializerMethodField()
    issued_at = serializers.DateTimeField(source="created_at", read_only=True)
    qr_payload = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = HealthPass
        fields = [
            "id", "uuid", "pass_number", "public_id", "status",
            "disease_code", "disease_name", "traveler_full_name",
            "entry_point_name", "issued_at", "expires_at",
            "qr_payload", "pdf_url",
        ]
        read_only_fields = fields

    def get_disease_code(self, obj) -> str:
        if obj.traveler_id and getattr(obj.traveler, "disease", None):
            return obj.traveler.disease.code
        return "EBOLA"

    def get_disease_name(self, obj) -> str:
        if obj.traveler_id and getattr(obj.traveler, "disease", None):
            return obj.traveler.disease.name
        return "Ebola"

    def get_traveler_full_name(self, obj) -> str:
        if obj.traveler_id:
            t = obj.traveler
            return f"{t.first_name} {t.last_name}".strip()
        return ""

    def get_entry_point_name(self, obj):
        if obj.traveler_id and obj.traveler.entry_point_id:
            return obj.traveler.entry_point.name
        return None

    def get_qr_payload(self, obj) -> str:
        # On retourne le payload signé (utilisé par scan offline)
        try:
            from apps.health_pass.services import build_qr_payload
            return build_qr_payload(obj)
        except Exception:
            return obj.pass_number

    def get_pdf_url(self, obj):
        request = self.context.get("request")
        if obj.pdf_file and request:
            return request.build_absolute_uri(obj.pdf_file.url)
        return None


# ---------------------------------------------------------------------------
# Vaccinations
# ---------------------------------------------------------------------------
class VaccinationSerializer(serializers.ModelSerializer):
    certificate_pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Vaccination
        fields = [
            "id", "uuid", "disease_code", "disease_name", "vaccine_name",
            "manufacturer", "lot_number", "administered_at", "next_dose_at",
            "dose_number", "total_doses", "center_name", "country_code",
            "certificate_pdf", "certificate_pdf_url", "qr_payload",
            "verified", "notes", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "uuid", "verified", "created_at", "updated_at",
                            "certificate_pdf_url"]
        extra_kwargs = {
            "certificate_pdf": {"write_only": True, "required": False},
        }

    def get_certificate_pdf_url(self, obj):
        if obj.certificate_pdf:
            request = self.context.get("request")
            return request.build_absolute_uri(obj.certificate_pdf.url) if request else obj.certificate_pdf.url
        return None


# ---------------------------------------------------------------------------
# Suivi 21 jours
# ---------------------------------------------------------------------------
class FollowupSummarySerializer(serializers.Serializer):
    """Vue agrégée du suivi pour l'écran d'accueil mobile."""
    active = serializers.BooleanField()
    day = serializers.IntegerField()
    total_days = serializers.IntegerField()
    started_at = serializers.DateField(required=False, allow_null=True)
    ends_at = serializers.DateField(required=False, allow_null=True)
    checkin_today_done = serializers.BooleanField()


class CheckinCreateSerializer(serializers.Serializer):
    """POST /api/mobile/checkins/ — payload journalier de check-in."""
    feeling_well = serializers.BooleanField(default=True)
    fever = serializers.BooleanField(default=False)
    unusual_fatigue = serializers.BooleanField(default=False)
    headache = serializers.BooleanField(default=False)
    muscle_pain = serializers.BooleanField(default=False)
    vomiting_or_diarrhea = serializers.BooleanField(default=False)
    unexplained_bleeding = serializers.BooleanField(default=False)
    wants_contact = serializers.BooleanField(default=False)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)


# ---------------------------------------------------------------------------
# Push device registration
# ---------------------------------------------------------------------------
class MobileDeviceRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = MobileDevice
        fields = [
            "fcm_token", "platform", "device_id",
            "app_version", "os_version", "locale",
        ]


# ---------------------------------------------------------------------------
# Assistance
# ---------------------------------------------------------------------------
class AssistanceRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistanceRequest
        fields = [
            "id", "uuid", "reason", "message", "callback_phone",
            "preferred_time", "latitude", "longitude", "status", "created_at",
        ]
        read_only_fields = ["id", "uuid", "status", "created_at"]


# ---------------------------------------------------------------------------
# Partage position
# ---------------------------------------------------------------------------
class LocationShareCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationShare
        fields = ["id", "uuid", "latitude", "longitude", "accuracy_m", "context", "created_at"]
        read_only_fields = ["id", "uuid", "created_at"]


# ---------------------------------------------------------------------------
# QR Import (ajout d'un pass scanné dans la wallet)
# ---------------------------------------------------------------------------
class QrImportSerializer(serializers.Serializer):
    """POST /api/mobile/qr/import/ — body : { qr_payload: 'epitrace://...' }"""
    qr_payload = serializers.CharField()


# ---------------------------------------------------------------------------
# Notifications (lecture)
# ---------------------------------------------------------------------------
class MobileNotificationSerializer(serializers.Serializer):
    """Vue mobile-friendly d'une notification (lecture seule)."""
    id = serializers.IntegerField()
    title = serializers.CharField()
    body = serializers.CharField()
    status = serializers.CharField()
    channel = serializers.CharField()
    created_at = serializers.DateTimeField()
    read = serializers.BooleanField(default=False)
