from rest_framework import serializers

from .models import HealthAlert


class HealthAlertSerializer(serializers.ModelSerializer):
    disease_code = serializers.CharField(source="disease.code", read_only=True, default=None)
    entry_point_name = serializers.CharField(source="entry_point.name", read_only=True, default=None)

    class Meta:
        model = HealthAlert
        fields = [
            "id", "uuid", "code", "title", "description",
            "severity", "status", "disease", "disease_code",
            "entry_point", "entry_point_name", "zone",
            "target_id", "triggered_by",
            "acknowledged_by", "acknowledged_at", "metadata",
            "created_at", "updated_at",
        ]
        read_only_fields = ["uuid", "acknowledged_by", "acknowledged_at"]
