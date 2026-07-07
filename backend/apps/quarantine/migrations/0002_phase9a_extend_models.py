"""Phase 9A — étend QuarantineRecord et DailyCheck pour le suivi médical
complet (apps.medical).

Ajoute :
  - QuarantineRecord :
      assigned_district FK geo.HealthZone
      assigned_team CharField
      assigned_agent FK User
      current_classification CharField (cache de la classif. courante)
      closure_reason CharField
      geolocation_alert_raised_at DateTimeField (anti-spam alerte géoloc)
      2 index supplémentaires

  - DailyCheck :
      agent_responsible FK User
      decision CharField
      status CharField (workflow journée, choices élargis)
      location_shared BooleanField (snapshot)
      notification_sent BooleanField

Aucune donnée existante n'est modifiée — tous les nouveaux champs sont
nullables / ont une valeur par défaut compatible.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("quarantine", "0001_initial"),
        ("geo", "0002_extend_healthzone_levels"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------
        # QuarantineRecord — nouveaux champs
        # ------------------------------------------------------------------
        migrations.AddField(
            model_name="quarantinerecord",
            name="assigned_district",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assigned_quarantines", to="geo.healthzone",
                verbose_name="District sanitaire assigné",
            ),
        ),
        migrations.AddField(
            model_name="quarantinerecord",
            name="assigned_team",
            field=models.CharField(blank=True, max_length=120, verbose_name="Équipe assignée"),
        ),
        migrations.AddField(
            model_name="quarantinerecord",
            name="assigned_agent",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="quarantines_assigned", to=settings.AUTH_USER_MODEL,
                verbose_name="Agent assigné",
            ),
        ),
        migrations.AddField(
            model_name="quarantinerecord",
            name="current_classification",
            field=models.CharField(
                blank=True, db_index=True, max_length=30,
                verbose_name="Classification courante",
            ),
        ),
        migrations.AddField(
            model_name="quarantinerecord",
            name="closure_reason",
            field=models.CharField(
                blank=True, max_length=80,
                help_text="auto_completed / escalated / manual_close / lost_to_followup.",
                verbose_name="Motif de clôture",
            ),
        ),
        migrations.AddField(
            model_name="quarantinerecord",
            name="geolocation_alert_raised_at",
            field=models.DateTimeField(
                blank=True, null=True,
                verbose_name="Dernière alerte géoloc levée",
            ),
        ),
        migrations.AddIndex(
            model_name="quarantinerecord",
            index=models.Index(
                fields=["assigned_agent", "status"], name="quarantine_agent_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="quarantinerecord",
            index=models.Index(
                fields=["current_classification", "status"],
                name="quarantine_classif_status_idx",
            ),
        ),

        # ------------------------------------------------------------------
        # DailyCheck — nouveaux champs
        # ------------------------------------------------------------------
        migrations.AddField(
            model_name="dailycheck",
            name="agent_responsible",
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="daily_checks_managed", to=settings.AUTH_USER_MODEL,
                verbose_name="Agent responsable",
            ),
        ),
        migrations.AddField(
            model_name="dailycheck",
            name="decision",
            field=models.CharField(blank=True, max_length=200, verbose_name="Décision du jour"),
        ),
        migrations.AddField(
            model_name="dailycheck",
            name="status",
            field=models.CharField(
                choices=[
                    ("planned", "Planifié"),
                    ("pending", "En attente"),
                    ("completed", "Effectué"),
                    ("missed", "Manqué"),
                    ("alert", "Alerte"),
                    ("visit_scheduled", "Visite programmée"),
                    ("sample_requested", "Prélèvement demandé"),
                    ("analysis_in_progress", "Analyse en cours"),
                    ("escalated", "Escaladé"),
                    ("closed", "Clôturé"),
                ],
                db_index=True, default="pending", max_length=24,
                verbose_name="Statut journée",
            ),
        ),
        migrations.AddField(
            model_name="dailycheck",
            name="location_shared",
            field=models.BooleanField(default=False, verbose_name="Position partagée"),
        ),
        migrations.AddField(
            model_name="dailycheck",
            name="notification_sent",
            field=models.BooleanField(default=False, verbose_name="Notification envoyée"),
        ),
    ]
