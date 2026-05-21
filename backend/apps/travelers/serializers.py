from rest_framework import serializers

from .models import CompanionLink, Traveler, TravelHistoryEntry


class TravelHistoryEntrySerializer(serializers.ModelSerializer):
    country_code = serializers.CharField(source="country.code", read_only=True)

    class Meta:
        model = TravelHistoryEntry
        fields = [
            "id", "role", "country", "country_code", "city",
            "residence_address", "hotel", "room_number",
            "arrival_date", "departure_date",
            "duration_days", "duration_text", "notes",
        ]


class CompanionLinkSerializer(serializers.ModelSerializer):
    companion_public_id = serializers.CharField(source="companion.public_id", read_only=True)

    class Meta:
        model = CompanionLink
        fields = ["id", "traveler", "companion", "companion_public_id", "relationship"]


class TravelerSerializer(serializers.ModelSerializer):
    travel_history = TravelHistoryEntrySerializer(many=True, read_only=True)
    companions = CompanionLinkSerializer(many=True, read_only=True)
    entry_point_name = serializers.CharField(source="entry_point.name", read_only=True)
    nationality_code = serializers.CharField(source="nationality.code", read_only=True)

    class Meta:
        model = Traveler
        fields = [
            "id", "uuid", "public_id",
            # Section 1 — voyage
            "arrival_date", "arrival_time", "transport_mode",
            "flight_or_voyage_number", "seat_number",
            "entry_point", "entry_point_name",
            # Section 2 — identité
            "last_name", "first_name", "middle_name",
            "age", "age_unit", "date_of_birth", "gender",
            "profession",
            "id_document_type", "id_document_number", "id_document_country",
            "nationality", "nationality_code",
            "phone_mobile", "email", "postal_address",
            "passport_document", "passport_uploaded_at",
            # Section 4 — confinement CI
            "confinement_city", "confinement_commune", "confinement_neighborhood",
            "confinement_street_number", "confinement_lot",
            "confinement_hotel", "confinement_room_number",
            "emergency_phone_ci", "confinement_address",
            # Statut
            "current_health_status",
            # Consentement / signature
            "consented_data_processing", "signed_at", "signed_place",
            # Sous-objets
            "travel_history", "companions",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "uuid", "public_id", "confinement_address", "created_at", "updated_at"]


class TravelerLiteSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Traveler
        fields = ["id", "uuid", "public_id", "full_name", "current_health_status", "arrival_date"]
