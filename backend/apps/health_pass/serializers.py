from rest_framework import serializers

from .models import HealthPass, PassBlacklistEntry, PassVerificationLog


class HealthPassSerializer(serializers.ModelSerializer):
    traveler_public_id = serializers.CharField(source="traveler.public_id", read_only=True)
    disease_code = serializers.CharField(source="disease.code", read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    qr_url = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = HealthPass
        fields = [
            "id", "uuid", "pass_number",
            "traveler", "traveler_public_id",
            "disease", "disease_code", "investigation_ref",
            "status", "risk_level", "risk_score",
            "issued_at", "expires_at", "is_valid",
            "payload", "signature_b64", "signing_kid",
            "revoked_at", "revocation_reason",
            "qr_url", "pdf_url",
        ]

    def get_qr_url(self, obj):
        if not obj.qr_image:
            return None
        url = obj.qr_image.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url

    def get_pdf_url(self, obj):
        if not obj.pdf_file:
            return None
        url = obj.pdf_file.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class HealthPassIssueSerializer(serializers.Serializer):
    traveler = serializers.IntegerField()
    disease_code = serializers.CharField()
    risk_level = serializers.CharField(required=False, default="low")
    risk_score = serializers.IntegerField(required=False, default=0)
    investigation_ref = serializers.CharField(required=False, allow_blank=True, default="")
    ttl_days = serializers.IntegerField(required=False)


class QRVerifyRequestSerializer(serializers.Serializer):
    token = serializers.CharField()
    online = serializers.BooleanField(required=False, default=True)
    entry_point = serializers.IntegerField(required=False)


class PassBlacklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = PassBlacklistEntry
        fields = ["id", "pass_number", "reason", "added_by", "created_at"]
        read_only_fields = ["added_by"]


class PassVerificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PassVerificationLog
        fields = [
            "id", "pass_number", "verified_at", "is_valid",
            "reason", "entry_point", "verified_by", "metadata",
        ]
