from rest_framework import serializers


class VisitTrackSerializer(serializers.Serializer):
    """Payload envoyé par le front à chaque page-view (public)."""

    session_id = serializers.CharField(max_length=64)
    path = serializers.CharField(max_length=400)
    portal = serializers.ChoiceField(choices=["public", "admin", "api"], default="public")
    referrer = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    language = serializers.CharField(max_length=12, required=False, allow_blank=True, default="")
    timezone = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    country_code = serializers.CharField(max_length=2, required=False, allow_blank=True, default="")
