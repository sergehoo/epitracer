"""Élargit les champs `confinement_*` et `room_number` de 40 à 120 caractères.

Évite `StringDataRightTruncation` quand un voyageur saisit un texte un peu
long (« Lot N° 234, Bât. C, 2e étage », « Chambre 408 — Aile Ouest », etc.).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("travelers", "0002_historicaltraveler_passport_document_and_more"),
    ]

    operations = [
        # ----- Traveler -----
        migrations.AlterField(
            model_name="traveler",
            name="confinement_street_number",
            field=models.CharField(blank=True, max_length=120, verbose_name="N° de rue"),
        ),
        migrations.AlterField(
            model_name="traveler",
            name="confinement_lot",
            field=models.CharField(blank=True, max_length=120, verbose_name="N° de lot"),
        ),
        migrations.AlterField(
            model_name="traveler",
            name="confinement_room_number",
            field=models.CharField(blank=True, max_length=120, verbose_name="N° de chambre"),
        ),
        # ----- HistoricalTraveler (simple_history) -----
        migrations.AlterField(
            model_name="historicaltraveler",
            name="confinement_street_number",
            field=models.CharField(blank=True, max_length=120, verbose_name="N° de rue"),
        ),
        migrations.AlterField(
            model_name="historicaltraveler",
            name="confinement_lot",
            field=models.CharField(blank=True, max_length=120, verbose_name="N° de lot"),
        ),
        migrations.AlterField(
            model_name="historicaltraveler",
            name="confinement_room_number",
            field=models.CharField(blank=True, max_length=120, verbose_name="N° de chambre"),
        ),
        # ----- TravelHistoryEntry -----
        migrations.AlterField(
            model_name="travelhistoryentry",
            name="room_number",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
