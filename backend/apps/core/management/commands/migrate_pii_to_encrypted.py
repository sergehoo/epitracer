"""migrate_pii_to_encrypted — re-écrit ligne par ligne les valeurs PII.

Cette commande est conçue pour être lancée APRÈS une migration de schéma
qui transforme un CharField/EmailField en EncryptedCharField/EncryptedEmailField
(django-cryptography). En l'absence de cette commande, les valeurs déjà
présentes restent stockées en clair dans la colonne, car Django ne ré-écrit
pas les lignes existantes lors d'un AlterField vers un FieldType chiffré.

Stratégie :
  - Itération QuerySet.iterator() pour éviter d'épuiser la mémoire sur
    de gros volumes.
  - Update via .save(update_fields=[...]) pour déclencher l'encrypt côté
    descripteur de champ (le champ chiffré ne s'active qu'au save, pas au
    bulk_update qui contourne le ORM).
  - Idempotent : un appel rejoue les lignes déjà chiffrées sans dommage
    (re-encrypt avec la même clé).
  - --dry-run pour mesurer le nombre de lignes affectées sans écrire.
  - --batch-size pour modérer l'impact en prod (laisse respirer Postgres).

Usage en prod (recommandé : fenêtre de maintenance) :

    python manage.py migrate_pii_to_encrypted --dry-run
    python manage.py migrate_pii_to_encrypted --batch-size 200

ATTENTION :
  - À lancer dans une fenêtre de faible trafic.
  - Le champ ne doit déjà avoir été migré vers Encrypted* dans le modèle.
  - Sauvegarder la base AVANT (script `scripts/backup_db.sh`).
  - Les champs ciblés ici doivent matcher EXACTEMENT ceux marqués Encrypted*
    dans `apps/travelers/models.py`. Mettre à jour PII_FIELDS lors d'un
    ajout de champ chiffré.
"""
from __future__ import annotations

import time

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

# Mapping des modèles + champs à re-chiffrer.
# Format : (app_label.ModelName, [field_names]).
# /!\ TODO #213-4 : compléter au fur et à mesure que des champs sont migrés
# en EncryptedCharField dans les modèles. Pour l'instant la liste est vide
# tant que la migration de schéma n'a pas été appliquée — la commande
# reste no-op et idempotente, prête à être étendue.
PII_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    # Exemple (à activer après migration de schéma) :
    # ("travelers.Traveler", (
    #     "id_document_number",
    #     "phone_mobile",
    #     "email",
    #     "first_name",
    #     "last_name",
    # )),
)


class Command(BaseCommand):
    help = "Re-écrit ligne par ligne les valeurs PII pour déclencher le chiffrement."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="N'écrit rien — affiche seulement le nombre de lignes qui seraient traitées.",
        )
        parser.add_argument(
            "--batch-size", type=int, default=500,
            help="Nombre de lignes par batch (défaut: 500).",
        )
        parser.add_argument(
            "--sleep", type=float, default=0.0,
            help="Pause entre batchs (secondes) pour soulager la DB en prod.",
        )
        parser.add_argument(
            "--model", type=str, default=None,
            help="Filtrer sur un seul modèle app_label.ModelName (sinon : tous).",
        )

    def handle(self, *args, **opts):
        dry_run: bool = opts["dry_run"]
        batch_size: int = opts["batch_size"]
        sleep_between: float = opts["sleep"]
        filter_model: str | None = opts["model"]

        if not PII_FIELDS:
            self.stdout.write(self.style.WARNING(
                "PII_FIELDS est vide — aucun champ à re-chiffrer pour l'instant.\n"
                "Mettre à jour apps/core/management/commands/migrate_pii_to_encrypted.py\n"
                "après avoir migré les modèles vers EncryptedCharField."
            ))
            return

        total = 0
        for dotted, fields in PII_FIELDS:
            if filter_model and dotted != filter_model:
                continue
            app_label, model_name = dotted.split(".")
            Model = apps.get_model(app_label, model_name)
            qs = Model.objects.all().order_by("pk")
            count = qs.count()
            self.stdout.write(
                f"=> {dotted} : {count} lignes, champs={list(fields)}"
            )
            if dry_run:
                total += count
                continue

            processed = 0
            # Itération par chunks pour limiter la mémoire et permettre un
            # commit incrémental (et non un long transaction-lock).
            for start in range(0, count, batch_size):
                end = start + batch_size
                pk_chunk = list(qs.values_list("pk", flat=True)[start:end])
                with transaction.atomic():
                    for instance in Model.objects.filter(pk__in=pk_chunk):
                        # save(update_fields=...) déclenche le descripteur du
                        # champ chiffré qui re-encrypte le ciphertext.
                        instance.save(update_fields=list(fields))
                processed += len(pk_chunk)
                self.stdout.write(
                    f"   {dotted}: {processed}/{count}"
                )
                if sleep_between:
                    time.sleep(sleep_between)

            total += processed

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"DRY-RUN : {total} lignes seraient traitées."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"OK — {total} lignes re-chiffrées."
            ))
