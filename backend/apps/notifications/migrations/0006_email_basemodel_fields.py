"""Migration corrective : ajoute les champs hérités de BaseModel
(uuid + deleted_at) aux 4 tables email créées par 0004.

⚠️ PIÈGE Django : si on met `default=uuid.uuid4` sur un AddField avec des
rows existantes, la fonction est appelée UNE SEULE FOIS et toutes les
rows reçoivent le MÊME UUID — l'AlterField unique=True plante ensuite
avec UniqueViolation.

Stratégie correcte :
  1. AddField uuid SANS default (null=True) → toutes les rows à NULL
  2. RunPython remplit chaque row avec un uuid4() distinct
  3. AlterField pour passer unique=True (les valeurs sont déjà uniques)
"""
import uuid as _uuid

from django.db import migrations, models


def populate_uuids(model_name: str):
    """Factory qui retourne une RunPython callable.

    Génère un UUID DIFFÉRENT pour chaque row (appel `_uuid.uuid4()` à
    chaque itération).
    """
    def _run(apps, schema_editor):
        Model = apps.get_model("notifications", model_name)
        for obj in Model.objects.all():
            obj.uuid = _uuid.uuid4()
            obj.save(update_fields=["uuid"])
    return _run


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
            field=models.UUIDField(null=True, editable=False, db_index=True),
        ),
        migrations.AddField(
            model_name="senderprofile",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.RunPython(populate_uuids("SenderProfile"), reverse_code=noop_reverse),
        migrations.AlterField(
            model_name="senderprofile",
            name="uuid",
            field=models.UUIDField(default=_uuid.uuid4, editable=False, unique=True, db_index=True),
        ),

        # ── EmailTemplate ────────────────────────────────────────────────
        migrations.AddField(
            model_name="emailtemplate",
            name="uuid",
            field=models.UUIDField(null=True, editable=False, db_index=True),
        ),
        migrations.AddField(
            model_name="emailtemplate",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.RunPython(populate_uuids("EmailTemplate"), reverse_code=noop_reverse),
        migrations.AlterField(
            model_name="emailtemplate",
            name="uuid",
            field=models.UUIDField(default=_uuid.uuid4, editable=False, unique=True, db_index=True),
        ),

        # ── EmailLog ─────────────────────────────────────────────────────
        migrations.AddField(
            model_name="emaillog",
            name="uuid",
            field=models.UUIDField(null=True, editable=False, db_index=True),
        ),
        migrations.AddField(
            model_name="emaillog",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.RunPython(populate_uuids("EmailLog"), reverse_code=noop_reverse),
        migrations.AlterField(
            model_name="emaillog",
            name="uuid",
            field=models.UUIDField(default=_uuid.uuid4, editable=False, unique=True, db_index=True),
        ),

        # ── PasswordResetToken ───────────────────────────────────────────
        migrations.AddField(
            model_name="passwordresettoken",
            name="uuid",
            field=models.UUIDField(null=True, editable=False, db_index=True),
        ),
        migrations.AddField(
            model_name="passwordresettoken",
            name="deleted_at",
            field=models.DateTimeField(blank=True, null=True, db_index=True),
        ),
        migrations.RunPython(populate_uuids("PasswordResetToken"), reverse_code=noop_reverse),
        migrations.AlterField(
            model_name="passwordresettoken",
            name="uuid",
            field=models.UUIDField(default=_uuid.uuid4, editable=False, unique=True, db_index=True),
        ),
    ]
