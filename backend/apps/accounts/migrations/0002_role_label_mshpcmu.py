"""Renomme le label du rôle MINISTRY en 'MSHPCMU (Ministère de la Santé)'.

La valeur stockée (code) reste 'MINISTRY' pour ne pas casser les FK ;
seul le label affiché change.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="role",
            name="code",
            field=models.CharField(
                choices=[
                    ("NATIONAL_ADMIN", "Super Admin National"),
                    ("MINISTRY", "MSHPCMU (Ministère de la Santé)"),
                    ("INHP", "INHP"),
                    ("DISTRICT", "District Sanitaire"),
                    ("ENTRY_POINT", "Responsable Point d'Entrée"),
                    ("BORDER_AGENT", "Agent Frontière"),
                    ("FIELD_AGENT", "Agent Terrain"),
                    ("LABORATORY", "Laboratoire"),
                    ("OBSERVER", "Observateur"),
                    ("TRAVELER", "Voyageur"),
                ],
                max_length=40,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="roleassignment",
            name="role",
            field=models.ForeignKey(
                on_delete=models.deletion.PROTECT,
                related_name="assignments",
                to="accounts.role",
            ),
        ),
    ]
