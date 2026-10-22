"""Catalogue public des maladies : brouillons de fiches + maladies manquantes.

Idempotent. Les maladies ajoutées (dengue, méningite, rougeole) sont créées
INACTIVES ; aucune fiche n'est publiée : la publication reste un acte d'un
administrateur habilité. Les champs déjà renseignés ne sont jamais écrasés.
"""
from django.db import migrations

from apps.diseases.catalog import sync_disease_catalog


def forwards(apps, schema_editor):
    sync_disease_catalog(
        apps.get_model("diseases", "Disease"),
        apps.get_model("diseases", "Symptom"),
        apps.get_model("diseases", "RiskFactor"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("diseases", "0002_disease_public_content"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
