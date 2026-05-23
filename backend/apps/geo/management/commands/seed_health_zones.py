"""Peuple la table HealthZone avec la hiérarchie sanitaire CI complète :

    National (1) → PRES (5) → Région (33) → District (~113) → Commune (~60)
    → Quartier (~150)

Les codes sont générés via slugify avec un préfixe par niveau, afin d'éviter
les collisions et de faciliter les lookups (ex : `dist-abobo-est`).

La commande est **idempotente** : un re-run met à jour le `name` et le
`parent` sans casser les FK existantes (HealthAlert.zone, etc.). Les
zones non-listées dans la source ne sont PAS supprimées (pour préserver
d'éventuelles zones customs créées manuellement par les agents).

Usage :
    python manage.py seed_health_zones                # peuple / met à jour
    python manage.py seed_health_zones --clear        # vide d'abord (DANGER)
    python manage.py seed_health_zones --dry-run      # affiche sans rien faire
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils.text import slugify

from apps.geo.management._ci_health_data import (
    COUNTRY, PRES, REGIONS, COMMUNES_ABIDJAN, COMMUNES_AUTRES, QUARTIERS,
)


def _code(prefix: str, name: str) -> str:
    """Génère un slug stable pour le code HealthZone."""
    base = slugify(name, allow_unicode=False)[:50]
    return f"{prefix}-{base}"[:60]


class Command(BaseCommand):
    help = "Peuple HealthZone avec la hiérarchie sanitaire CI (National → Quartier)."

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true",
                            help="Supprime toutes les HealthZone avant de seeder. DANGER.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Affiche le plan sans toucher la DB.")

    def handle(self, *args, **opts):
        from apps.geo.models import HealthZone

        dry = opts.get("dry_run", False)
        clear = opts.get("clear", False)

        if clear and not dry:
            n = HealthZone.objects.count()
            HealthZone.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"  {n} HealthZone supprimées."))

        n_created, n_updated = 0, 0

        # --------------------------------------------------------------
        # 1) National
        # --------------------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("1) Niveau National"))
        country, c, u = self._upsert(
            HealthZone, dry,
            code=COUNTRY["code"], name=COUNTRY["name"],
            level="country", parent=None,
        )
        n_created += c; n_updated += u
        self.stdout.write(f"   • {COUNTRY['name']}")

        # --------------------------------------------------------------
        # 2) PRES
        # --------------------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n2) Pôles Régionaux Sanitaires (PRES) — {len(PRES)}"))
        pres_by_name: dict[str, "HealthZone"] = {}
        for pres in PRES:
            obj, c, u = self._upsert(
                HealthZone, dry,
                code=pres["code"], name=pres["name"],
                level="pres", parent=country,
            )
            n_created += c; n_updated += u
            pres_by_name[pres["name"]] = obj
            self.stdout.write(f"   • {pres['name']} ({len(pres['regions'])} régions)")

        # Index région → PRES parent
        region_to_pres: dict[str, "HealthZone"] = {}
        for pres in PRES:
            for region_name in pres["regions"]:
                region_to_pres[region_name] = pres_by_name[pres["name"]]

        # --------------------------------------------------------------
        # 3) Régions sanitaires
        # --------------------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n3) Régions Sanitaires — {len(REGIONS)}"))
        regions_by_name: dict[str, "HealthZone"] = {}
        for region in REGIONS:
            parent = region_to_pres.get(region["name"], country)
            obj, c, u = self._upsert(
                HealthZone, dry,
                code=_code("reg", region["name"]),
                name=region["name"],
                level="region", parent=parent,
            )
            n_created += c; n_updated += u
            regions_by_name[region["name"]] = obj
        self.stdout.write(f"   → {len(REGIONS)} régions seedées.")

        # --------------------------------------------------------------
        # 4) Districts sanitaires
        # --------------------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("\n4) Districts Sanitaires"))
        districts_by_name: dict[str, "HealthZone"] = {}
        n_districts = 0
        for region in REGIONS:
            region_obj = regions_by_name[region["name"]]
            for district_name in region["districts"]:
                obj, c, u = self._upsert(
                    HealthZone, dry,
                    code=_code("dist", district_name),
                    name=district_name,
                    level="district", parent=region_obj,
                )
                n_created += c; n_updated += u
                districts_by_name[district_name] = obj
                n_districts += 1
        self.stdout.write(f"   → {n_districts} districts seedés.")

        # --------------------------------------------------------------
        # 5) Communes
        # --------------------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("\n5) Communes"))
        communes_by_name: dict[str, "HealthZone"] = {}
        n_communes = 0
        for commune in COMMUNES_ABIDJAN + COMMUNES_AUTRES:
            district_name = commune["district"]
            parent = districts_by_name.get(district_name)
            if parent is None:
                self.stdout.write(self.style.WARNING(
                    f"   ⚠ Commune {commune['name']} : district {district_name!r} introuvable, rattachée au pays"
                ))
                parent = country
            obj, c, u = self._upsert(
                HealthZone, dry,
                code=_code("com", commune["name"]),
                name=commune["name"],
                level="commune", parent=parent,
            )
            n_created += c; n_updated += u
            communes_by_name[commune["name"]] = obj
            n_communes += 1
        self.stdout.write(f"   → {n_communes} communes seedées.")

        # --------------------------------------------------------------
        # 6) Quartiers
        # --------------------------------------------------------------
        self.stdout.write(self.style.MIGRATE_HEADING("\n6) Quartiers"))
        n_quartiers = 0
        for commune_name, quartiers in QUARTIERS.items():
            commune_obj = communes_by_name.get(commune_name)
            if commune_obj is None:
                self.stdout.write(self.style.WARNING(
                    f"   ⚠ Commune {commune_name!r} non trouvée, quartiers ignorés"
                ))
                continue
            for quartier_name in quartiers:
                obj, c, u = self._upsert(
                    HealthZone, dry,
                    code=_code("qua", quartier_name),
                    name=quartier_name,
                    level="quartier", parent=commune_obj,
                )
                n_created += c; n_updated += u
                n_quartiers += 1
        self.stdout.write(f"   → {n_quartiers} quartiers seedés.")

        # --------------------------------------------------------------
        # Récapitulatif
        # --------------------------------------------------------------
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"=== Seed terminé : {n_created} créés, {n_updated} mis à jour ==="
        ))
        if dry:
            self.stdout.write(self.style.WARNING("Mode --dry-run : aucune modification en base."))
        else:
            total = HealthZone.objects.count()
            by_level = HealthZone.objects.values('level').annotate(
                n=Count('id'),
            ).order_by('level')
            self.stdout.write(f"\nÉtat final HealthZone (total : {total}) :")
            for row in by_level:
                self.stdout.write(f"   {row['level']:12s} {row['n']}")

    # ------------------------------------------------------------------
    # Helper upsert idempotent
    # ------------------------------------------------------------------
    def _upsert(self, model, dry: bool, *, code: str, name: str, level: str, parent):
        """Crée ou met à jour une HealthZone. Retourne (obj, created_flag, updated_flag)."""
        if dry:
            return None, 1, 0
        with transaction.atomic():
            obj, created = model.objects.get_or_create(
                code=code,
                defaults={"name": name, "level": level, "parent": parent},
            )
            if created:
                return obj, 1, 0
            # Update if changed
            changed = False
            if obj.name != name:
                obj.name = name; changed = True
            if obj.level != level:
                obj.level = level; changed = True
            if obj.parent_id != (parent.id if parent else None):
                obj.parent = parent; changed = True
            if changed:
                obj.save(update_fields=["name", "level", "parent", "updated_at"])
                return obj, 0, 1
            return obj, 0, 0
