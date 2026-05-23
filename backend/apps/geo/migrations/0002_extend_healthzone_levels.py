"""Étend les choix du champ HealthZone.level pour la hiérarchie CI :

    country  → National
    pres     → Pôle Régional Sanitaire  (NOUVEAU)
    region   → Région Sanitaire
    district → District Sanitaire
    commune  → Commune
    quartier → Quartier                  (NOUVEAU)
    custom   → Zone personnalisée

Aucune donnée n'est modifiée — c'est uniquement un changement de validation
des choices au niveau Django / formulaires / admin.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("geo", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="healthzone",
            name="level",
            field=models.CharField(
                choices=[
                    ("country", "National"),
                    ("pres", "Pôle Régional Sanitaire (PRES)"),
                    ("region", "Région Sanitaire"),
                    ("district", "District Sanitaire"),
                    ("commune", "Commune"),
                    ("quartier", "Quartier"),
                    ("custom", "Zone personnalisée"),
                ],
                default="district",
                max_length=20,
            ),
        ),
    ]
