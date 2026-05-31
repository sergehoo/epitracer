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
        from django.utils import timezone
        from apps.accounts.services.email_otp import verify_otp

        mfa_code = attrs.pop("mfa_code", "") or ""
        data = super().validate(attrs)

        user = self.user

        # ── Vérouillage compte (manuel ou temporaire automatique) ─────
        if user.is_locked:
            raise serializers.ValidationError({"detail": "Compte verrouillé. Contactez l'administrateur."})
        if user.locked_until and user.locked_until > timezone.now():
            remaining_min = int((user.locked_until - timezone.now()).total_seconds() / 60) + 1
            raise serializers.ValidationError({
                "detail": f"Compte verrouillé temporairement. Réessayer dans {remaining_min} minute(s).",
            })

        # ── Vérification MFA email si activée pour l'utilisateur ──────
        if user.mfa_enabled:
            if not mfa_code:
                # 1ère étape : email/password OK → backend va envoyer le code OTP
                raise serializers.ValidationError({
                    "mfa": "Code MFA requis.",
                    "mfa_required": True,
                    "mfa_method": "email",
                    "email_masked": _mask_email(user.email),
                })
            # 2ème étape : vérification du code OTP saisi
            result = verify_otp(user, mfa_code)
            if not result.ok:
                raise serializers.ValidationError({
                    "mfa": result.error,
                    "mfa_required": True,
                    "mfa_method": "email",
                    "attempts_remaining": result.attempts_remaining,
                })

        # ── Reset compteur d'échecs sur connexion réussie ─────────────
        if user.failed_login_attempts > 0:
            user.failed_login_attempts = 0
            user.locked_until = None
            user.save(update_fields=["failed_login_attempts", "locked_until"])

        data["user"] = UserSerializer(user).data
        # Le client sait s'il doit forcer le changement de mot de passe
        data["must_change_password"] = bool(user.must_change_password)
        return data


def _mask_email(email: str) -> str:
    """Masque l'email pour l'affichage UI : `j*****h@domain.com`."""
    if not email or "@" not in email:
        return email or ""
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked = local[0] + "*"
    else:
        masked = local[0] + "*" * (len(local) - 2) + local[-1]
    return f"{masked}@{domain}"


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
            "phone", "job_title", "is_active", "is_locked",
            "mfa_enabled", "mfa_enforced", "must_change_password",
            "date_joined", "last_login", "roles",
        ]
        read_only_fields = ["id", "uuid", "date_joined", "last_login", "is_locked"]

    def update(self, instance, validated_data):
        """Si l'admin force MFA → active aussi mfa_enabled automatiquement
        (sinon on aurait un état incohérent : 'imposé mais pas activé').
        """
        if validated_data.get("mfa_enforced") is True and not instance.mfa_enabled:
            validated_data["mfa_enabled"] = True
        # Inversement : si on dé-force, on laisse mfa_enabled tel quel
        # (l'utilisateur peut maintenant le désactiver via son profil).
        return super().update(instance, validated_data)

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
    """Création d'un utilisateur depuis l'admin.

    - `password` est OPTIONNEL : s'il n'est pas fourni, on génère un mot de
      passe temporaire fort qui est renvoyé une seule fois dans la réponse
      sous le champ `temporary_password`. L'admin doit le copier/le
      transmettre à l'utilisateur final.
    - `role_codes` reçoit la liste des codes de rôles à affecter directement
      (raccourci pour ne pas appeler /role-assignments/ après).
    """
    # write_only=True + required=False → password optionnel à la création.
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, validators=[validate_password],
    )
    # `username` est calculé depuis l'email si absent dans le payload.
    # Sans `required=False` explicite, DRF reprend le champ du modèle qui
    # est NOT NULL → 400 « Ce champ est obligatoire » avant create().
    username = serializers.CharField(required=False, allow_blank=True)
    role_codes = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False, default=list
    )
    # Champ exposé dans la réponse uniquement quand on a généré un mot de passe.
    temporary_password = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = User
        fields = [
            "id", "uuid", "email", "username", "first_name", "last_name",
            "phone", "job_title", "is_active", "mfa_enforced",
            "password", "role_codes", "temporary_password",
        ]
        read_only_fields = ["id", "uuid", "temporary_password"]

    @staticmethod
    def _generate_temporary_password(length: int = 14) -> str:
        """Mot de passe fort : majuscules + minuscules + chiffres + symboles."""
        import secrets
        import string
        # On évite les caractères ambigus (0/O, 1/l/I) côté humain.
        alphabet = (
            "ABCDEFGHJKLMNPQRSTUVWXYZ"      # majuscules sans I, O
            "abcdefghijkmnopqrstuvwxyz"     # minuscules sans l
            "23456789"                       # chiffres sans 0, 1
            "!@#$%&*+-=?"                    # symboles safe URL
        )
        # Au moins 1 de chaque catégorie pour passer validate_password.
        groups = [
            "ABCDEFGHJKLMNPQRSTUVWXYZ",
            "abcdefghijkmnopqrstuvwxyz",
            "23456789",
            "!@#$%&*+-=?",
        ]
        pw = [secrets.choice(g) for g in groups]
        pw += [secrets.choice(alphabet) for _ in range(length - len(groups))]
        secrets.SystemRandom().shuffle(pw)
        return "".join(pw)

    def create(self, validated):
        role_codes = validated.pop("role_codes", [])
        password = validated.pop("password", "") or ""
        generated = False
        if not password:
            password = self._generate_temporary_password()
            generated = True
            # Sécurité : ré-applique la validation Django sur le password généré.
            try:
                validate_password(password)
            except Exception:
                # Si la politique est très stricte, on regénère 3x max.
                for _ in range(3):
                    password = self._generate_temporary_password(length=18)
                    try:
                        validate_password(password)
                        break
                    except Exception:
                        continue

        # `username` : si vide ou absent → on prend l'email (compatible avec
        # AbstractUser qui exige USERNAME_FIELD non-null).
        if not validated.get("username"):
            validated["username"] = validated["email"]
        user = User(**validated)
        user.set_password(password)
        user.save()

        roles = Role.objects.filter(code__in=role_codes)
        for r in roles:
            RoleAssignment.objects.create(user=user, role=r, is_active=True)

        # Expose le mot de passe temporaire à l'admin qui crée le compte (une
        # seule fois — pas stocké en clair). Le frontend le copie et l'efface.
        if generated:
            user.temporary_password = password  # attribut volatile, lu par to_representation

        # ── Envoi auto de l'email d'activation (depuis inhp@veillesanitaire.com).
        # On enqueue Celery pour ne pas bloquer la requête HTTP, et on
        # avale les exceptions : si l'email part pas, le compte est quand
        # même créé (l'admin a déjà le password temporaire en main).
        try:
            from apps.notifications.tasks_email import send_admin_account_created_email
            send_admin_account_created_email.delay(user.pk, password)
        except Exception:  # noqa: BLE001
            import logging
            logging.getLogger("epidemitracker.accounts").warning(
                "Envoi email création compte échoué (user_id=%s)", user.pk, exc_info=True,
            )
        return user

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Le `temporary_password` est exposé UNIQUEMENT si le serializer
        # vient de le générer dans `create()` (jamais à la lecture normale).
        tmp = getattr(instance, "temporary_password", None)
        if tmp:
            data["temporary_password"] = tmp
        return data


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
