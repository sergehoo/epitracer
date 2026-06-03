"""Migration initiale mobile_api : MobileDevice, Vaccination, AssistanceRequest, LocationShare."""
import uuid as _uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── MobileDevice ─────────────────────────────────────────────────
        migrations.CreateModel(
            name="MobileDevice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=_uuid.uuid4, editable=False, unique=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True, db_index=True)),
                ("fcm_token", models.CharField(max_length=512, unique=True, verbose_name="token FCM")),
                ("platform", models.CharField(
                    choices=[("android", "Android"), ("ios", "iOS"), ("web", "Web (PWA)")],
                    default="android", max_length=20,
                )),
                ("device_id", models.CharField(blank=True, max_length=200, verbose_name="identifiant appareil")),
                ("app_version", models.CharField(blank=True, max_length=40)),
                ("os_version", models.CharField(blank=True, max_length=40)),
                ("locale", models.CharField(default="fr-CI", max_length=20)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("user", models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name="mobile_devices",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "Appareil mobile",
                "verbose_name_plural": "Appareils mobiles",
                "ordering": ["-last_seen_at"],
                "indexes": [
                    models.Index(fields=["user", "is_active"], name="mobi_dev_user_active_idx"),
                    models.Index(fields=["fcm_token"], name="mobi_dev_token_idx"),
                ],
            },
        ),

        # ── Vaccination ──────────────────────────────────────────────────
        migrations.CreateModel(
            name="Vaccination",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=_uuid.uuid4, editable=False, unique=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True, db_index=True)),
                ("disease_code", models.CharField(db_index=True, max_length=40, verbose_name="code maladie")),
                ("disease_name", models.CharField(max_length=120, verbose_name="nom maladie")),
                ("vaccine_name", models.CharField(max_length=160, verbose_name="nom du vaccin")),
                ("manufacturer", models.CharField(blank=True, max_length=160, verbose_name="fabricant / labo")),
                ("lot_number", models.CharField(blank=True, max_length=80, verbose_name="n° de lot")),
                ("administered_at", models.DateField(db_index=True, verbose_name="date d'administration")),
                ("next_dose_at", models.DateField(blank=True, null=True, verbose_name="prochaine dose")),
                ("dose_number", models.PositiveSmallIntegerField(default=1, verbose_name="n° de dose")),
                ("total_doses", models.PositiveSmallIntegerField(default=1, verbose_name="doses totales")),
                ("center_name", models.CharField(blank=True, max_length=200, verbose_name="centre de vaccination")),
                ("country_code", models.CharField(default="CI", max_length=2, verbose_name="pays")),
                ("certificate_pdf", models.FileField(blank=True, null=True, upload_to="vaccinations/certificates/%Y/%m/")),
                ("qr_payload", models.TextField(blank=True, help_text="Payload QR officiel si fourni")),
                ("verified", models.BooleanField(default=False, help_text="Validé par un agent INHP / centre agréé")),
                ("notes", models.TextField(blank=True)),
                ("user", models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name="vaccinations",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "Vaccination",
                "verbose_name_plural": "Carnet vaccinal",
                "ordering": ["-administered_at", "-created_at"],
                "indexes": [
                    models.Index(fields=["user", "-administered_at"], name="vacc_user_date_idx"),
                    models.Index(fields=["disease_code"], name="vacc_disease_idx"),
                ],
            },
        ),

        # ── AssistanceRequest ────────────────────────────────────────────
        migrations.CreateModel(
            name="AssistanceRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=_uuid.uuid4, editable=False, unique=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True, db_index=True)),
                ("reason", models.CharField(blank=True, max_length=200, verbose_name="motif")),
                ("message", models.TextField(blank=True, verbose_name="message")),
                ("callback_phone", models.CharField(max_length=32, verbose_name="téléphone de rappel")),
                ("preferred_time", models.CharField(blank=True, max_length=80, verbose_name="plage horaire préférée")),
                ("latitude", models.FloatField(blank=True, null=True)),
                ("longitude", models.FloatField(blank=True, null=True)),
                ("status", models.CharField(
                    choices=[
                        ("pending", "En attente"),
                        ("assigned", "Assignée"),
                        ("contacted", "Voyageur contacté"),
                        ("closed", "Clôturée"),
                    ],
                    db_index=True, default="pending", max_length=20,
                )),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("closed_note", models.TextField(blank=True)),
                ("user", models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name="assistance_requests",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("assigned_to", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=models.deletion.SET_NULL,
                    related_name="assistance_assignments",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "Demande d'assistance",
                "verbose_name_plural": "Demandes d'assistance",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["status", "-created_at"], name="ass_req_status_idx"),
                    models.Index(fields=["user"], name="ass_req_user_idx"),
                ],
            },
        ),

        # ── LocationShare ────────────────────────────────────────────────
        migrations.CreateModel(
            name="LocationShare",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(default=_uuid.uuid4, editable=False, unique=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True, db_index=True)),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                ("accuracy_m", models.FloatField(blank=True, null=True)),
                ("context", models.CharField(
                    blank=True, max_length=60,
                    help_text="ex: 'assistance_request', 'checkin', 'manual'",
                    verbose_name="contexte",
                )),
                ("user", models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name="location_shares",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("shared_with_agent", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=models.deletion.SET_NULL,
                    related_name="shared_locations_received",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "Partage de position",
                "verbose_name_plural": "Partages de position",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["user", "-created_at"], name="loc_share_user_idx"),
                ],
            },
        ),
    ]
