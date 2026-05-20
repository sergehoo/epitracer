from rest_framework import serializers

from .models import Disease, RiskFactor, Symptom


class SymptomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Symptom
        fields = ["id", "uuid", "code", "label", "weight", "is_red_flag", "order"]


class RiskFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskFactor
        fields = ["id", "uuid", "code", "label", "weight", "description"]


class DiseaseSerializer(serializers.ModelSerializer):
    symptoms = SymptomSerializer(many=True, read_only=True)
    risk_factors = RiskFactorSerializer(many=True, read_only=True)

    class Meta:
        model = Disease
        fields = [
            "id", "uuid", "code", "name", "short_name", "description",
            "icd11_code", "severity", "color",
            "incubation_min_days", "incubation_max_days",
            "surveillance_days", "quarantine_days",
            "transmission_modes", "risk_countries",
            "case_definition", "protocols", "notification_rules",
            "is_active", "requires_quarantine", "requires_pass",
            "symptoms", "risk_factors",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "uuid", "created_at", "updated_at"]
