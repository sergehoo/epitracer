"""Migration corrective : ajoute les champs hérités de BaseModel
(uuid + deleted_at) aux 4 tables email créées par 0004.

La migration 0004 a oublié ces champs car ils proviennent de la chaîne
d'héritage abstrait UUIDModel + SoftDeleteModel + TimestampedModel.
"""
import uuid as _uuid

from django.db import migrations, models


def populate_uuids(apps, schema_editor, model_name: str):
    Model = apps.get_model("notifications", model_name)
    for obj in Model.objects.all():
        if not obj.uuid:
            obj.uuid = _uuid.uuid4()
            obj.save(update_fields=["uuid"])


def populate_sender_profile_uuids(apps, schema_editor):
    populate_uuids(apps, schema_editor, "SenderProfile")


def populate_email_template_uuids(apps, schema_editor):
    populate_uuids(apps, schema_editor, "EmailTemplate")


def populate_email_log_uuids(apps, schema_editor):
    populate_uuids(apps, schema_editor, "EmailLog")


def populate_password_reset_token_uuids(apps, schema_editor):
    populate_uuids(apps, schema_editor, "PasswordResetToken")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0005_seed_email_templates"),
    ]

    operations = [
        # ── SenderProfile ────────────────────────────────────────────────
        migrations.AddField(
            model_name="senderprofile",
            name="uuid",
            field=models.UUIDField(default=_uuid.uuid4, editable=False, null=True, db_index=True),
        ),
        migrations.AddField(
            model_name="senderprofile",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.RunPython(populate_sender_profile_uuids, reverse_code=noop_reverse),
        migrations.AlterField(
            model_name="senderprofile",
            name="uuid",
            field=models.UUIDField(default=_uuid.uuid4, editable=False, unique=True, db_index=True),
        ),

        # ── EmailTemplate ────────────────────────────────────────────────
        migrations.AddField(
            model_name="emailtemplate",
            name="uuid",
            field=models.UUIDField(default=_uuid.uuid4, editable=False, null=True, db_index=True),
        ),
        migrations.AddField(
            model_name="emailtemplate",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.RunPython(populate_email_template_uuids, reverse_code=noop_reverse),
        migrations.AlterField(
            model_name="emailtemplate",
            name="uuid",
            field=models.UUIDField(default=_uuid.uuid4, editable=False, unique=True, db_index=True),
        ),

        # ── EmailLog ─────────────────────────────────────────────────────
        migrations.AddField(
            model_name="emaillog",
            name="uuid",
            field=models.UUIDField(default=_uuid.uuid4, editable=False, null=True, db_index=True),
        ),
        migrations.AddField(
            model_name="emaillog",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.RunPython(populate_email_log_uuids, reverse_code=noop_reverse),
        migrations.AlterField(
            model_name="emaillog",
            name="uuid",
            field=models.UUIDField(default=_uuid.uuid4, editable=False, unique=True, db_index=True),
        ),

        # ── PasswordResetToken ───────────────────────────────────────────
        migrations.AddField(
            model_name="passwordresettoken",
            name="uuid",
            field=models.UUIDField(default=_uuid.uuid4, editable=False, null=True, db_index=True),
        ),
        migrations.AddField(
            model_name="passwordresettoken",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.RunPython(populate_password_reset_token_uuids, reverse_code=noop_reverse),
        migrations.AlterField(
            model_name="passwordresettoken",
            name="uuid",
            field=models.UUIDField(default=_uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
    ]
