"""Référentiel pays : sous-région ouest-africaine + reprise des niveaux existants.

Idempotent et sans doublon :
1. convertit l'ancienne échelle (low/red) vers la nouvelle (normal/critical) ;
2. transforme chaque niveau existant supérieur à normal en évaluation datée
   (par maladie si la maladie existe, sinon « toutes maladies »), une seule fois ;
3. crée les pays manquants (ISO-2/ISO-3) et complète les existants sans écraser
   les valeurs saisies ; les nouveaux pays restent au niveau « normal ».
"""
from django.db import migrations
from django.utils import timezone

from apps.geo.referential import MONITORED_CODES, sync_reference_countries

LEGACY_TO_NEW = {"low": "normal", "red": "critical"}
LEGACY_SOURCE = "Référentiel pays antérieur"


def forwards(apps, schema_editor):
    Country = apps.get_model("geo", "Country")
    Assessment = apps.get_model("geo", "CountryRiskAssessment")
    Disease = apps.get_model("diseases", "Disease")

    for old, new in LEGACY_TO_NEW.items():
        Country.objects.filter(risk_level=old).update(risk_level=new)

    today = timezone.localdate()
    for country in Country.objects.exclude(risk_level="normal"):
        if Assessment.objects.filter(country=country).exists():
            continue
        codes = [str(c).upper() for c in (country.risk_for_diseases or [])]
        diseases = list(Disease.objects.filter(code__in=codes)) or [None]
        justification = (
            "Niveau repris du référentiel pays existant lors du passage à l'historique "
            "par maladie (migration geo 0004). À confirmer au regard des alertes sanitaires validées."
        )
        if codes:
            justification += f" Maladies d'origine : {', '.join(codes)}."
        for disease in diseases:
            Assessment.objects.create(
                country=country, disease=disease, risk_level=country.risk_level,
                valid_from=today, justification=justification, source_reference=LEGACY_SOURCE,
            )
        country.is_monitored = True
        country.save(update_fields=["is_monitored"])

    sync_reference_countries(Country)
    Country.objects.filter(code__in=MONITORED_CODES).update(is_monitored=True)


def backwards(apps, schema_editor):
    Country = apps.get_model("geo", "Country")
    for old, new in LEGACY_TO_NEW.items():
        Country.objects.filter(risk_level=new).update(risk_level=old)


class Migration(migrations.Migration):

    dependencies = [
        ("geo", "0003_country_risk_assessments"),
        ("diseases", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
