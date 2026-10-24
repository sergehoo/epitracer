"""Complète le référentiel pays avec tous les pays et territoires ISO 3166-1.

Le formulaire public proposait des pays absents de la base (Kenya, Allemagne,
Canada, Chine…) : la provenance, les séjours et la nationalité choisis étaient
alors ignorés silencieusement à l'enregistrement. Idempotent : crée uniquement
les pays manquants (niveau « normal », non surveillés) sans modifier les
existants ni leurs niveaux de risque.
"""
from django.db import migrations

from apps.geo.world_countries import WORLD_COUNTRIES


def forwards(apps, schema_editor):
    Country = apps.get_model("geo", "Country")
    existing = set(Country.objects.values_list("code", flat=True))
    Country.objects.bulk_create([
        Country(code=code, name=name)
        for code, name in WORLD_COUNTRIES
        if code not in existing
    ])


class Migration(migrations.Migration):

    dependencies = [
        ("geo", "0004_seed_country_referential"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
