"""Sérialiseurs du portail : lecture publique (contenus publiés) et gestion admin."""

from __future__ import annotations

from django.utils.translation import get_language
from rest_framework import serializers

from apps.diseases.models import (
    PUBLIC_TRANSLATABLE_FIELDS,
    Disease,
    PublicAlertLevel,
    TransmissionMode,
)
from apps.geo.models import Country
from apps.medical.screening import is_contact_exposure, risk_country_codes, screening_rules
from apps.quarantine.services import followup_duration_days

from .models import PublicNotice
from .services import localized, split_lines

TRANSMISSION_LABELS = dict(TransmissionMode.choices)
ALERT_LABELS = dict(PublicAlertLevel.choices)
# Valeurs fixes en anglais (aucun catalogue gettext n'est livré ; `?lang=en` ne les traduisait pas).
LABELS_EN = {
    "alert": {
        PublicAlertLevel.NORMAL: "Watch", PublicAlertLevel.MODERATE: "Vigilance",
        PublicAlertLevel.HIGH: "Alert", PublicAlertLevel.CRITICAL: "Health emergency",
    },
    "transmission": {
        TransmissionMode.AIRBORNE: "Airborne", TransmissionMode.DROPLET: "Droplets",
        TransmissionMode.CONTACT: "Direct/indirect contact",
        TransmissionMode.VECTOR: "Vector-borne",
        TransmissionMode.SEXUAL: "Sexual", TransmissionMode.FECAL_ORAL: "Faecal-oral",
        TransmissionMode.BLOOD: "Blood-borne", TransmissionMode.OTHER: "Other",
    },
}


class _LocalizedMixin:
    translations_attr = "public_translations"

    def _lang(self) -> str:
        request = self.context.get("request")
        lang = request.query_params.get("lang") if request else None
        return (lang or get_language() or "fr")[:2]

    def tr(self, obj, field: str):
        return localized(obj, field, self._lang(), self.translations_attr)

    def fixed_label(self, kind: str, value: str, fr_labels: dict) -> str:
        """Libellé d'une valeur fixe dans la langue demandée, français à défaut."""
        if self._lang() == "en" and value in LABELS_EN[kind]:
            return LABELS_EN[kind][value]
        return str(fr_labels.get(value, value))


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
        return self.fixed_label("alert", obj.public_alert_level, ALERT_LABELS)

    def get_transmission(self, obj):
        return [
            self.fixed_label("transmission", m, TRANSMISSION_LABELS)
            for m in obj.transmission_modes or []
        ]

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
        return self.fixed_label("alert", obj.alert_level, ALERT_LABELS)

    def get_disease(self, obj):
        d = obj.disease
        if d is None or not d.is_published:
            return None
        return {"slug": d.slug, "name": localized(d, "name", self._lang(), "public_translations")}

    def get_countries(self, obj):
        return [{"code": c.code, "name": c.name} for c in obj.countries.all()]


class PublicDiseaseDetailSerializer(PublicDiseaseListSerializer):
    transmission_details = serializers.SerializerMethodField()
    prevention = serializers.SerializerMethodField()
    traveler_recommendations = serializers.SerializerMethodField()
    symptoms = serializers.SerializerMethodField()
    notices = serializers.SerializerMethodField()
    untranslated_fields = serializers.SerializerMethodField()

    class Meta(PublicDiseaseListSerializer.Meta):
        fields = PublicDiseaseListSerializer.Meta.fields + [
            "icd11_code",
            "transmission_details",
            "prevention",
            "traveler_recommendations",
            "symptoms",
            "notices",
            "untranslated_fields",
        ]

    def _translation(self, obj) -> dict:
        tr = (obj.public_translations or {}).get(self._lang(), {})
        return tr if isinstance(tr, dict) else {}

    def get_transmission_details(self, obj):
        return self.tr(obj, "transmission_details")

    def get_prevention(self, obj):
        return split_lines(self.tr(obj, "prevention"))

    def get_traveler_recommendations(self, obj):
        return split_lines(self.tr(obj, "traveler_recommendations"))

    def get_symptoms(self, obj):
        # Traductions dans public_translations : {"en": {"symptoms": {"<code>": "Fever"}}}.
        labels = self._translation(obj).get("symptoms") if self._lang() != "fr" else None
        labels = labels if isinstance(labels, dict) else {}
        return [
            {"label": labels.get(s.code) or s.label, "is_red_flag": s.is_red_flag}
            for s in sorted(obj.symptoms.all(), key=lambda s: (s.order, s.label))
        ]

    def get_untranslated_fields(self, obj):
        """Contenus affichés en français faute de traduction dans la langue demandée."""
        if self._lang() == "fr":
            return []
        tr = self._translation(obj)
        missing = [f for f in PUBLIC_TRANSLATABLE_FIELDS if getattr(obj, f) and not tr.get(f)]
        symptom_labels = tr.get("symptoms") if isinstance(tr.get("symptoms"), dict) else {}
        if any(not symptom_labels.get(s.code) for s in obj.symptoms.all()):
            missing.append("symptoms")
        return missing

    def get_notices(self, obj):
        notices = PublicNotice.objects.visible().filter(disease=obj).prefetch_related("countries")
        return PublicNoticeSerializer(notices, many=True, context=self.context).data


class ScreeningDiseaseSerializer(serializers.ModelSerializer):
    """Questionnaire voyageur d'une maladie sous surveillance active.

    `contact_exposures` sont posées dans le tronc commun (une seule question
    « contact avec un malade »), `specific_exposures` seulement si l'itinéraire
    passe par `risk_countries` (ou toujours, selon le protocole).
    """

    contact_exposures = serializers.SerializerMethodField()
    specific_exposures = serializers.SerializerMethodField()
    ask_specific_exposures = serializers.SerializerMethodField()
    risk_countries = serializers.SerializerMethodField()
    followup_days = serializers.SerializerMethodField()
    daily_checkin = serializers.SerializerMethodField()

    class Meta:
        model = Disease
        fields = [
            "code", "name", "slug", "contact_exposures", "specific_exposures",
            "ask_specific_exposures", "risk_countries", "followup_days", "daily_checkin",
        ]

    def _exposures(self, obj, contact: bool):
        return [
            {"code": rf.code, "label": rf.label}
            for rf in obj.risk_factors.all()
            if is_contact_exposure(rf.code) == contact
        ]

    def get_contact_exposures(self, obj):
        return self._exposures(obj, contact=True)

    def get_specific_exposures(self, obj):
        return self._exposures(obj, contact=False)

    def get_ask_specific_exposures(self, obj):
        return screening_rules(obj)["ask_specific_exposures"]

    def get_risk_countries(self, obj):
        return risk_country_codes(obj)

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
