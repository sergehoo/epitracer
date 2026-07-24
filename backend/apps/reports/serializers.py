"""Serializers DRF pour les rapports automatisés."""
from __future__ import annotations

from rest_framework import serializers

from .models import (
    AutomatedReportRecipient, AutomatedReportSchedule,
    GeneratedReport, ReportDeliveryLog,
)


# ---------------------------------------------------------------------------
# 1. AutomatedReportSchedule
# ---------------------------------------------------------------------------
class AutomatedReportScheduleSerializer(serializers.ModelSerializer):
    weekday_label = serializers.CharField(source="get_weekday_display", read_only=True)
    report_type_label = serializers.CharField(source="get_report_type_display", read_only=True)
    frequency_label = serializers.CharField(source="get_frequency_display", read_only=True)

    class Meta:
        model = AutomatedReportSchedule
        fields = [
            "id", "uuid",
            "name", "report_type", "report_type_label",
            "frequency", "frequency_label",
            "weekday", "weekday_label", "time", "timezone",
            "is_active", "include_pdf", "include_excel",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["uuid", "created_by", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# 2. AutomatedReportRecipient
# ---------------------------------------------------------------------------
class AutomatedReportRecipientSerializer(serializers.ModelSerializer):
    masked_phone = serializers.ReadOnlyField()
    preferred_channel_label = serializers.CharField(
        source="get_preferred_channel_display", read_only=True,
    )
    district_name = serializers.CharField(
        source="district.name", read_only=True, default=None,
    )

    class Meta:
        model = AutomatedReportRecipient
        fields = [
            "id", "uuid",
            "full_name", "job_title", "organization",
            "phone_number", "masked_phone", "email",
            "preferred_channel", "preferred_channel_label",
            "language", "district", "district_name",
            "allowed_report_types",
            "is_active",
            "consent_date", "consent_evidence",
            "created_by", "created_at", "updated_at",
        ]
        read_only_fields = [
            "uuid", "masked_phone", "created_by", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        # Reprendre la logique clean() du modèle pour renvoyer 400 propre au client
        instance = AutomatedReportRecipient(**{
            k: v for k, v in attrs.items()
            if k in {"full_name", "phone_number", "email", "preferred_channel",
                     "is_active", "consent_date"}
        })
        try:
            instance.clean()
        except Exception as exc:  # noqa: BLE001
            raise serializers.ValidationError(
                getattr(exc, "message_dict", str(exc))
            )
        return attrs


class AutomatedReportRecipientLightSerializer(serializers.ModelSerializer):
    """Version light pour listes — pas de PII en clair (jamais phone_number)."""
    masked_phone = serializers.ReadOnlyField()

    class Meta:
        model = AutomatedReportRecipient
        fields = [
            "id", "full_name", "organization", "preferred_channel",
            "masked_phone", "email", "is_active",
        ]


# ---------------------------------------------------------------------------
# 3. GeneratedReport
# ---------------------------------------------------------------------------
class GeneratedReportLightSerializer(serializers.ModelSerializer):
    """Version light pour liste (sans summary_data qui peut être lourd)."""
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    report_type_label = serializers.CharField(source="get_report_type_display", read_only=True)
    has_pdf = serializers.SerializerMethodField()
    has_excel = serializers.SerializerMethodField()
    delivery_count = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedReport
        fields = [
            "id", "uuid", "report_code",
            "report_type", "report_type_label",
            "period_start", "period_end",
            "status", "status_label",
            "generated_at", "duration_ms",
            "has_pdf", "has_excel",
            "delivery_count",
        ]

    def get_has_pdf(self, obj) -> bool:
        return bool(obj.pdf_file)

    def get_has_excel(self, obj) -> bool:
        return bool(obj.excel_file)

    def get_delivery_count(self, obj) -> int:
        return obj.deliveries.count()


class GeneratedReportDetailSerializer(GeneratedReportLightSerializer):
    """Version complète avec summary_data (pour vue détail)."""

    class Meta(GeneratedReportLightSerializer.Meta):
        fields = GeneratedReportLightSerializer.Meta.fields + [
            "summary_data", "error_message", "generated_by",
        ]


# ---------------------------------------------------------------------------
# 4. ReportDeliveryLog
# ---------------------------------------------------------------------------
class ReportDeliveryLogSerializer(serializers.ModelSerializer):
    """Historique des envois — jamais phone_number/email en clair.

    `destination_masked` est la seule projection visible côté API.
    """
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    channel_label = serializers.CharField(source="get_channel_display", read_only=True)
    report_code = serializers.CharField(source="report.report_code", read_only=True)
    recipient_name = serializers.CharField(source="recipient.full_name", read_only=True)
    recipient_org = serializers.CharField(source="recipient.organization", read_only=True)

    class Meta:
        model = ReportDeliveryLog
        fields = [
            "id", "uuid",
            "report", "report_code",
            "recipient", "recipient_name", "recipient_org",
            "channel", "channel_label",
            "provider",
            "destination_masked",
            "status", "status_label",
            "notification_id",
            "sent_at", "delivered_at",
            "error_message", "retry_count", "next_retry_at",
            "created_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# 5. Actions personnalisées — inputs
# ---------------------------------------------------------------------------
class GenerateReportInputSerializer(serializers.Serializer):
    """Input pour POST /weekly/generate/ — période optionnelle."""
    period_start = serializers.DateTimeField(required=False, allow_null=True)
    period_end = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        start = attrs.get("period_start")
        end = attrs.get("period_end")
        if (start and not end) or (end and not start):
            raise serializers.ValidationError(
                "period_start et period_end doivent être fournis ensemble "
                "(ou aucun des deux pour utiliser la semaine précédente auto)."
            )
        if start and end and start >= end:
            raise serializers.ValidationError(
                "period_start doit être strictement avant period_end."
            )
        return attrs


class TestSendInputSerializer(serializers.Serializer):
    """Input pour POST /recipients/{id}/test/ — canal explicite."""
    channel = serializers.ChoiceField(choices=["sms", "email"])


class RecipientImportCsvInputSerializer(serializers.Serializer):
    """Input pour POST /recipients/import-csv/."""
    csv_file = serializers.FileField()
    dry_run = serializers.BooleanField(default=False)
