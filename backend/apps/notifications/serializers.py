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
