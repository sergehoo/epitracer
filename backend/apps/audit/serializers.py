from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", read_only=True, default=None)
    target_type = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id", "created_at", "actor", "actor_email", "action", "summary",
            "target_type", "target_id", "payload", "ip_address", "user_agent", "request_id",
        ]

    def get_target_type(self, obj):
        return obj.target_ct.model if obj.target_ct_id else None
