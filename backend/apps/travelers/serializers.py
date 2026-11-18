from rest_framework import serializers

from .models import CompanionLink, Traveler, TravelHistoryEntry
from .transport import entry_point_error


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
            "arrival_date", "arrival_time", "planned_departure_date", "transport_mode",
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

    def validate(self, attrs):
        arrival = attrs.get("arrival_date", getattr(self.instance, "arrival_date", None))
        departure = attrs.get(
            "planned_departure_date", getattr(self.instance, "planned_departure_date", None),
        )
        if arrival and departure and departure < arrival:
            raise serializers.ValidationError(
                {"planned_departure_date": "Le départ prévu précède la date d'arrivée."}
            )
        self._validate_entry_point(attrs)
        return attrs

    def _validate_entry_point(self, attrs):
        """Transport ↔ point d'entrée : contrôlé seulement si l'un des deux change,
        pour que les fiches anciennes restent modifiables sur leurs autres champs."""
        transport = attrs.get("transport_mode", getattr(self.instance, "transport_mode", ""))
        entry_point = attrs.get("entry_point", getattr(self.instance, "entry_point", None))
        entry_changed = "entry_point" in attrs and (
            self.instance is None or entry_point != self.instance.entry_point
        )
        transport_changed = "transport_mode" in attrs and (
            self.instance is None or transport != self.instance.transport_mode
        )
        if not (entry_changed or transport_changed):
            return
        error = entry_point_error(transport, entry_point, check_active=entry_changed)
        if error:
            raise serializers.ValidationError({"entry_point": error})


class TravelerLiteSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Traveler
        fields = ["id", "uuid", "public_id", "full_name", "current_health_status", "arrival_date"]
