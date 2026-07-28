"""Fix max_length de notification.provider (32 → 40).

Ma migration 0010 avait mis max_length=32 par erreur alors que le modèle
définit max_length=40. Aucun impact données (32 ≤ 40, aucune troncature).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0010_align_field_options"),
    ]

    operations = [
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
                max_length=40,
            ),
        ),
    ]
