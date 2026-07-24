"""Migration Telegram — complément 0008.

Corrige les points manqués :
  - Ajoute 'telegram' + 'telegram_bot' dans NotificationProviderConfig
    (choices channel + provider) — la 0008 ne les avait mis que sur Notification
  - Renomme l'index auto-généré de TelegramSubscription pour matcher exactement
    ce que Django autodétecte (évite les alertes recurrentes de makemigrations)
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0008_telegram_subscription_and_channel"),
    ]

    operations = [
        # NotificationProviderConfig : mêmes choices que Notification
        migrations.AlterField(
            model_name="notificationproviderconfig",
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
        migrations.AlterField(
            model_name="notificationproviderconfig",
            name="provider",
            field=models.CharField(
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
                max_length=40,
            ),
        ),
        # Rename index TelegramSubscription pour matcher le hash auto-généré
        # par Django (dépend de l'ordre alphabétique des tables — l'index
        # posé par 0008 avait un hash conservateur, Django veut celui-ci).
        migrations.RenameIndex(
            model_name="telegramsubscription",
            new_name="notificatio_travele_72cf5d_idx",
            old_name="notif_teleg_travele_e0e0f2_idx",
        ),
    ]
