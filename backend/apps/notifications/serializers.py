from rest_framework import serializers

from .models import (
    Channel, MessageType, Notification, NotificationAuditLog, NotificationProviderConfig,
    NotificationTemplate, Provider, ProviderAvailability, ProviderState, SmsSecurityEvent,
)
from .services.errors import friendly_error


def can_see_technical_errors(request) -> bool:
    """Réponses brutes des fournisseurs : administrateurs nationaux seulement."""
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return False
    if user.is_superuser:
        return True
    from apps.accounts.models import RoleCode

    return RoleCode.NATIONAL_ADMIN in user.role_codes()


def sms_segments(body: str) -> int:
    """Nombre de SMS facturés (160 car. seul, 153 par segment concaténé)."""
    n = len(body or "")
    return 1 if n <= 160 else -(-n // 153)


class NotificationTemplateSerializer(serializers.ModelSerializer):
    disease_code = serializers.CharField(source="disease.code", read_only=True, default=None)
    created_by_email = serializers.CharField(source="created_by.email", read_only=True, default=None)

    class Meta:
        model = NotificationTemplate
        fields = [
            "id", "uuid", "code", "name", "description",
            "subject", "body", "channels",
            "is_active", "disease", "disease_code",
            "variables_schema", "created_by", "created_by_email",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_by", "created_by_email"]


class NotificationProviderConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationProviderConfig
        fields = [
            "id", "uuid", "provider", "channel", "is_enabled", "priority",
            "country_code", "sender_name", "metadata",
            "created_at", "updated_at",
        ]


class NotificationAuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", read_only=True, default=None)

    class Meta:
        model = NotificationAuditLog
        fields = [
            "id", "uuid", "action", "actor", "actor_email",
            "ip_address", "user_agent", "metadata", "created_at",
        ]
        read_only_fields = ["created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    template_code = serializers.CharField(source="template.code", read_only=True, default=None)
    template_name = serializers.CharField(source="template.name", read_only=True, default=None)
    traveler_public_id = serializers.CharField(
        source="traveler.public_id", read_only=True, default=None,
    )
    sent_by_email = serializers.CharField(source="sent_by.email", read_only=True, default=None)
    masked_recipient = serializers.CharField(read_only=True)
    traveler_name = serializers.SerializerMethodField()
    # `error_message` est exposé sous forme lisible (jamais la réponse brute
    # du fournisseur) ; le détail technique n'est servi qu'aux admins.
    error_message = serializers.SerializerMethodField()
    error_label = serializers.SerializerMethodField()
    technical_error = serializers.SerializerMethodField()
    sms_segments = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id", "uuid",
            "channel", "template", "template_code", "template_name",
            "traveler", "traveler_public_id",
            "recipient", "normalized_phone", "masked_recipient",
            "subject", "body", "context",
            "direction", "message_type",
            "status", "provider", "provider_message_id",
            "error_message", "error_code", "error_label", "technical_error",
            "retry_count", "max_retries",
            "sent_by", "sent_by_email",
            "queued_at", "sent_at", "delivered_at", "failed_at",
            "metadata", "created_at", "updated_at",
            "traveler_name", "sms_segments",
        ]
        read_only_fields = [
            "status", "provider", "provider_message_id", "error_message",
            "error_code", "retry_count", "queued_at", "sent_at", "delivered_at", "failed_at",
            "normalized_phone", "masked_recipient", "sent_by_email",
            "template_code", "template_name", "traveler_public_id",
        ]

    def _technical_allowed(self) -> bool:
        # Calculé une fois par requête (partagé entre les lignes d'une liste).
        if "_technical_allowed" not in self.context:
            self.context["_technical_allowed"] = can_see_technical_errors(
                self.context.get("request"),
            )
        return self.context["_technical_allowed"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.message_type == MessageType.OTP:
            # Un code de connexion ne s'affiche jamais dans l'historique.
            data["body"] = "Code de connexion à usage unique (masqué)."
            data["context"] = {}
        return data

    def get_traveler_name(self, obj) -> str | None:
        if not obj.traveler_id or obj.traveler is None:
            return None
        return obj.traveler.full_name

    def get_error_label(self, obj) -> str:
        return friendly_error(obj.error_code, obj.error_message)

    def get_error_message(self, obj) -> str:
        return self.get_error_label(obj)

    def get_technical_error(self, obj) -> str | None:
        if not obj.error_message or not self._technical_allowed():
            return None
        return obj.error_message

    def get_sms_segments(self, obj) -> int | None:
        return sms_segments(obj.body) if obj.channel == Channel.SMS else None


class ProviderAvailabilitySerializer(serializers.Serializer):
    """État d'un fournisseur pour le bandeau de la page Notifications."""

    provider = serializers.CharField()
    provider_label = serializers.SerializerMethodField()
    state = serializers.CharField()
    state_label = serializers.SerializerMethodField()
    is_suspended = serializers.BooleanField()
    reason_label = serializers.SerializerMethodField()
    suspended_at = serializers.DateTimeField(allow_null=True)
    last_failure_at = serializers.DateTimeField(allow_null=True)
    blocked_attempts = serializers.IntegerField()
    held_count = serializers.SerializerMethodField()
    resumed_at = serializers.DateTimeField(allow_null=True)
    resumed_by_email = serializers.SerializerMethodField()
    technical_detail = serializers.SerializerMethodField()

    def get_provider_label(self, obj) -> str:
        return Provider(obj.provider).label if obj.provider in Provider.values else obj.provider

    def get_state_label(self, obj) -> str:
        return ProviderState(obj.state).label

    def get_reason_label(self, obj) -> str:
        return friendly_error(obj.reason_code) if obj.reason_code else ""

    def get_held_count(self, obj) -> int:
        return self.context.get("held_counts", {}).get(obj.provider, 0)

    def get_resumed_by_email(self, obj) -> str | None:
        return obj.resumed_by.email if getattr(obj, "resumed_by_id", None) else None

    def get_technical_detail(self, obj) -> str | None:
        if not obj.technical_detail or not can_see_technical_errors(self.context.get("request")):
            return None
        return obj.technical_detail


class SmsSecurityEventSerializer(serializers.ModelSerializer):
    traveler_public_id = serializers.CharField(
        source="traveler.public_id", read_only=True, default=None,
    )
    user_email = serializers.CharField(source="user.email", read_only=True, default=None)

    class Meta:
        model = SmsSecurityEvent
        fields = [
            "id", "uuid", "kind", "severity", "source", "ip_address", "phone_masked",
            "traveler_public_id", "user_email", "details", "created_at",
        ]


def provider_state_rows(providers: list[str]) -> list[ProviderAvailability]:
    """États connus + lignes « disponible » par défaut (non persistées)."""
    known = {
        row.provider: row
        for row in ProviderAvailability.objects.select_related("resumed_by").filter(
            provider__in=providers,
        )
    }
    return [known.get(p) or ProviderAvailability(provider=p) for p in providers]


class SendNotificationSerializer(serializers.Serializer):
    """Payload pour POST /api/v1/notifications/send/"""
    # Canaux supportés :
    #   sms / whatsapp — routés selon le téléphone
    #   email          — routé via EmailRouter (PUBLIC SES pour voyageurs)
    #   push           — notification in-app mobile (FCM) sur les MobileDevice
    #                    actifs liés au voyageur cible (via son email).
    channel = serializers.ChoiceField(
        choices=["sms", "whatsapp", "email", "push", "telegram"],
    )
    traveler = serializers.IntegerField(required=False, allow_null=True)
    recipient = serializers.CharField(required=False, allow_blank=True)
    template_code = serializers.CharField(required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=True)
    # subject : recommandé quand channel='email' (objet du mail).
    subject = serializers.CharField(required=False, allow_blank=True, max_length=200)
    context = serializers.JSONField(required=False)

    def validate(self, data):
        if not data.get("template_code") and not data.get("body"):
            raise serializers.ValidationError(
                "Fournir au moins un template_code OU un body."
            )
        if not data.get("recipient") and not data.get("traveler"):
            raise serializers.ValidationError(
                "Fournir au moins un recipient OU un traveler."
            )
        # Pour email : valider grossièrement le format
        if data.get("channel") == "email" and data.get("recipient"):
            r = data["recipient"].strip()
            if "@" not in r or "." not in r.split("@")[-1]:
                raise serializers.ValidationError(
                    {"recipient": "Adresse email invalide."}
                )
        return data


# ===========================================================================
# Email multi-expéditeur — serializers
# ===========================================================================
from .email_models import (  # noqa: E402
    EmailLog, EmailTemplate, SenderProfile,
)


class SenderProfileSerializer(serializers.ModelSerializer):
    formatted_from = serializers.CharField(read_only=True)

    class Meta:
        model = SenderProfile
        fields = [
            "id", "uuid", "code", "name", "from_address", "from_name",
            "reply_to", "usage_scope", "is_active", "formatted_from",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "uuid", "code", "formatted_from", "created_at", "updated_at"]


class EmailTemplateSerializer(serializers.ModelSerializer):
    sender_profile_code = serializers.CharField(
        source="sender_profile.code", read_only=True, default=None,
    )

    class Meta:
        model = EmailTemplate
        fields = [
            "id", "uuid", "code", "name", "email_type",
            "subject", "body_html", "body_text",
            "sender_profile", "sender_profile_code",
            "variables_schema", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "uuid", "created_at", "updated_at"]


class EmailLogSerializer(serializers.ModelSerializer):
    masked_recipient = serializers.CharField(read_only=True)
    template_code = serializers.CharField(source="template.code", read_only=True, default=None)
    sent_by_email = serializers.CharField(source="sent_by.email", read_only=True, default=None)
    related_user_email = serializers.CharField(source="related_user.email", read_only=True, default=None)
    related_traveler_public_id = serializers.CharField(
        source="related_traveler.public_id", read_only=True, default=None,
    )

    class Meta:
        model = EmailLog
        fields = [
            "id", "uuid", "recipient", "masked_recipient",
            "email_type", "sender_address", "subject",
            "status", "provider_message_id", "error_message",
            "retry_count", "max_retries",
            "template", "template_code", "context",
            "related_user", "related_user_email",
            "related_traveler", "related_traveler_public_id",
            "sent_by", "sent_by_email",
            "sent_at", "delivered_at", "failed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = fields  # lecture seule depuis l'API
