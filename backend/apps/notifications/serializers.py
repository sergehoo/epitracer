from rest_framework import serializers

from .models import (
    Notification, NotificationAuditLog, NotificationProviderConfig,
    NotificationTemplate,
)


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
            "error_message", "retry_count", "max_retries",
            "sent_by", "sent_by_email",
            "queued_at", "sent_at", "delivered_at", "failed_at",
            "metadata", "created_at", "updated_at",
        ]
        read_only_fields = [
            "status", "provider", "provider_message_id", "error_message",
            "retry_count", "queued_at", "sent_at", "delivered_at", "failed_at",
            "normalized_phone", "masked_recipient", "sent_by_email",
            "template_code", "template_name", "traveler_public_id",
        ]


class SendNotificationSerializer(serializers.Serializer):
    """Payload pour POST /api/v1/notifications/send/"""
    channel = serializers.ChoiceField(choices=["sms", "whatsapp"])
    traveler = serializers.IntegerField(required=False, allow_null=True)
    recipient = serializers.CharField(required=False, allow_blank=True)
    template_code = serializers.CharField(required=False, allow_blank=True)
    body = serializers.CharField(required=False, allow_blank=True)
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
