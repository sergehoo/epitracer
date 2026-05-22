"""Migration : DataRetentionPolicy + DataPurgeLog.

Ajoute les deux modèles nécessaires à la conformité RGPD / loi 2013-450.
"""
import uuid

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("companion", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DataRetentionPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="mis à jour le")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="supprimé le")),
                ("name", models.CharField(default="Politique par défaut", max_length=120, verbose_name="Nom")),
                ("is_active", models.BooleanField(db_index=True, default=True, verbose_name="Active")),
                ("followup_retention_days", models.PositiveIntegerField(default=30,
                    help_text="Délai entre la fin du suivi 21j et l'anonymisation effective.",
                    verbose_name="Délai après clôture (jours)")),
                ("location_retention_days", models.PositiveIntegerField(default=90,
                    help_text="Les pings GPS plus anciens sont purgés indépendamment du suivi.",
                    verbose_name="Conservation des positions (jours)")),
                ("audit_log_retention_years", models.PositiveSmallIntegerField(default=5,
                    verbose_name="Conservation des logs d'audit (années)")),
                ("description", models.TextField(blank=True, verbose_name="Justification")),
            ],
            options={
                "verbose_name": "Politique de rétention des données",
                "verbose_name_plural": "Politiques de rétention",
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="DataPurgeLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("uuid", models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="créé le")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="mis à jour le")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="supprimé le")),
                ("traveler_id", models.BigIntegerField(blank=True, null=True, verbose_name="ID interne (avant purge)")),
                ("traveler_public_id", models.CharField(blank=True, db_index=True, max_length=32, verbose_name="Public ID")),
                ("pings_deleted", models.PositiveIntegerField(default=0)),
                ("subs_disabled", models.PositiveIntegerField(default=0)),
                ("email_redacted", models.BooleanField(default=False)),
                ("notes", models.TextField(blank=True)),
                ("policy", models.ForeignKey(blank=True, null=True,
                    on_delete=models.SET_NULL, related_name="purges",
                    to="companion.dataretentionpolicy")),
            ],
            options={
                "verbose_name": "Journal de purge",
                "verbose_name_plural": "Journal de purges",
                "ordering": ["-created_at"],
                "abstract": False,
            },
        ),
    ]
