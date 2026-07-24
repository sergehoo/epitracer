"""Migration initiale du sous-module rapports automatisés.

Crée les 4 modèles :
  - AutomatedReportSchedule
  - AutomatedReportRecipient
  - GeneratedReport
  - ReportDeliveryLog

Note : cette app 'reports' n'avait AUCUN modèle jusqu'ici (que des vues
d'export à la volée). C'est donc la première migration.
"""
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("geo", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # =====================================================================
        # 1. AutomatedReportSchedule
        # =====================================================================
        migrations.CreateModel(
            name="AutomatedReportSchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("name", models.CharField(help_text="Étiquette humaine, ex. 'Rapport hebdomadaire INHP'.", max_length=120)),
                ("report_type", models.CharField(choices=[
                    ("weekly", "Hebdomadaire"),
                    ("monthly", "Mensuel"),
                    ("quarterly", "Trimestriel"),
                    ("adhoc", "Ponctuel"),
                ], default="weekly", max_length=20)),
                ("frequency", models.CharField(choices=[
                    ("daily", "Quotidien"),
                    ("weekly", "Hebdomadaire"),
                    ("monthly", "Mensuel"),
                ], default="weekly", max_length=20)),
                ("weekday", models.IntegerField(choices=[
                    (1, "Lundi"), (2, "Mardi"), (3, "Mercredi"),
                    (4, "Jeudi"), (5, "Vendredi"), (6, "Samedi"), (7, "Dimanche"),
                ], default=1, help_text="Jour de la semaine où le rapport est généré (ISO 8601).")),
                ("time", models.TimeField(default="08:00", help_text="Heure locale de génération.")),
                ("timezone", models.CharField(default="Africa/Abidjan", help_text="Fuseau IANA. Doit correspondre à CELERY_TIMEZONE.", max_length=64)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("include_pdf", models.BooleanField(default=True)),
                ("include_excel", models.BooleanField(default=True)),
                ("created_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=models.deletion.SET_NULL,
                    related_name="report_schedules_created",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "Planification de rapport",
                "verbose_name_plural": "Planifications de rapport",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="automatedreportschedule",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_active", True)),
                fields=("report_type",),
                name="unique_active_schedule_per_type",
            ),
        ),

        # =====================================================================
        # 2. AutomatedReportRecipient
        # =====================================================================
        migrations.CreateModel(
            name="AutomatedReportRecipient",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("full_name", models.CharField(max_length=180)),
                ("job_title", models.CharField(blank=True, max_length=120)),
                ("organization", models.CharField(blank=True, max_length=180)),
                ("phone_number", models.CharField(
                    blank=True, db_index=True, max_length=32,
                    help_text="Format international E.164 (+225XXXXXXXXXX).",
                )),
                ("email", models.EmailField(blank=True, db_index=True, max_length=254)),
                ("preferred_channel", models.CharField(choices=[
                    ("sms", "SMS uniquement"),
                    ("email", "Email uniquement"),
                    ("both", "SMS + Email"),
                ], default="email", max_length=10)),
                ("language", models.CharField(default="fr", help_text="Code ISO 639-1 (fr, en, ...).", max_length=8)),
                ("allowed_report_types", models.JSONField(blank=True, default=list, help_text="Liste des report_type autorisés — vide = tous.")),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("consent_date", models.DateField(blank=True, help_text="Date de recueil du consentement écrit du destinataire.", null=True)),
                ("consent_evidence", models.CharField(blank=True, help_text="Référence du document ou URL de preuve du consentement.", max_length=500)),
                ("created_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=models.deletion.SET_NULL,
                    related_name="report_recipients_created",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("district", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=models.deletion.SET_NULL,
                    related_name="report_recipients",
                    to="geo.healthzone",
                    help_text="District sanitaire ou périmètre géographique optionnel.",
                )),
            ],
            options={
                "verbose_name": "Destinataire de rapport",
                "verbose_name_plural": "Destinataires de rapport",
                "ordering": ["full_name"],
            },
        ),
        migrations.AddIndex(
            model_name="automatedreportrecipient",
            index=models.Index(fields=["is_active", "preferred_channel"], name="reports_aut_is_acti_a5f2d1_idx"),
        ),

        # =====================================================================
        # 3. GeneratedReport
        # =====================================================================
        migrations.CreateModel(
            name="GeneratedReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("report_code", models.CharField(db_index=True, help_text="Ex. RAP-HEBDO-2026-S24 — généré au save si vide.", max_length=32, unique=True)),
                ("report_type", models.CharField(choices=[
                    ("weekly", "Hebdomadaire"),
                    ("monthly", "Mensuel"),
                    ("quarterly", "Trimestriel"),
                    ("adhoc", "Ponctuel"),
                ], max_length=20)),
                ("period_start", models.DateTimeField(db_index=True)),
                ("period_end", models.DateTimeField(db_index=True)),
                ("status", models.CharField(choices=[
                    ("pending", "En attente"),
                    ("generating", "Génération en cours"),
                    ("ready", "Prêt"),
                    ("failed", "Échec"),
                    ("archived", "Archivé"),
                ], default="pending", max_length=20)),
                ("summary_data", models.JSONField(blank=True, default=dict)),
                ("pdf_file", models.FileField(blank=True, null=True, upload_to="reports/weekly/%Y/%m/")),
                ("excel_file", models.FileField(blank=True, null=True, upload_to="reports/weekly/%Y/%m/")),
                ("generated_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("duration_ms", models.PositiveIntegerField(blank=True, help_text="Durée de génération en millisecondes (monitoring).", null=True)),
                ("generated_by", models.ForeignKey(
                    blank=True, help_text="Null si généré par la tâche Celery Beat.",
                    null=True, on_delete=models.deletion.SET_NULL,
                    related_name="reports_generated",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "Rapport généré",
                "verbose_name_plural": "Rapports générés",
                "ordering": ["-period_start"],
            },
        ),
        migrations.AddConstraint(
            model_name="generatedreport",
            constraint=models.UniqueConstraint(
                fields=("report_type", "period_start", "period_end"),
                name="unique_report_per_type_period",
            ),
        ),
        migrations.AddIndex(
            model_name="generatedreport",
            index=models.Index(fields=["report_type", "-period_start"], name="reports_gen_report__b7c9e1_idx"),
        ),
        migrations.AddIndex(
            model_name="generatedreport",
            index=models.Index(fields=["status", "-generated_at"], name="reports_gen_status_d4f2a8_idx"),
        ),

        # =====================================================================
        # 4. ReportDeliveryLog
        # =====================================================================
        migrations.CreateModel(
            name="ReportDeliveryLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("channel", models.CharField(choices=[
                    ("sms", "SMS"),
                    ("whatsapp", "WhatsApp"),
                    ("email", "Email"),
                ], max_length=20)),
                ("provider", models.CharField(blank=True, help_text="Ex. orange_ci, twilio, smtp, ses.", max_length=40)),
                ("destination_masked", models.CharField(help_text="Version masquée du numéro ou email (jamais en clair).", max_length=80)),
                ("status", models.CharField(choices=[
                    ("queued", "En file"),
                    ("sent", "Envoyé"),
                    ("delivered", "Délivré"),
                    ("failed", "Échec"),
                    ("permanently_failed", "Échec définitif"),
                    ("retrying", "Réessai en cours"),
                ], db_index=True, default="queued", max_length=20)),
                ("notification_id", models.PositiveBigIntegerField(blank=True, help_text="FK logique vers apps.notifications.Notification.", null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("delivered_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("retry_count", models.PositiveSmallIntegerField(default=0)),
                ("next_retry_at", models.DateTimeField(blank=True, null=True)),
                ("recipient", models.ForeignKey(
                    on_delete=models.deletion.PROTECT,
                    related_name="deliveries",
                    to="reports.automatedreportrecipient",
                )),
                ("report", models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name="deliveries",
                    to="reports.generatedreport",
                )),
            ],
            options={
                "verbose_name": "Log d'envoi de rapport",
                "verbose_name_plural": "Logs d'envoi de rapport",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="reportdeliverylog",
            index=models.Index(fields=["report", "status"], name="reports_del_report__c3e5a7_idx"),
        ),
        migrations.AddIndex(
            model_name="reportdeliverylog",
            index=models.Index(fields=["recipient", "-created_at"], name="reports_del_recipie_f1d9b2_idx"),
        ),
        migrations.AddIndex(
            model_name="reportdeliverylog",
            index=models.Index(fields=["status", "next_retry_at"], name="reports_del_status_e8c4f0_idx"),
        ),
    ]
