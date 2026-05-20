from rest_framework import serializers

from apps.travelers.serializers import TravelerSerializer

from .models import (
    EbolaDeclaration,
    EbolaExposureAssessment,
    EbolaInvestigation,
    EbolaSymptomReport,
)


class EbolaExposureSerializer(serializers.ModelSerializer):
    positive_answers_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = EbolaExposureAssessment
        fields = [
            "id",
            "visited_ebola_zone", "visited_ebola_zone_details",
            "contact_with_case",
            "attended_funeral_or_touched_corpse",
            "visited_ebola_healthcare_facility",
            "raw_exposure_score", "positive_answers_count",
        ]
        read_only_fields = ["raw_exposure_score", "positive_answers_count"]


class EbolaSymptomReportSerializer(serializers.ModelSerializer):
    has_red_flag = serializers.BooleanField(read_only=True)
    has_high_fever = serializers.BooleanField(read_only=True)
    positive_symptoms_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = EbolaSymptomReport
        fields = [
            "id", "investigation",
            "reported_at", "temperature_celsius",
            "fever", "intense_fatigue", "muscle_joint_pain", "severe_headache",
            "sore_throat_or_abdominal", "diarrhea_nausea_vomiting", "unexplained_bleeding",
            "other_symptoms", "notes", "reported_by",
            "has_red_flag", "has_high_fever", "positive_symptoms_count",
        ]
        read_only_fields = ["reported_by"]


class EbolaDeclarationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EbolaDeclaration
        fields = [
            "id", "investigation", "declared_at", "declarant_full_name", "signed_place",
            "truthful_declaration",
            "consent_data_processing", "consent_health_followup",
            "consent_quarantine_if_needed",
            "signature", "signature_hash", "extra",
        ]


class EbolaInvestigationSerializer(serializers.ModelSerializer):
    traveler_detail = TravelerSerializer(source="traveler", read_only=True)
    exposure = EbolaExposureSerializer(read_only=True)
    declaration = EbolaDeclarationSerializer(read_only=True)
    last_symptoms = serializers.SerializerMethodField()
    entry_point_name = serializers.CharField(source="entry_point.name", read_only=True)
    investigator_name = serializers.CharField(source="investigator.display_name", read_only=True)

    class Meta:
        model = EbolaInvestigation
        fields = [
            "id", "uuid", "case_number",
            "traveler", "traveler_detail",
            "submission", "investigator", "investigator_name",
            "entry_point", "entry_point_name",
            "status", "risk_level", "risk_score",
            "surveillance_start", "surveillance_end",
            "notes", "exposure", "declaration", "last_symptoms",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "uuid", "case_number", "risk_level", "risk_score",
            "surveillance_start", "surveillance_end", "created_at", "updated_at",
        ]

    def get_last_symptoms(self, obj):
        report = obj.symptom_reports.order_by("-reported_at").first()
        return EbolaSymptomReportSerializer(report).data if report else None


class EbolaInvestigationCreateSerializer(serializers.ModelSerializer):
    """Création d'une enquête depuis l'admin (agents santé)."""

    exposure = EbolaExposureSerializer(required=False)
    symptoms = EbolaSymptomReportSerializer(required=False, write_only=True)
    declaration = EbolaDeclarationSerializer(required=False)

    class Meta:
        model = EbolaInvestigation
        fields = [
            "traveler", "entry_point", "status", "notes",
            "exposure", "symptoms", "declaration",
        ]

    def create(self, validated):
        exposure = validated.pop("exposure", None)
        symptoms = validated.pop("symptoms", None)
        declaration = validated.pop("declaration", None)
        request = self.context.get("request")
        investigation = EbolaInvestigation.objects.create(
            investigator=request.user if request and request.user.is_authenticated else None,
            **validated,
        )
        if exposure:
            EbolaExposureAssessment.objects.create(investigation=investigation, **exposure)
        if symptoms:
            EbolaSymptomReport.objects.create(investigation=investigation, **symptoms)
        if declaration:
            EbolaDeclaration.objects.create(investigation=investigation, **declaration)
        return investigation


# ============================================================================
# Serializer PUBLIC : auto-enregistrement du voyageur depuis le portail
# ============================================================================
class TravelHistoryItemPublicSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["origin", "transit", "visited"])
    country_code = serializers.CharField(max_length=3)
    city = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    residence_address = serializers.CharField(max_length=300, required=False, allow_blank=True, default="")
    hotel = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    room_number = serializers.CharField(max_length=40, required=False, allow_blank=True, default="")
    arrival_date = serializers.DateField(required=False, allow_null=True)
    departure_date = serializers.DateField(required=False, allow_null=True)
    duration_text = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")


class PublicTravelerSubmissionSerializer(serializers.Serializer):
    """Soumission publique d'un voyageur depuis le portail web (sans auth).

    Structure stricte alignée sur la fiche INHP officielle :
    voyage / identite / historique / confinement / exposure / symptoms / declaration.
    """

    # --- Section 1 : voyage ---
    voyage = serializers.DictField()
    # --- Section 2 : identite ---
    identite = serializers.DictField()
    # --- Section 3 : historique ---
    historique = serializers.ListField(
        child=TravelHistoryItemPublicSerializer(), required=False, default=list,
    )
    # --- Section 4 : confinement ---
    confinement = serializers.DictField()
    # --- Section 5 : évaluation risque ---
    exposure = serializers.DictField()
    # --- Section 6 : symptômes ---
    symptoms = serializers.DictField()
    # --- Section 7 : déclaration ---
    declaration = serializers.DictField()
