"""Migration Telegram : channel + provider + modèle TelegramSubscription."""
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0007_rename_notif_emaillog_status_created_notificatio_status_d84ea4_idx_and_more"),
        ("travelers", "0001_initial"),  # dépendance Traveler
    ]

    operations = [
        # Étendre Channel choices sur Notification
        migrations.AlterField(
            model_name="notification",
            name="channel",
            field=models.CharField(
                choices=[
                    ("sms", "SMS"),
                    ("email", "Email"),
                    ("whatsapp", "WhatsApp"),
                    ("push", "Push notification"),
                    ("telegram", "Telegram"),
                    ("internal", "Notification interne"),
                ],
                max_length=20,
            ),
        ),
        # Étendre Provider choices
        migrations.AlterField(
            model_name="notification",
            name="provider",
            field=models.CharField(
                blank=True,
                choices=[
                    ("orange_ci", "Orange Côte d'Ivoire"),
                    ("twilio", "Twilio"),
                    ("meta_whatsapp", "Meta WhatsApp Cloud API"),
                    ("system", "Système (stub)"),
                    ("smtp", "SMTP / Email"),
                    ("fcm", "Firebase Cloud Messaging"),
                    ("telegram_bot", "Telegram Bot API"),
                ],
                default="",
                max_length=32,
            ),
        ),
        # Créer le modèle TelegramSubscription
        migrations.CreateModel(
            name="TelegramSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("chat_id", models.CharField(
                    db_index=True, max_length=64, unique=True,
                    help_text="ID de chat Telegram (int stocké en str pour éviter la limite bigint).",
                )),
                ("username", models.CharField(
                    blank=True, max_length=64,
                    help_text="@username Telegram du voyageur, s'il en a un.",
                )),
                ("first_name", models.CharField(blank=True, max_length=120)),
                ("last_name", models.CharField(blank=True, max_length=120)),
                ("language_code", models.CharField(blank=True, max_length=8)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("linked_at", models.DateTimeField(auto_now_add=True)),
                ("last_message_at", models.DateTimeField(blank=True, null=True)),
                ("traveler", models.ForeignKey(
                    on_delete=models.deletion.CASCADE,
                    related_name="telegram_subs",
                    to="travelers.traveler",
                )),
            ],
            options={
                "verbose_name": "Abonnement Telegram",
                "verbose_name_plural": "Abonnements Telegram",
                "ordering": ["-linked_at"],
            },
        ),
        migrations.AddIndex(
            model_name="telegramsubscription",
            index=models.Index(fields=["traveler", "is_active"], name="notif_teleg_travele_e0e0f2_idx"),
        ),
    ]
