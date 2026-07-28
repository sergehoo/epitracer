"""Alignement des options de champs pour les 4 modèles reports.

La migration 0001_initial a été écrite à la main sans tous les kwargs
finaux (db_index=True sur uuid, verbose_name FR sur timestamps, hash
d'index calculé différemment par Django).

Cette migration aligne le tout — aucun impact fonctionnel, uniquement
labels admin + indexes optimisés.
"""
import uuid

from django.db import migrations, models
from django.utils.translation import gettext_lazy as _


class Migration(migrations.Migration):

    dependencies = [
        ("reports", "0001_initial"),
    ]

    operations = [
        # ─── Renommage des indexes (hash Django-calculé exact) ─────────
        migrations.RenameIndex(
            model_name="automatedreportrecipient",
            new_name="reports_aut_is_acti_1b3b39_idx",
            old_name="reports_aut_is_acti_a5f2d1_idx",
        ),
        migrations.RenameIndex(
            model_name="generatedreport",
            new_name="reports_gen_report__4da94e_idx",
            old_name="reports_gen_report__b7c9e1_idx",
        ),
        migrations.RenameIndex(
            model_name="generatedreport",
            new_name="reports_gen_status_8cc69e_idx",
            old_name="reports_gen_status_d4f2a8_idx",
        ),
        migrations.RenameIndex(
            model_name="reportdeliverylog",
            new_name="reports_rep_report__b4a293_idx",
            old_name="reports_del_report__c3e5a7_idx",
        ),
        migrations.RenameIndex(
            model_name="reportdeliverylog",
            new_name="reports_rep_recipie_c3f5dc_idx",
            old_name="reports_del_recipie_f1d9b2_idx",
        ),
        migrations.RenameIndex(
            model_name="reportdeliverylog",
            new_name="reports_rep_status_f1f9ca_idx",
            old_name="reports_del_status_e8c4f0_idx",
        ),

        # ─── AutomatedReportRecipient — 4 champs BaseModel ─────────────
        migrations.AlterField(
            model_name="automatedreportrecipient", name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False,
                verbose_name="ID",
            ),
        ),
        migrations.AlterField(
            model_name="automatedreportrecipient", name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="automatedreportrecipient", name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, db_index=True, verbose_name=_("créé le"),
            ),
        ),
        migrations.AlterField(
            model_name="automatedreportrecipient", name="updated_at",
            field=models.DateTimeField(
                auto_now=True, verbose_name=_("mis à jour le"),
            ),
        ),

        # ─── AutomatedReportSchedule — idem ────────────────────────────
        migrations.AlterField(
            model_name="automatedreportschedule", name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False,
                verbose_name="ID",
            ),
        ),
        migrations.AlterField(
            model_name="automatedreportschedule", name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="automatedreportschedule", name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, db_index=True, verbose_name=_("créé le"),
            ),
        ),
        migrations.AlterField(
            model_name="automatedreportschedule", name="updated_at",
            field=models.DateTimeField(
                auto_now=True, verbose_name=_("mis à jour le"),
            ),
        ),

        # ─── GeneratedReport — idem ────────────────────────────────────
        migrations.AlterField(
            model_name="generatedreport", name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False,
                verbose_name="ID",
            ),
        ),
        migrations.AlterField(
            model_name="generatedreport", name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="generatedreport", name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, db_index=True, verbose_name=_("créé le"),
            ),
        ),
        migrations.AlterField(
            model_name="generatedreport", name="updated_at",
            field=models.DateTimeField(
                auto_now=True, verbose_name=_("mis à jour le"),
            ),
        ),

        # ─── ReportDeliveryLog — idem ──────────────────────────────────
        migrations.AlterField(
            model_name="reportdeliverylog", name="id",
            field=models.BigAutoField(
                auto_created=True, primary_key=True, serialize=False,
                verbose_name="ID",
            ),
        ),
        migrations.AlterField(
            model_name="reportdeliverylog", name="uuid",
            field=models.UUIDField(
                db_index=True, default=uuid.uuid4, editable=False, unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="reportdeliverylog", name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, db_index=True, verbose_name=_("créé le"),
            ),
        ),
        migrations.AlterField(
            model_name="reportdeliverylog", name="updated_at",
            field=models.DateTimeField(
                auto_now=True, verbose_name=_("mis à jour le"),
            ),
        ),
    ]
