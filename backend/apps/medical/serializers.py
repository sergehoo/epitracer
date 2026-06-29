"""Serializers DRF — module medical (Phase 9B).

Tous les serializers de sortie masquent les PII (téléphone, email) — la
récupération en clair passe par les endpoints dédiés qui journalisent
l'accès via DataAccessLog. Aucun champ ne renvoie de token ou de pièce
d'identité brute.
"""
from __future__ import annotations

from datetime import date

from rest_framework import serializers

from .models import (
    CaseClassification,
    CaseClassificationCode,
    DiseaseFollowupProtocol,
    FollowUpAction,
    FollowUpActionStatus,
    FollowUpActionType,
    LabAnalysis,
    LabAnalysisResult,
    LabAnalysisStatus,
    MedicalSample,
    MedicalSymptomReport,
    SampleType,
    SampleTransportStatus,
    SymptomSeverity,
    SymptomSource,
)


# ---------------------------------------------------------------------------
# Helpers PII
# ---------------------------------------------------------------------------


def _mask_phone(phone: str | None) -> str:
    """Masque un numéro de téléphone — garde l'indicatif + 4 derniers chiffres."""
    if not phone:
        return ""
    phone = str(phone)
    if len(phone) < 9:
        return phone
    return phone[:5] + "****" + phone[-4:]


def _mask_email(email: str | None) -> str:
    """Masque un email — garde l'initiale du local-part et le domaine entier."""
    if not email:
        return ""
    email = str(email)
    if "@" not in email:
        return email
    local, _, domain = email.partition("@")
    if not local:
        return email
    return f"{local[0]}***@{domain}"


def _user_full_name(user) -> str:
    if not user:
        return ""
    full = (getattr(user, "get_full_name", None) or (lambda: ""))()
    if full:
        return full
    return getattr(user, "email", "") or getattr(user, "username", "") or ""


# ---------------------------------------------------------------------------
# Protocoles, symptômes, prélèvements, analyses, classification, actions
# ---------------------------------------------------------------------------


