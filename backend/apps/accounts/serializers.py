from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Organization, Role, RoleAssignment

User = get_user_model()


# ---------------------------------------------------------------------------
# Auth / JWT
# ---------------------------------------------------------------------------
class EpidemiTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Étend le token JWT pour embarquer les rôles & metadata utilisateur."""

    mfa_code = serializers.CharField(required=False, allow_blank=True)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["roles"] = user.role_codes()
        token["mfa"] = user.mfa_enabled
        token["name"] = user.display_name
        return token

    def validate(self, attrs):
        mfa_code = attrs.pop("mfa_code", "") or ""
        data = super().validate(attrs)

        user = self.user
        if user.is_locked:
            raise serializers.ValidationError({"detail": "Compte verrouillé."})

        # Vérification MFA si activée pour l'utilisateur
        if user.mfa_enabled:
            confirmed_devices = TOTPDevice.objects.filter(user=user, confirmed=True)
            if not confirmed_devices.exists():
                # MFA déclaré actif mais pas d'appareil confirmé → on bloque pour cohérence
                raise serializers.ValidationError(
                    {"mfa": "MFA activée mais aucun appareil TOTP confirmé."}
                )
            if not mfa_code:
                raise serializers.ValidationError(
                    {"mfa": "Code MFA requis.", "mfa_required": True}
                )
            if not any(d.verify_token(mfa_code) for d in confirmed_devices):
                raise serializers.ValidationError({"mfa": "Code MFA invalide."})

        data["user"] = UserSerializer(user).data
        return data


# ---------------------------------------------------------------------------
# Roles / Orgs
# ---------------------------------------------------------------------------
class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "uuid", "code", "name", "type", "parent", "contact_email", "contact_phone", "address"]


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "code", "name", "description", "is_system"]


class RoleAssignmentSerializer(serializers.ModelSerializer):
    role_code = serializers.CharField(source="role.code", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)

    class Meta:
        model = RoleAssignment
        fields = [
            "id", "user", "role", "role_code",
            "organization", "organization_name",
            "is_active", "valid_from", "valid_to",
        ]


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    full_name = serializers.CharField(source="display_name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id", "uuid", "email", "username", "first_name", "last_name", "full_name",
            "phone", "job_title", "is_active", "is_locked", "mfa_enabled",
            "date_joined", "last_login", "roles",
        ]
        read_only_fields = ["id", "uuid", "date_joined", "last_login", "is_locked"]

    def get_roles(self, obj) -> list[dict]:
        return [
            {
                "code": a.role.code,
                "name": a.role.name,
                "organization": a.organization.name if a.organization else None,
            }
            for a in obj.role_assignments.select_related("role", "organization").filter(is_active=True)
        ]


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    role_codes = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False, default=list
    )

    class Meta:
        model = User
        fields = [
            "id", "uuid", "email", "username", "first_name", "last_name",
            "phone", "job_title", "is_active", "password", "role_codes",
        ]
        read_only_fields = ["id", "uuid"]

    def create(self, validated):
        role_codes = validated.pop("role_codes", [])
        password = validated.pop("password")
        validated.setdefault("username", validated["email"])
        user = User(**validated)
        user.set_password(password)
        user.save()
        roles = Role.objects.filter(code__in=role_codes)
        for r in roles:
            RoleAssignment.objects.create(user=user, role=r, is_active=True)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Mot de passe actuel incorrect.")
        return value


# ---------------------------------------------------------------------------
# MFA
# ---------------------------------------------------------------------------
class MFASetupSerializer(serializers.Serializer):
    """Renvoie l'URI otpauth:// + secret pour configurer Google Authenticator."""

    otpauth_url = serializers.CharField(read_only=True)
    secret = serializers.CharField(read_only=True)


class MFAVerifySerializer(serializers.Serializer):
    code = serializers.CharField(max_length=10)
