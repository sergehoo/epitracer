"""Ajout du routage multicanal SMS / WhatsApp.

- Notification : nouveaux champs (traveler, normalized_phone, direction,
  message_type, provider_message_id, error_message, retry_count,
  max_retries, sent_by, queued_at, delivered_at, failed_at, metadata).
- NotificationTemplate : disease, variables_schema, created_by.
- NotificationProviderConfig (nouveau).
- NotificationAuditLog (nouveau).
"""
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
        ("travelers", "0001_initial"),
        ("diseases", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── NotificationTemplate : nouveaux champs ──────────────────────
        migrations.AddField(
            model_name="notificationtemplate",
            name="disease",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="notification_templates",
                to="diseases.disease",
            ),
        ),
        migrations.AddField(
            model_name="notificationtemplate",
            name="variables_schema",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="notificationtemplate",
            name="created_by",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_templates",
                to=settings.AUTH_USER_MODEL,
            ),
        ),

        # ── Notification : élargir les choix de statut + nouveaux champs ─
        migrations.AlterField(
            model_name="notification",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Brouillon"),
                    ("pending", "En attente"),
                    ("queued", "En file"),
                    ("sent", "Envoyée"),
                    ("delivered", "Délivrée"),
                    ("failed", "Échec"),
                    ("cancelled", "Annulée"),
                    ("read", "Lue"),
                ],
                db_index=True, default="pending", max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="traveler",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="notifications",
                to="travelers.traveler",
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="normalized_phone",
            field=models.CharField(blank=True, db_index=True, max_length=24),
        ),
        migrations.AddField(
            model_name="notification",
            name="direction",
            field=models.CharField(
                choices=[
                    ("outbound", "Sortante (admin → voyageur)"),
                    ("inbound", "Entrante (voyageur → système)"),
                ],
                db_index=True, default="outbound", max_length=12,
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="message_type",
            field=models.CharField(
                choices=[
                    ("automatic_reminder", "Rappel automatique"),
                    ("manual_message", "Message manuel agent"),
                    ("symptom_alert", "Alerte symptômes"),
                    ("assistance", "Demande d'assistance"),
                    ("followup_reminder", "Rappel suivi 21j"),
                    ("followup_completed", "Fin de suivi"),
                    ("admin_notice", "Notice administrateur"),
                    ("location_request", "Demande de position"),
                    ("ebola_prevention", "Prévention Ebola"),
                    ("other", "Autre"),
                ],
                db_index=True, default="automatic_reminder", max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="notification",
            name="provider",
            field=models.CharField(
                blank=True, db_index=True, max_length=40,
                choices=[
                    ("orange_ci", "Orange Côte d'Ivoire"),
                    ("twilio", "Twilio"),
                    ("meta_whatsapp", "Meta WhatsApp Cloud API"),
                    ("system", "Système (stub)"),
                    ("smtp", "SMTP / Email"),
                    ("fcm", "Firebase Cloud Messaging"),
                ],
            ),
        ),
        migrations.RenameField(
            model_name="notification",
            old_name="provider_id",
            new_name="provider_message_id",
        ),
        migrations.AlterField(
            model_name="notification",
            name="provider_message_id",
            field=models.CharField(blank=True, db_index=True, max_length=200),
        ),
        migrations.RenameField(
            model_name="notification",
            old_name="error",
            new_name="error_message",
        ),
        migrations.RenameField(
            model_name="notification",
            old_name="attempts",
            new_name="retry_count",
        ),
        migrations.AddField(
            model_name="notification",
            name="max_retries",
            field=models.PositiveSmallIntegerField(default=3),
        ),
        migrations.AddField(
            model_name="notification",
            name="sent_by",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sent_notifications",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="queued_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="delivered_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="failed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="metadata",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["traveler", "-created_at"], name="notif_traveler_created_idx"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["provider_message_id"], name="notif_provider_msgid_idx"),
        ),

        # ── NotificationProviderConfig ──────────────────────────────────
        migrations.CreateModel(
            name="NotificationProviderConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="mis à jour le")),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("provider", models.CharField(
                    db_index=True, max_length=40,
                    choices=[
                        ("orange_ci", "Orange Côte d'Ivoire"),
                        ("twilio", "Twilio"),
                        ("meta_whatsapp", "Meta WhatsApp Cloud API"),
                        ("system", "Système (stub)"),
                        ("smtp", "SMTP / Email"),
                        ("fcm", "Firebase Cloud Messaging"),
                    ],
                )),
                ("channel", models.CharField(
                    db_index=True, max_length=20,
                    choices=[
                        ("sms", "SMS"), ("email", "Email"),
                        ("whatsapp", "WhatsApp"), ("push", "Push notification"),
                        ("internal", "Notification interne"),
                    ],
                )),
                ("is_enabled", models.BooleanField(db_index=True, default=True)),
                ("priority", models.PositiveSmallIntegerField(default=100)),
                ("country_code", models.CharField(blank=True, db_index=True, max_length=4)),
                ("sender_name", models.CharField(blank=True, max_length=40)),
                ("metadata", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "verbose_name": "Configuration fournisseur",
                "verbose_name_plural": "Configurations fournisseurs",
                "ordering": ["channel", "priority"],
                "abstract": False,
            },
        ),
        migrations.AddConstraint(
            model_name="notificationproviderconfig",
            constraint=models.UniqueConstraint(
                fields=("provider", "channel", "country_code"),
                name="uniq_provider_per_channel_country",
            ),
        ),

        # ── NotificationAuditLog ────────────────────────────────────────
        migrations.CreateModel(
            name="NotificationAuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="mis à jour le")),
                ("deleted_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("action", models.CharField(
                    db_index=True, max_length=20,
                    choices=[
                        ("create", "Création"), ("send", "Envoi"),
                        ("retry", "Réessai"), ("cancel", "Annulation"),
                        ("delivered", "Reçu confirmé"), ("failed", "Échec"),
                        ("view", "Consultation"),
                    ],
                )),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=300)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("actor", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="notification_actions",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("notification", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="audit_logs",
                    to="notifications.notification",
                )),
            ],
            options={
                "verbose_name": "Journal de notification",
                "verbose_name_plural": "Journaux de notification",
                "ordering": ["-created_at"],
                "abstract": False,
            },
        ),
        migrations.AddIndex(
            model_name="notificationauditlog",
            index=models.Index(fields=["notification", "-created_at"], name="notif_audit_notif_created_idx"),
        ),
    ]
