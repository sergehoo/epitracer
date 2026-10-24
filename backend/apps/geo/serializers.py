from rest_framework import serializers

from apps.diseases.models import Disease
from apps.surveillance.models import HealthAlert

from .models import Country, CountryRiskAssessment, CountryRiskLevel, EntryPoint, HealthZone


class CurrentRiskSerializer(serializers.ModelSerializer):
    disease_code = serializers.CharField(source="disease.code", read_only=True, default=None)
    disease_name = serializers.CharField(source="disease.name", read_only=True, default=None)

    class Meta:
        model = CountryRiskAssessment
        fields = ["uuid", "disease_code", "disease_name", "risk_level", "valid_from", "valid_until"]


class CountrySerializer(serializers.ModelSerializer):
    # Le niveau se modifie uniquement via les évaluations (historique + justification).
    current_risks = serializers.SerializerMethodField()

    class Meta:
        model = Country
        fields = [
            "id",
            "uuid",
            "code",
            "code3",
            "name",
            "name_local",
            "region",
            "is_monitored",
            "risk_level",
            "risk_for_diseases",
            "current_risks",
        ]
        read_only_fields = ["risk_level", "risk_for_diseases"]

    def get_current_risks(self, obj) -> list[dict]:
        rows = getattr(obj, "current_assessments_list", None)
        if rows is None:
            return []
        return CurrentRiskSerializer(rows, many=True).data

    def validate_code(self, value: str) -> str:
        value = value.strip().upper()
        qs = Country.all_objects.filter(code__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Un pays avec ce code ISO-2 existe déjà.")
        return value

    def validate_code3(self, value: str) -> str:
        value = (value or "").strip().upper()
        if value:
            qs = Country.all_objects.filter(code3__iexact=value)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Un pays avec ce code ISO-3 existe déjà.")
        return value


class CountryRiskAssessmentSerializer(serializers.ModelSerializer):
    country = serializers.SlugRelatedField(slug_field="code", queryset=Country.objects.all())
    country_name = serializers.CharField(source="country.name", read_only=True)
    disease = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Disease.objects.all(),
        required=False,
        allow_null=True,
    )
    disease_name = serializers.CharField(source="disease.name", read_only=True, default=None)
    risk_level = serializers.ChoiceField(choices=CountryRiskLevel.choices)
    source_alert = serializers.SlugRelatedField(
        slug_field="uuid",
        queryset=HealthAlert.objects.all(),
        required=False,
        allow_null=True,
    )
    decided_by_email = serializers.EmailField(
        source="decided_by.email",
        read_only=True,
        default=None,
    )
    superseded_by = serializers.UUIDField(source="superseded_by.uuid", read_only=True, default=None)
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = CountryRiskAssessment
        fields = [
            "id",
            "uuid",
            "country",
            "country_name",
            "disease",
            "disease_name",
            "risk_level",
            "valid_from",
            "valid_until",
            "justification",
            "source_alert",
            "source_reference",
            "decided_by_email",
            "superseded_by",
            "is_current",
            "created_at",
        ]
        read_only_fields = ["id", "uuid", "created_at"]
        extra_kwargs = {"valid_from": {"required": False}}

    def get_is_current(self, obj) -> bool:
        from django.utils import timezone

        today = timezone.localdate()
        return (
            obj.superseded_by_id is None
            and obj.valid_from <= today
            and (obj.valid_until is None or obj.valid_until >= today)
        )


class CloseRiskAssessmentSerializer(serializers.Serializer):
    valid_until = serializers.DateField(required=False)
    reason = serializers.CharField()


class EntryPointSerializer(serializers.ModelSerializer):
    country_code = serializers.CharField(source="country.code", read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = EntryPoint
        fields = [
            "id",
            "uuid",
            "code",
            "name",
            "type",
            "iata_code",
            "icao_code",
            "country",
            "country_code",
            "country_name",
            "region",
            "city",
            "address",
            "latitude",
            "longitude",
            "is_active",
            "notes",
        ]

    def get_latitude(self, obj):
        return obj.location.y if obj.location else None

    def get_longitude(self, obj):
        return obj.location.x if obj.location else None


class HealthZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthZone
        fields = ["id", "uuid", "code", "name", "level", "parent", "risk_level", "population"]
