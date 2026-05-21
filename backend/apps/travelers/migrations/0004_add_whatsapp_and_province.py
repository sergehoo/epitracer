"""Ajoute Traveler.whatsapp_phone et TravelHistoryEntry.province.

- whatsapp_phone : numéro WhatsApp international (E.164), saisi via Step4 du
  formulaire public. Obligatoire côté formulaire, optionnel côté DB pour
  permettre la migration des voyageurs existants sans valeur.
- province : subdivision administrative (région/province) à l'intérieur du
  pays de provenance / pays visité, demandée en Step3.
"""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("travelers", "0003_widen_confinement_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="traveler",
            name="whatsapp_phone",
            field=models.CharField(
                blank=True,
                help_text="Format E.164 (ex : +22507XXXXXXXX).",
                max_length=32,
                verbose_name="Numéro WhatsApp international",
            ),
        ),
        migrations.AddField(
            model_name="historicaltraveler",
            name="whatsapp_phone",
            field=models.CharField(
                blank=True,
                help_text="Format E.164 (ex : +22507XXXXXXXX).",
                max_length=32,
                verbose_name="Numéro WhatsApp international",
            ),
        ),
        migrations.AddField(
            model_name="travelhistoryentry",
            name="province",
            field=models.CharField(
                blank=True,
                help_text="Subdivision administrative à l'intérieur du pays (ex: Nord-Kivu).",
                max_length=160,
                verbose_name="Province / Région",
            ),
        ),
    ]
