from rest_framework import serializers

from .models import Country, EntryPoint, HealthZone


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "uuid", "code", "code3", "name", "name_local", "region", "risk_level", "risk_for_diseases"]


class EntryPointSerializer(serializers.ModelSerializer):
    country_code = serializers.CharField(source="country.code", read_only=True)
    country_name = serializers.CharField(source="country.name", read_only=True)
    latitude = serializers.SerializerMethodField()
    longitude = serializers.SerializerMethodField()

    class Meta:
        model = EntryPoint
        fields = [
            "id", "uuid", "code", "name", "type", "iata_code", "icao_code",
            "country", "country_code", "country_name", "region", "city", "address",
            "latitude", "longitude", "is_active", "notes",
        ]

    def get_latitude(self, obj):
        return obj.location.y if obj.location else None

    def get_longitude(self, obj):
        return obj.location.x if obj.location else None


class HealthZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthZone
        fields = ["id", "uuid", "code", "name", "level", "parent", "risk_level", "population"]
