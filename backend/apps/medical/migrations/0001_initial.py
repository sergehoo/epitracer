"""Migration initiale pour l'app `medical` — Phase 9A.

Crée 6 tables :
  - medical_diseasefollowupprotocol
  - medical_medicalsymptomreport
  - medical_medicalsample
  - medical_labanalysis
  - medical_caseclassification
  - medical_followupaction
"""
import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("diseases", "0001_initial"),
        ("quarantine", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------
        # DiseaseFollowupProtocol
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="DiseaseFollowupProtocol",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="mis à jour le")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("duration_days", models.PositiveSmallIntegerField(default=21, verbose_name="Durée du suivi (jours)")),
                ("daily_checkin_required", models.BooleanField(default=True, verbose_name="Check-in quotidien obligatoire")),
                ("daily_checkin_recommended", models.BooleanField(default=False, verbose_name="Check-in quotidien recommandé")),
                ("critical_symptoms", models.JSONField(
                    blank=True, default=list,
                    help_text="Codes machine qui déclenchent une escalade immédiate.",
                    verbose_name="Symptômes critiques",
                )),
                ("monitored_symptoms", models.JSONField(blank=True, default=list, verbose_name="Symptômes surveillés")),
                ("sample_required_rules", models.JSONField(blank=True, default=dict, verbose_name="Règles prélèvement")),
                ("lab_analysis_required_rules", models.JSONField(blank=True, default=dict, verbose_name="Règles analyse labo")),
                ("escalation_rules", models.JSONField(blank=True, default=dict, verbose_name="Règles d'escalade")),
                ("closure_rules", models.JSONField(blank=True, default=dict, verbose_name="Règles de clôture")),
                ("notification_schedule", models.JSONField(blank=True, default=dict, verbose_name="Planning de notifications")),
                ("field_visit_rules", models.JSONField(blank=True, default=dict, verbose_name="Règles de visite terrain")),
                ("require_geolocation", models.BooleanField(default=True, verbose_name="Géolocalisation requise")),
                ("geolocation_alert_after_hours", models.PositiveSmallIntegerField(default=24, verbose_name="Alerte géoloc après (heures)")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Actif")),
                ("disease", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="followup_protocol",
                    to="diseases.disease",
                    verbose_name="Maladie",
                )),
            ],
            options={
                "verbose_name": "Protocole de suivi",
                "verbose_name_plural": "Protocoles de suivi",
                "ordering": ["-created_at"],
                "abstract": False,
            },
        ),

        # ------------------------------------------------------------------
        # MedicalSymptomReport
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="MedicalSymptomReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="mis à jour le")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("symptom_code", models.CharField(db_index=True, max_length=40, verbose_name="Code symptôme")),
                ("symptom_label", models.CharField(max_length=120, verbose_name="Libellé")),
                ("severity", models.CharField(
                    choices=[("mild", "Légère"), ("moderate", "Modérée"), ("severe", "Sévère"), ("critical", "Critique")],
                    db_index=True, default="mild", max_length=20, verbose_name="Sévérité",
                )),
                ("onset_date", models.DateField(db_index=True, verbose_name="Date d'apparition")),
                ("reported_by_traveler", models.BooleanField(default=False, verbose_name="Déclaré par le voyageur")),
                ("source", models.CharField(
                    choices=[("checkin", "Check-in"), ("visit", "Visite terrain"), ("call", "Appel"), ("admin", "Saisie admin")],
                    db_index=True, default="checkin", max_length=20, verbose_name="Source",
                )),
                ("notes", models.TextField(blank=True, verbose_name="Notes")),
                ("is_critical", models.BooleanField(
                    db_index=True, default=False,
                    help_text="True si symptom_code ∈ protocol.critical_symptoms.",
                    verbose_name="Critique",
                )),
                ("followup_case", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="symptom_reports", to="quarantine.quarantinerecord",
                    verbose_name="Cas de suivi",
                )),
                ("followup_day", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="symptom_reports", to="quarantine.dailycheck",
                    verbose_name="Jour de suivi",
                )),
                ("reported_by_user", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="symptom_reports_recorded", to=settings.AUTH_USER_MODEL,
                    verbose_name="Saisi par",
                )),
            ],
            options={
                "verbose_name": "Signalement de symptôme",
                "verbose_name_plural": "Signalements de symptômes",
                "ordering": ["-onset_date", "-created_at"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="medicalsymptomreport",
            index=models.Index(fields=["followup_case", "-onset_date"], name="medical_msr_case_onset_idx"),
        ),
        migrations.AddIndex(
            model_name="medicalsymptomreport",
            index=models.Index(fields=["is_critical", "-created_at"], name="medical_msr_critical_idx"),
        ),

        # ------------------------------------------------------------------
        # MedicalSample
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="MedicalSample",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="mis à jour le")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("sample_code", models.CharField(db_index=True, max_length=40, unique=True, verbose_name="Code prélèvement")),
                ("sample_type", models.CharField(
                    choices=[("blood", "Sang"), ("saliva", "Salive"), ("nasopharyngeal", "Naso-pharyngé"),
                             ("urine", "Urine"), ("stool", "Selles"), ("other", "Autre")],
                    default="blood", max_length=20, verbose_name="Type",
                )),
                ("collected_at", models.DateTimeField(blank=True, null=True, verbose_name="Prélevé le")),
                ("collection_location", models.CharField(blank=True, max_length=200, verbose_name="Lieu de prélèvement")),
                ("transport_conditions", models.TextField(blank=True, verbose_name="Conditions de transport")),
                ("destination_lab", models.CharField(blank=True, max_length=200, verbose_name="Laboratoire destinataire")),
                ("transport_status", models.CharField(
                    choices=[
                        ("requested", "Demandé"), ("scheduled", "Programmé"),
                        ("collected", "Effectué"), ("in_transit", "En transit"),
                        ("received", "Reçu labo"), ("rejected", "Rejeté"),
                        ("cancelled", "Annulé"),
                    ],
                    db_index=True, default="requested", max_length=20, verbose_name="Statut transport",
                )),
                ("transport_departed_at", models.DateTimeField(blank=True, null=True, verbose_name="Départ transport")),
                ("received_at", models.DateTimeField(blank=True, null=True, verbose_name="Reçu au labo")),
                ("notes", models.TextField(blank=True, verbose_name="Notes")),
                ("collected_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="samples_collected", to=settings.AUTH_USER_MODEL,
                    verbose_name="Préleveur",
                )),
                ("followup_case", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="samples", to="quarantine.quarantinerecord",
                    verbose_name="Cas de suivi",
                )),
                ("followup_day", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="samples", to="quarantine.dailycheck",
                    verbose_name="Jour de suivi",
                )),
            ],
            options={
                "verbose_name": "Prélèvement médical",
                "verbose_name_plural": "Prélèvements médicaux",
                "ordering": ["-created_at"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="medicalsample",
            index=models.Index(fields=["followup_case", "-created_at"], name="medical_sample_case_idx"),
        ),
        migrations.AddIndex(
            model_name="medicalsample",
            index=models.Index(fields=["transport_status", "-created_at"], name="medical_sample_status_idx"),
        ),

        # ------------------------------------------------------------------
        # LabAnalysis
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="LabAnalysis",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="mis à jour le")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("lab_name", models.CharField(max_length=200, verbose_name="Laboratoire")),
                ("test_type", models.CharField(max_length=80, verbose_name="Type d'analyse")),
                ("status", models.CharField(
                    choices=[
                        ("pending", "En attente"), ("received", "Reçu"),
                        ("in_analysis", "En analyse"), ("result_available", "Résultat disponible"),
                        ("validated", "Validé"), ("communicated", "Communiqué"),
                        ("rejected", "Rejeté"),
                    ],
                    db_index=True, default="pending", max_length=24, verbose_name="Statut",
                )),
                ("result", models.CharField(
                    blank=True,
                    choices=[
                        ("", "—"), ("negative", "Négatif"), ("positive", "Positif"),
                        ("indeterminate", "Indéterminé"), ("retest", "À refaire"),
                    ],
                    db_index=True, default="", max_length=20, verbose_name="Résultat",
                )),
                ("received_at", models.DateTimeField(blank=True, null=True, verbose_name="Reçu le")),
                ("analyzed_at", models.DateTimeField(blank=True, null=True, verbose_name="Analysé le")),
                ("validated_at", models.DateTimeField(blank=True, null=True, verbose_name="Validé le")),
                ("result_file", models.FileField(blank=True, null=True, upload_to="lab/", verbose_name="Fichier résultat")),
                ("notes", models.TextField(blank=True, verbose_name="Notes")),
                ("sample", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="analyses", to="medical.medicalsample",
                    verbose_name="Prélèvement",
                )),
                ("validated_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="lab_results_validated", to=settings.AUTH_USER_MODEL,
                    verbose_name="Validé par",
                )),
            ],
            options={
                "verbose_name": "Analyse de laboratoire",
                "verbose_name_plural": "Analyses de laboratoire",
                "ordering": ["-created_at"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="labanalysis",
            index=models.Index(fields=["sample", "-created_at"], name="medical_lab_sample_idx"),
        ),
        migrations.AddIndex(
            model_name="labanalysis",
            index=models.Index(fields=["status", "-created_at"], name="medical_lab_status_idx"),
        ),

        # ------------------------------------------------------------------
        # CaseClassification
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="CaseClassification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="mis à jour le")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("classification", models.CharField(
                    choices=[
                        ("not_suspect", "Non suspect"), ("under_surveillance", "Sous surveillance"),
                        ("suspect", "Cas suspect"), ("probable", "Cas probable"),
                        ("confirmed", "Cas confirmé"), ("excluded", "Cas exclu"),
                        ("recovered", "Rétabli"), ("closed", "Clôturé"),
                    ],
                    db_index=True, max_length=30, verbose_name="Classification",
                )),
                ("reason", models.TextField(blank=True, verbose_name="Motif")),
                ("classified_at", models.DateTimeField(auto_now_add=True, verbose_name="Classé le")),
                ("is_current", models.BooleanField(db_index=True, default=True, verbose_name="Classification active")),
                ("classified_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="case_classifications", to=settings.AUTH_USER_MODEL,
                    verbose_name="Classé par",
                )),
                ("followup_case", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="classifications", to="quarantine.quarantinerecord",
                    verbose_name="Cas de suivi",
                )),
            ],
            options={
                "verbose_name": "Classification de cas",
                "verbose_name_plural": "Classifications de cas",
                "ordering": ["-classified_at"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="caseclassification",
            index=models.Index(fields=["followup_case", "is_current"], name="medical_cc_case_current_idx"),
        ),
        migrations.AddIndex(
            model_name="caseclassification",
            index=models.Index(fields=["classification", "-classified_at"], name="medical_cc_class_idx"),
        ),

        # ------------------------------------------------------------------
        # FollowUpAction
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="FollowUpAction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="mis à jour le")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("action_type", models.CharField(
                    choices=[
                        ("contacted", "Contacté"), ("notification_sent", "Notification envoyée"),
                        ("call_scheduled", "Appel programmé"), ("visit_scheduled", "Visite programmée"),
                        ("symptom_declared", "Symptôme déclaré"), ("sample_requested", "Prélèvement demandé"),
                        ("sample_collected", "Prélèvement effectué"), ("sent_to_lab", "Envoyé au labo"),
                        ("lab_result_added", "Résultat ajouté"), ("alert_created", "Alerte créée"),
                        ("escalated", "Escaladé"), ("day_closed", "Journée clôturée"),
                        ("case_classified", "Classification mise à jour"),
                        ("medical_orientation", "Orientation médicale"),
                        ("followup_closed", "Suivi clôturé"),
                    ],
                    db_index=True, max_length=40, verbose_name="Type d'action",
                )),
                ("title", models.CharField(max_length=200, verbose_name="Titre")),
                ("description", models.TextField(blank=True, verbose_name="Description")),
                ("performed_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Effectué le")),
                ("status", models.CharField(
                    choices=[
                        ("planned", "Planifiée"), ("in_progress", "En cours"),
                        ("completed", "Effectuée"), ("cancelled", "Annulée"),
                    ],
                    db_index=True, default="completed", max_length=20, verbose_name="Statut",
                )),
                ("metadata", models.JSONField(blank=True, default=dict, verbose_name="Métadonnées")),
                ("followup_case", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="actions", to="quarantine.quarantinerecord",
                    verbose_name="Cas de suivi",
                )),
                ("followup_day", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="actions", to="quarantine.dailycheck",
                    verbose_name="Jour de suivi",
                )),
                ("performed_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="followup_actions", to=settings.AUTH_USER_MODEL,
                    verbose_name="Effectué par",
                )),
            ],
            options={
                "verbose_name": "Action de suivi",
                "verbose_name_plural": "Actions de suivi",
                "ordering": ["-performed_at"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="followupaction",
            index=models.Index(fields=["followup_case", "-performed_at"], name="medical_fa_case_perf_idx"),
        ),
        migrations.AddIndex(
            model_name="followupaction",
            index=models.Index(fields=["action_type", "-performed_at"], name="medical_fa_type_idx"),
        ),
    ]