class DiseaseFollowupProtocolSerializer(serializers.ModelSerializer):
    disease_code = serializers.CharField(source="disease.code", read_only=True)
    disease_name = serializers.CharField(source="disease.name", read_only=True)

    class Meta:
        model = DiseaseFollowupProtocol
        fields = [
            "id", "uuid",
            "disease", "disease_code", "disease_name",
            "duration_days",
            "daily_checkin_required", "daily_checkin_recommended",
            "critical_symptoms", "monitored_symptoms",
            "sample_required_rules", "lab_analysis_required_rules",
            "escalation_rules", "closure_rules",
            "notification_schedule", "field_visit_rules",
            "require_geolocation", "geolocation_alert_after_hours",
            "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "uuid", "created_at", "updated_at"]


class MedicalSymptomReportSerializer(serializers.ModelSerializer):
    source_label = serializers.CharField(source="get_source_display", read_only=True)
    severity_label = serializers.CharField(source="get_severity_display", read_only=True)
    reported_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MedicalSymptomReport
        fields = [
            "id", "uuid",
            "followup_case", "followup_day",
            "symptom_code", "symptom_label",
            "severity", "severity_label",
            "onset_date",
            "source", "source_label",
            "notes",
            "is_critical",
            "reported_by_user", "reported_by_name", "reported_by_traveler",
            "created_at",
        ]
        read_only_fields = [
            "id", "uuid", "followup_case",
            "is_critical", "reported_by_user", "reported_by_name",
            "reported_by_traveler", "created_at",
            "severity_label", "source_label",
        ]

    def get_reported_by_name(self, obj):
        return _user_full_name(obj.reported_by_user)


class MedicalSampleSerializer(serializers.ModelSerializer):
    transport_status_label = serializers.CharField(
        source="get_transport_status_display", read_only=True,
    )
    sample_type_label = serializers.CharField(
        source="get_sample_type_display", read_only=True,
    )
    collected_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MedicalSample
        fields = [
            "id", "uuid",
            "followup_case", "followup_day",
            "sample_code",
            "sample_type", "sample_type_label",
            "collected_at", "collected_by", "collected_by_name",
            "collection_location",
            "transport_conditions",
            "destination_lab",
            "transport_status", "transport_status_label",
            "transport_departed_at",
            "received_at",
            "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "uuid",
            "sample_code",  # auto-généré côté serveur
            "followup_case",
            "collected_by", "collected_by_name",
            "created_at", "updated_at",
            "sample_type_label", "transport_status_label",
        ]

    def get_collected_by_name(self, obj):
        return _user_full_name(obj.collected_by)


class LabAnalysisSerializer(serializers.ModelSerializer):
    result_label = serializers.CharField(source="get_result_display", read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    validated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = LabAnalysis
        fields = [
            "id", "uuid",
            "sample", "lab_name", "test_type",
            "status", "status_label",
            "result", "result_label",
            "received_at", "analyzed_at",
            "validated_at", "validated_by", "validated_by_name",
            "result_file",
            "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "uuid",
            "validated_at", "validated_by", "validated_by_name",
            "created_at", "updated_at",
            "result_label", "status_label",
        ]

    def get_validated_by_name(self, obj):
        return _user_full_name(obj.validated_by)


class CaseClassificationSerializer(serializers.ModelSerializer):
    classification_label = serializers.CharField(
        source="get_classification_display", read_only=True,
    )
    classified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CaseClassification
        fields = [
            "id", "uuid",
            "followup_case",
            "classification", "classification_label",
            "reason",
            "classified_by", "classified_by_name",
            "classified_at",
            "is_current",
        ]
        read_only_fields = [
            "id", "uuid", "followup_case",
            "classified_by", "classified_by_name",
            "classified_at", "is_current",
            "classification_label",
        ]

    def get_classified_by_name(self, obj):
        return _user_full_name(obj.classified_by)


class FollowUpActionSerializer(serializers.ModelSerializer):
    action_type_label = serializers.CharField(
        source="get_action_type_display", read_only=True,
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = FollowUpAction
        fields = [
            "id", "uuid",
            "followup_case", "followup_day",
            "action_type", "action_type_label",
            "title", "description",
            "status", "status_label",
            "performed_by", "performed_by_name",
            "performed_at",
            "metadata",
        ]
        read_only_fields = [
            "id", "uuid",
            "followup_case", "followup_day",
            "performed_by", "performed_by_name", "performed_at",
            "action_type_label", "status_label",
        ]

    def get_performed_by_name(self, obj):
        return _user_full_name(obj.performed_by)


# ---------------------------------------------------------------------------
# Détail d'un cas — agrégateur (lecture seule)
# ---------------------------------------------------------------------------


class FollowupCaseDetailSerializer(serializers.Serializer):
    """Serializer agrégateur : prend un QuarantineRecord et l'expose
    enrichi avec les relations medical/companion."""

    id = serializers.IntegerField()
    public_id = serializers.SerializerMethodField()

    traveler = serializers.SerializerMethodField()
    disease = serializers.SerializerMethodField()

    status = serializers.CharField()
    started_on = serializers.DateField()
    expected_end_on = serializers.DateField()
    day_index = serializers.SerializerMethodField()
    total_days = serializers.SerializerMethodField()

    current_classification = serializers.CharField(allow_blank=True)
    current_classification_label = serializers.SerializerMethodField()
    classifications = serializers.SerializerMethodField()

    assigned_district = serializers.SerializerMethodField()
    assigned_agent = serializers.SerializerMethodField()
    assigned_team = serializers.CharField(allow_blank=True)

    last_checkin = serializers.SerializerMethodField()
    last_location_ping = serializers.SerializerMethodField()
    latest_lab_result = serializers.SerializerMethodField()

    days_completed = serializers.SerializerMethodField()
    days_missed = serializers.SerializerMethodField()
    samples_count = serializers.SerializerMethodField()
    symptoms_count = serializers.SerializerMethodField()
    critical_symptoms_count = serializers.SerializerMethodField()
    alerts_count = serializers.SerializerMethodField()

    kpis = serializers.SerializerMethodField()
    closure_reason = serializers.CharField(allow_blank=True)
    geolocation_alert_raised_at = serializers.DateTimeField(allow_null=True)
    follow_up_protocol = serializers.SerializerMethodField()

    # -- helpers --

    def get_public_id(self, case):
        return getattr(case.traveler, "public_id", "")

    def get_traveler(self, case):
        t = case.traveler
        ep = getattr(t, "entry_point", None)
        return {
            "id": t.id,
            "public_id": t.public_id,
            "full_name": t.full_name,
            "phone": _mask_phone(t.phone_mobile),
            "email": _mask_email(t.email),
            "nationality": getattr(getattr(t, "nationality", None), "name", "") or "",
            "entry_point": getattr(ep, "name", "") if ep else "",
        }

    def get_disease(self, case):
        d = case.disease
        return {
            "code": d.code,
            "name": d.name,
            "color": getattr(d, "color", "#dc2626"),
        }

    def get_day_index(self, case):
        if not case.started_on:
            return 0
        delta = (date.today() - case.started_on).days
        return max(0, delta)

    def get_total_days(self, case):
        if case.started_on and case.expected_end_on:
            return max(0, (case.expected_end_on - case.started_on).days)
        return 0

    def get_current_classification_label(self, case):
        code = case.current_classification or ""
        if not code:
            return ""
        return dict(CaseClassificationCode.choices).get(code, code)

    def get_classifications(self, case):
        qs = case.classifications.all().order_by("-classified_at")
        return CaseClassificationSerializer(qs, many=True).data

    def get_assigned_district(self, case):
        d = case.assigned_district
        if not d:
            return None
        return {"id": d.id, "name": getattr(d, "name", "") or str(d)}

    def get_assigned_agent(self, case):
        a = case.assigned_agent
        if not a:
            return None
        return {
            "id": a.id,
            "full_name": _user_full_name(a),
            "email": getattr(a, "email", "") or "",
        }

    def get_last_checkin(self, case):
        check = case.daily_checks.order_by("-check_date", "-day_index").first()
        if not check:
            return None
        return {
            "id": check.id,
            "day_index": check.day_index,
            "check_date": check.check_date,
            "status": check.status,
            "has_symptoms": check.has_symptoms,
            "temperature_celsius": (
                str(check.temperature_celsius)
                if check.temperature_celsius is not None else None
            ),
            "alert_raised": check.alert_raised,
        }

    def get_last_location_ping(self, case):
        try:
            from apps.companion.models import TravelerLocationPing
        except Exception:  # pragma: no cover
            return None
        ping = (
            TravelerLocationPing.objects
            .filter(traveler=case.traveler)
            .order_by("-captured_at")
            .first()
        )
        if not ping:
            return None
        lat = None
        lon = None
        try:
            if ping.location is not None:
                lat = ping.location.y
                lon = ping.location.x
        except Exception:  # pragma: no cover
            pass
        return {"lat": lat, "lon": lon, "captured_at": ping.captured_at}

    def get_latest_lab_result(self, case):
        analysis = (
            LabAnalysis.objects
            .filter(sample__followup_case=case)
            .exclude(result="")
            .order_by("-created_at")
            .first()
        )
        if not analysis:
            return None
        return {
            "result": analysis.result,
            "result_label": analysis.get_result_display(),
            "status": analysis.status,
            "validated_at": analysis.validated_at,
            "test_type": analysis.test_type,
            "lab_name": analysis.lab_name,
        }

    def get_days_completed(self, case):
        return case.daily_checks.filter(status="completed").count()

    def get_days_missed(self, case):
        return case.daily_checks.filter(status="missed").count()

    def get_samples_count(self, case):
        return case.samples.count()

    def get_symptoms_count(self, case):
        return case.symptom_reports.count()

    def get_critical_symptoms_count(self, case):
        return case.symptom_reports.filter(is_critical=True).count()

    def get_alerts_count(self, case):
        try:
            from django.contrib.contenttypes.models import ContentType
            from apps.surveillance.models import HealthAlert
            ct = ContentType.objects.get_for_model(case.__class__)
            return HealthAlert.objects.filter(
                target_ct=ct, target_id=str(case.pk),
            ).count()
        except Exception:  # pragma: no cover
            return 0

    def get_kpis(self, case):
        return {
            "days_completed": self.get_days_completed(case),
            "days_missed": self.get_days_missed(case),
            "samples_count": self.get_samples_count(case),
            "symptoms_count": self.get_symptoms_count(case),
            "critical_symptoms_count": self.get_critical_symptoms_count(case),
            "alerts_count": self.get_alerts_count(case),
        }

    def get_follow_up_protocol(self, case):
        protocol = getattr(case.disease, "followup_protocol", None)
        if not protocol:
            return None
        return {
            "duration_days": protocol.duration_days,
            "daily_checkin_required": protocol.daily_checkin_required,
            "critical_symptoms": protocol.critical_symptoms or [],
            "require_geolocation": protocol.require_geolocation,
        }


# ---------------------------------------------------------------------------
# Timeline jour par jour
# ---------------------------------------------------------------------------


class FollowupTimelineDaySerializer(serializers.ModelSerializer):
    symptoms_count = serializers.SerializerMethodField()
    sample_requested_flag = serializers.SerializerMethodField()
    notification_sent_flag = serializers.BooleanField(
        source="notification_sent", read_only=True,
    )
    actions = serializers.SerializerMethodField()
    agent_responsible_name = serializers.SerializerMethodField()

    class Meta:
        # Lazy import — DailyCheck is in apps.quarantine
        from apps.quarantine.models import DailyCheck as _DC
        model = _DC
        fields = [
            "id",
            "day_index",
            "check_date",
            "status",
            "has_symptoms",
            "temperature_celsius",
            "decision",
            "agent_responsible", "agent_responsible_name",
            "location_shared",
            "alert_raised",
            "notes",
            "symptoms_count",
            "sample_requested_flag",
            "notification_sent_flag",
            "actions",
        ]
        read_only_fields = fields

    def get_symptoms_count(self, obj):
        return MedicalSymptomReport.objects.filter(followup_day=obj).count()

    def get_sample_requested_flag(self, obj):
        return MedicalSample.objects.filter(followup_day=obj).exists()

    def get_agent_responsible_name(self, obj):
        return _user_full_name(getattr(obj, "agent_responsible", None))

    def get_actions(self, obj):
        actions = FollowUpAction.objects.filter(followup_day=obj).order_by("-performed_at")[:10]
        return [
            {
                "id": a.id,
                "action_type": a.action_type,
                "action_type_label": a.get_action_type_display(),
                "title": a.title,
                "performed_at": a.performed_at,
                "performed_by_name": _user_full_name(a.performed_by),
            }
            for a in actions
        ]


# ---------------------------------------------------------------------------
# Inputs (POST/PATCH) — write-only
# ---------------------------------------------------------------------------


class FollowupCreateActionSerializer(serializers.Serializer):
    action_type = serializers.ChoiceField(choices=FollowUpActionType.choices)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(allow_blank=True, required=False, default="")
    status = serializers.ChoiceField(
        choices=FollowUpActionStatus.choices,
        required=False,
        default=FollowUpActionStatus.COMPLETED,
    )
    metadata = serializers.JSONField(required=False, default=dict)


_CLOSURE_REASON_CHOICES = [
    ("auto_completed", "Suivi terminé automatiquement"),
    ("escalated", "Escaladé"),
    ("manual_close", "Clôture manuelle"),
    ("lost_to_followup", "Perdu de vue"),
]
_FINAL_STATUS_CHOICES = [
    ("completed", "Terminé"),
    ("cancelled", "Annulé"),
]


class FollowupCloseSerializer(serializers.Serializer):
    closure_reason = serializers.ChoiceField(
        choices=_CLOSURE_REASON_CHOICES, required=True,
    )
    final_status = serializers.ChoiceField(
        choices=_FINAL_STATUS_CHOICES, required=False, default="completed",
    )
    notes = serializers.CharField(allow_blank=True, required=False, default="")


class FollowupClassifySerializer(serializers.Serializer):
    classification = serializers.ChoiceField(
        choices=CaseClassificationCode.choices, required=True,
    )
    reason = serializers.CharField(
        allow_blank=True, required=False, default="", max_length=500,
    )


class FollowupAssignAgentSerializer(serializers.Serializer):
    assigned_agent_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_district_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_team = serializers.CharField(
        allow_blank=True, required=False, default="", max_length=120,
    )


_NOTIFY_CHANNEL_CHOICES = [
    ("sms", "SMS"),
    ("whatsapp", "WhatsApp"),
    ("email", "Email"),
    ("push", "Push"),
]


class FollowupNotifySerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=_NOTIFY_CHANNEL_CHOICES)
    recipient = serializers.CharField(required=False, allow_blank=True, default="")
    subject = serializers.CharField(allow_blank=True, required=False, default="")
    body = serializers.CharField(max_length=4000)
    template_code = serializers.CharField(allow_blank=True, required=False, default="")

    def validate(self, attrs):
        channel = attrs.get("channel")
        recipient = (attrs.get("recipient") or "").strip()
        if channel in ("sms", "whatsapp", "email") and not recipient:
            raise serializers.ValidationError(
                {"recipient": "Recipient requis pour ce canal."}
            )
        return attrs


class FollowupRequestSampleSerializer(serializers.Serializer):
    sample_type = serializers.ChoiceField(
        choices=SampleType.choices, required=False, default=SampleType.BLOOD,
    )
    destination_lab = serializers.CharField(
        allow_blank=True, required=False, default="", max_length=200,
    )
    collection_location = serializers.CharField(
        allow_blank=True, required=False, default="", max_length=200,
    )
    transport_conditions = serializers.CharField(
        allow_blank=True, required=False, default="",
    )
    notes = serializers.CharField(allow_blank=True, required=False, default="")
    followup_day_id = serializers.IntegerField(required=False, allow_null=True)


class FollowupLabAnalysisCreateSerializer(serializers.Serializer):
    sample_id = serializers.IntegerField(required=True)
    lab_name = serializers.CharField(max_length=200)
    test_type = serializers.CharField(max_length=80)
    result = serializers.ChoiceField(
        choices=LabAnalysisResult.choices, required=False,
        default=LabAnalysisResult.EMPTY,
    )
    status = serializers.ChoiceField(
        choices=LabAnalysisStatus.choices, required=False,
        default=LabAnalysisStatus.RESULT_AVAILABLE,
    )
    notes = serializers.CharField(allow_blank=True, required=False, default="")


# ---------------------------------------------------------------------------
# Endpoints publics (PWA voyageur) — NO PII output
# ---------------------------------------------------------------------------


_PUBLIC_SAFE_CLASSIFICATIONS = {
    CaseClassificationCode.NOT_SUSPECT: "Non suspect",
    CaseClassificationCode.UNDER_SURVEILLANCE: "Sous surveillance",
    CaseClassificationCode.EXCLUDED: "Suivi terminé",
    CaseClassificationCode.RECOVERED: "Rétabli",
    CaseClassificationCode.CLOSED: "Clôturé",
}


def _public_classification_label(code: str | None) -> str:
    """Retourne un libellé safe pour le voyageur — masque les cas
    suspect/probable/confirmed pour ne pas révéler de diagnostic via API publique.
    """
    if not code:
        return ""
    if code in (
        CaseClassificationCode.SUSPECT,
        CaseClassificationCode.PROBABLE,
        CaseClassificationCode.CONFIRMED,
    ):
        return "Sous surveillance médicale"
    return _PUBLIC_SAFE_CLASSIFICATIONS.get(code, "Sous surveillance")


class PublicFollowupStatusSerializer(serializers.Serializer):
    """Sortie publique — aucun PII (téléphone, email, document).

    Conçu pour la PWA voyageur (/api/v1/public/followup/status/).
    """

    public_id = serializers.CharField()
    disease_code = serializers.CharField()
    disease_name = serializers.CharField()
    status = serializers.CharField()
    started_on = serializers.DateField(allow_null=True)
    expected_end_on = serializers.DateField(allow_null=True)
    day_index = serializers.IntegerField()
    total_days = serializers.IntegerField()
    current_classification_label = serializers.CharField()
    last_checkin_date = serializers.DateField(allow_null=True)
    last_checkin_feeling = serializers.CharField(allow_blank=True)
    days_completed = serializers.IntegerField()
    days_remaining = serializers.IntegerField()
    assistance_phones = serializers.DictField(child=serializers.CharField())


class PublicSymptomReportSerializer(serializers.Serializer):
    public_id = serializers.CharField(required=True, max_length=24)
    symptom_code = serializers.CharField(max_length=40)
    symptom_label = serializers.CharField(max_length=120)
    severity = serializers.ChoiceField(
        choices=SymptomSeverity.choices, required=False, default=SymptomSeverity.MILD,
    )
    onset_date = serializers.DateField(required=False, default=date.today)
    notes = serializers.CharField(allow_blank=True, required=False, default="")


class PublicAssistanceRequestSerializer(serializers.Serializer):
    public_id = serializers.CharField(required=True, max_length=24)
    reason = serializers.CharField(max_length=500)
    is_emergency = serializers.BooleanField(required=False, default=False)
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)
