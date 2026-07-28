"""Alignement des options de champs — dérive cosmétique détectée par makemigrations.

Les migrations 0008 (Telegram) et 0009 (rebrand) ont été écrites à la main
avec des options légèrement différentes de celles inférées par Django
depuis les modèles (verbose_name manquant, db_index oublié sur created_at
et deleted_at, choices channel/provider re-inférés).

Aucun impact fonctionnel — que du cosmétique / index pour perf.
"""
import uuid

from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0009_telegram_provider_config_and_index_rename"),
    ]

    operations = [
        # Notification.channel — re-alignement des choices dans l'ordre exact
        # (impact 0 : les codes en DB restent identiques).
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
                db_index=True,
                max_length=20,
            ),
        ),
        # Notification.provider — idem
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
                db_index=True,
                default="",
                max_length=32,
            ),
        ),
        # TelegramSubscription.id : cosmétique, aligne auto_created (aucun changement DDL)
        migrations.AlterField(
            model_name="telegramsubscription",
            name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False,
                verbose_name="ID",
            ),
        ),
        # TelegramSubscription.uuid : ajoute db_index=True (perf lookups par uuid)
        migrations.AlterField(
            model_name="telegramsubscription",
            name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True,
            ),
        ),
        # TelegramSubscription.created_at : ajoute db_index + verbose_name
        migrations.AlterField(
            model_name="telegramsubscription",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, db_index=True, verbose_name=_("créé le"),
            ),
        ),
        # TelegramSubscription.updated_at : ajoute verbose_name
        migrations.AlterField(
            model_name="telegramsubscription",
            name="updated_at",
            field=models.DateTimeField(
                auto_now=True, verbose_name=_("mis à jour le"),
            ),
        ),
        # TelegramSubscription.deleted_at : ajoute db_index=True
        migrations.AlterField(
            model_name="telegramsubscription",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
    ]
