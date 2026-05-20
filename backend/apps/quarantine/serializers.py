from rest_framework import serializers

from .models import DailyCheck, FollowUpVisit, QuarantineRecord


class DailyCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyCheck
        fields = [
            "id", "quarantine", "day_index", "check_date", "temperature_celsius",
            "has_symptoms", "symptoms_details", "reported_by_user", "is_self_reported",
            "notes", "alert_raised", "created_at",
        ]
        read_only_fields = ["alert_raised", "reported_by_user"]


class FollowUpVisitSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source="agent.display_name", read_only=True)

    class Meta:
        model = FollowUpVisit
        fields = [
            "id", "quarantine", "visit_datetime", "agent", "agent_name",
            "found_person", "temperature_celsius", "observations", "photo", "created_at",
        ]


class QuarantineRecordSerializer(serializers.ModelSerializer):
    traveler_public_id = serializers.CharField(source="traveler.public_id", read_only=True)
    disease_code = serializers.CharField(source="disease.code", read_only=True)
    daily_checks = DailyCheckSerializer(many=True, read_only=True)
    visits = FollowUpVisitSerializer(many=True, read_only=True)

    class Meta:
        model = QuarantineRecord
        fields = [
            "id", "uuid", "traveler", "traveler_public_id",
            "disease", "disease_code", "investigation_ref",
            "started_on", "expected_end_on", "actual_end_on",
            "status", "address", "notes", "opened_by",
            "daily_checks", "visits",
            "created_at", "updated_at",
        ]
