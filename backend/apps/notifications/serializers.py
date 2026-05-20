from rest_framework import serializers

from .models import Notification, NotificationTemplate


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = ["id", "uuid", "code", "name", "description", "subject", "body", "channels", "is_active"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "uuid", "channel", "template", "recipient",
            "subject", "body", "context", "status", "provider", "provider_id",
            "error", "attempts", "sent_at", "created_at",
        ]
        read_only_fields = ["status", "provider", "provider_id", "error", "attempts", "sent_at"]
