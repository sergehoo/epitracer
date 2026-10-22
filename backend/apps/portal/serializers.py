"""Sérialiseurs du portail : lecture publique (contenus publiés) et gestion admin."""

from __future__ import annotations

from django.utils.translation import get_language
from rest_framework import serializers

from apps.diseases.models import Disease, PublicAlertLevel, TransmissionMode
from apps.geo.models import Country
from apps.quarantine.services import followup_duration_days

from .models import PublicNotice
from .services import localized, split_lines

TRANSMISSION_LABELS = dict(TransmissionMode.choices)
ALERT_LABELS = dict(PublicAlertLevel.choices)


class _LocalizedMixin:
    translations_attr = "public_translations"

    def _lang(self) -> str:
        request = self.context.get("request")
        lang = request.query_params.get("lang") if request else None
        return (lang or get_language() or "fr")[:2]

    def tr(self, obj, field: str):
        return localized(obj, field, self._lang(), self.translations_attr)


# ------------------------------------------------------------------- public


class PublicDiseaseListSerializer(_LocalizedMixin, serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    alert_level_label = serializers.SerializerMethodField()
    transmission = serializers.SerializerMethodField()
    followup_days = serializers.SerializerMethodField()
    under_surveillance = serializers.BooleanField(source="is_active", read_only=True)

    class Meta:
        model = Disease
        fields = [
            "slug",
            "code",
            "name",
            "short_name",
            "description",
            "color",
            "public_alert_level",
            "alert_level_label",
            "under_surveillance",
            "transmission",
            "incubation_min_days",
            "incubation_max_days",
            "followup_days",
            "published_at",
            "updated_at",
        ]

    def get_name(self, obj):
        return self.tr(obj, "name")

    def get_description(self, obj):
        return self.tr(obj, "description")

    def get_alert_level_label(self, obj):
        return str(ALERT_LABELS.get(obj.public_alert_level, obj.public_alert_level))

    def get_transmission(self, obj):
        return [str(TRANSMISSION_LABELS.get(m, m)) for m in obj.transmission_modes or []]

    def get_followup_days(self, obj):
        return followup_duration_days(obj)


class PublicNoticeSerializer(_LocalizedMixin, serializers.ModelSerializer):
    translations_attr = "translations"
    title = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    alert_level_label = serializers.SerializerMethodField()
    disease = serializers.SerializerMethodField()
    countries = serializers.SerializerMethodField()

    class Meta:
        model = PublicNotice
        fields = [
            "uuid",
            "kind",
            "title",
            "summary",
            "body",
            "alert_level",
            "alert_level_label",
            "disease",
            "countries",
            "valid_from",
            "valid_until",
            "published_at",
        ]

    def get_title(self, obj):
        return self.tr(obj, "title")

    def get_summary(self, obj):
        return self.tr(obj, "summary")

    def get_body(self, obj):
        return self.tr(obj, "body")

    def get_alert_level_label(self, obj):
        return str(ALERT_LABELS.get(obj.alert_level, obj.alert_level))

    def get_disease(self, obj):
        d = obj.disease
        if d is None or not d.is_published:
            return None
        return {"slug": d.slug, "name": d.name}

    def get_countries(self, obj):
        return [{"code": c.code, "name": c.name} for c in obj.countries.all()]


class PublicDiseaseDetailSerializer(PublicDiseaseListSerializer):
    transmission_details = serializers.SerializerMethodField()
    prevention = serializers.SerializerMethodField()
    traveler_recommendations = serializers.SerializerMethodField()
    symptoms = serializers.SerializerMethodField()
    notices = serializers.SerializerMethodField()

    class Meta(PublicDiseaseListSerializer.Meta):
        fields = PublicDiseaseListSerializer.Meta.fields + [
            "icd11_code",
            "transmission_details",
            "prevention",
            "traveler_recommendations",
            "symptoms",
            "notices",
        ]

    def get_transmission_details(self, obj):
        return self.tr(obj, "transmission_details")

    def get_prevention(self, obj):
        return split_lines(self.tr(obj, "prevention"))

    def get_traveler_recommendations(self, obj):
        return split_lines(self.tr(obj, "traveler_recommendations"))

    def get_symptoms(self, obj):
        return [
            {"label": s.label, "is_red_flag": s.is_red_flag}
            for s in sorted(obj.symptoms.all(), key=lambda s: (s.order, s.label))
        ]

    def get_notices(self, obj):
        notices = PublicNotice.objects.visible().filter(disease=obj).prefetch_related("countries")
        return PublicNoticeSerializer(notices, many=True, context=self.context).data


class ScreeningDiseaseSerializer(serializers.ModelSerializer):
    """Configuration du questionnaire voyageur pour une maladie sous surveillance."""

    exposures = serializers.SerializerMethodField()
    symptoms = serializers.SerializerMethodField()
    followup_days = serializers.SerializerMethodField()
    daily_checkin = serializers.SerializerMethodField()

    class Meta:
        model = Disease
        fields = ["code", "name", "slug", "exposures", "symptoms", "followup_days", "daily_checkin"]

    def get_exposures(self, obj):
        return [{"code": rf.code, "label": rf.label} for rf in obj.risk_factors.all()]

    def get_symptoms(self, obj):
        return [
            {"code": s.code, "label": s.label, "is_red_flag": s.is_red_flag}
            for s in sorted(obj.symptoms.all(), key=lambda s: (s.order, s.label))
        ]

    def get_followup_days(self, obj):
        return followup_duration_days(obj)

    def get_daily_checkin(self, obj):
        protocol = getattr(obj, "followup_protocol", None)
        return bool(protocol.daily_checkin_required) if protocol and protocol.is_active else True


# -------------------------------------------------------------------- admin


class PublicNoticeAdminSerializer(serializers.ModelSerializer):
    disease = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Disease.objects.all(),
        required=False,
        allow_null=True,
    )
    countries = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Country.objects.all(),
        many=True,
        required=False,
    )
    published_by_email = serializers.EmailField(
        source="published_by.email",
        read_only=True,
        default=None,
    )

    class Meta:
        model = PublicNotice
        fields = [
            "id",
            "uuid",
            "kind",
            "title",
            "summary",
            "body",
            "alert_level",
            "disease",
            "countries",
            "source_alert",
            "translations",
            "status",
            "valid_from",
            "valid_until",
            "published_at",
            "published_by_email",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "uuid", "status", "published_at", "created_at", "updated_at"]

    def validate(self, attrs):
        start = attrs.get("valid_from", getattr(self.instance, "valid_from", None))
        end = attrs.get("valid_until", getattr(self.instance, "valid_until", None))
        if start and end and end < start:
            raise serializers.ValidationError({"valid_until": "Fin antérieure au début."})
        return attrs
