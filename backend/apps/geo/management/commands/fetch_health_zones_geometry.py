"""Récupère les polygones géographiques (geometry) des HealthZone depuis
OpenStreetMap via l'API Overpass.

Stratégie :
    1. Pour chaque HealthZone sans `geometry`, on construit une requête
       Overpass `relation["boundary"="administrative"]["name"=<nom>]`
       avec un filtre `[admin_level=N]` adapté au niveau sanitaire.
    2. Si plusieurs résultats : on choisit celui qui appartient au pays
       Côte d'Ivoire (CIV / "Côte d'Ivoire" en wikidata).
    3. La réponse Overpass est convertie en MultiPolygon WKT puis stockée
       dans le champ `geometry` PostGIS.
    4. Fallback Nominatim si Overpass échoue (lookup par nom + country=CI).

Mapping admin_level OSM ↔ niveau sanitaire (selon convention OSM CI) :
    region   → admin_level=4
    district → admin_level=5 ou 6  (variable selon la zone)
    commune  → admin_level=8
    quartier → admin_level=9 ou 10 (variable, souvent non polygonal)

Usage :
    # Fetch toutes les zones sans géom
    python manage.py fetch_health_zones_geometry

    # Limiter à un niveau précis
    python manage.py fetch_health_zones_geometry --level region

    # Forcer le re-fetch (ignore les géom déjà présentes)
    python manage.py fetch_health_zones_geometry --force

    # Dry-run (n'écrit rien en DB)
    python manage.py fetch_health_zones_geometry --dry-run

Limites & politesse :
    * Overpass API impose un rate-limit : on pause 1.5s entre requêtes
      (cf. https://overpass-api.de/api/status).
    * Le fetch complet (~370 zones) prend env. 10-15 minutes.
    * En cas de timeout réseau, la commande log et continue avec la
      zone suivante (idempotent — on peut relancer).
"""
from __future__ import annotations

import json
import time
from typing import Optional
from urllib.parse import urlencode

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.core.management.base import BaseCommand
from django.db import transaction

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "EpiTrace/1.0 (contact: admin@afriqconsulting.com)"
SLEEP_BETWEEN = 1.5  # s — respecte le rate limit
HTTP_TIMEOUT = 60  # s

# Mapping niveau EpiTrace → admin_level OSM (valeurs typiques pour la CI)
LEVEL_TO_OSM_ADMIN = {
    "country": [2],
    "pres": [],            # pas d'équivalent OSM direct → skip
    "region": [4],
    "district": [5, 6],
    "commune": [7, 8],
    "quartier": [9, 10],
}


class Command(BaseCommand):
    help = "Récupère les polygones des HealthZone depuis OpenStreetMap (Overpass + Nominatim)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--level", choices=list(LEVEL_TO_OSM_ADMIN.keys()),
            help="Limiter à un niveau précis (region, district, commune, quartier).",
        )
        parser.add_argument(
            "--force", action="store_true",
            help="Re-fetch même les zones ayant déjà une geometry.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="N'écrit rien en DB, affiche juste ce qui serait fait.",
        )
        parser.add_argument(
            "--max", type=int, default=0,
            help="Nombre max de zones à traiter (0 = pas de limite).",
        )

    def handle(self, *args, **opts):
        # Import différé pour ne pas casser les autres commands quand requests
        # n'est pas (encore) installé.
        try:
            import requests
        except ImportError:
            self.stderr.write(self.style.ERROR(
                "Le module 'requests' est requis. Installation : pip install requests"
            ))
            return

        from apps.geo.models import HealthZone

        level_filter = opts.get("level")
        force = opts.get("force", False)
        dry = opts.get("dry_run", False)
        max_n = opts.get("max", 0)

        # Sélection des zones à traiter
        qs = HealthZone.objects.all()
        if level_filter:
            qs = qs.filter(level=level_filter)
        if not force:
            qs = qs.filter(geometry__isnull=True)
        # On skip les niveaux qui n'ont pas de correspondant OSM (pres)
        qs = qs.exclude(level__in=["pres", "country", "custom"])
        qs = qs.order_by("level", "name")
        if max_n:
            qs = qs[:max_n]

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING(
                "Aucune zone à traiter (toutes ont déjà une geometry, ou aucun match)."
            ))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Récupération geometry OSM pour {total} HealthZone (sleep {SLEEP_BETWEEN}s entre requêtes)"
        ))
        if dry:
            self.stdout.write(self.style.WARNING("Mode --dry-run : aucune écriture en DB.\n"))

        n_ok, n_fail, n_skip = 0, 0, 0
        for idx, zone in enumerate(qs, 1):
            self.stdout.write(f"\n[{idx}/{total}] {zone.name} ({zone.level})  ", ending="")
            geom = self._fetch_geometry(requests, zone)
            if geom is None:
                n_fail += 1
                self.stdout.write(self.style.ERROR("✗ non trouvé"))
                continue
            self.stdout.write(self.style.SUCCESS(f"✓ {geom.geom_type} ({len(geom.coords[0]) if hasattr(geom, 'coords') else '?'} pts)"))
            if not dry:
                with transaction.atomic():
                    zone.geometry = geom
                    zone.save(update_fields=["geometry", "updated_at"])
            n_ok += 1
            # Respecter le rate-limit Overpass
            time.sleep(SLEEP_BETWEEN)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"=== Terminé : {n_ok} géométries récupérées, {n_fail} échecs, {n_skip} skipped ==="
        ))
        if dry:
            self.stdout.write(self.style.WARNING("Mode --dry-run rappel : aucune écriture en DB."))

    # ------------------------------------------------------------------
    # Fetch geometry : Overpass d'abord, Nominatim en fallback
    # ------------------------------------------------------------------
    def _fetch_geometry(self, requests, zone) -> Optional["GEOSGeometry"]:
        admin_levels = LEVEL_TO_OSM_ADMIN.get(zone.level, [])
        for admin_level in admin_levels:
            try:
                geom = self._fetch_overpass(requests, zone.name, admin_level)
                if geom:
                    return geom
            except Exception as e:  # noqa: BLE001
                self.stdout.write(self.style.WARNING(f"  Overpass admin_level={admin_level} échec : {e}"), ending=" ")
        # Fallback Nominatim
        try:
            return self._fetch_nominatim(requests, zone.name)
        except Exception as e:  # noqa: BLE001
            self.stdout.write(self.style.WARNING(f"  Nominatim échec : {e}"), ending=" ")
            return None

    # ------------------------------------------------------------------
    # Overpass : requête relation boundary + reconstitution polygon
    # ------------------------------------------------------------------
    def _fetch_overpass(self, requests, name: str, admin_level: int) -> Optional["GEOSGeometry"]:
        # Query Overpass : on cherche une relation "boundary=administrative"
        # avec le nom donné, en se restreignant à la Côte d'Ivoire (area).
        # `out geom` retourne les coordonnées des ways composant la relation.
        query = f"""
        [out:json][timeout:50];
        area["ISO3166-1"="CI"]->.searchArea;
        (
          relation["boundary"="administrative"]
                  ["admin_level"="{admin_level}"]
                  ["name"="{name}"](area.searchArea);
        );
        out geom;
        """
        r = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers={"User-Agent": USER_AGENT},
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        elements = data.get("elements", [])
        if not elements:
            return None
        # On prend la première relation matchante et on reconstitue son
        # outer ring (peut être multipolygone si plusieurs outers).
        return _osm_relation_to_geos(elements[0])

    # ------------------------------------------------------------------
    # Nominatim : fallback (retourne souvent un geojson)
    # ------------------------------------------------------------------
    def _fetch_nominatim(self, requests, name: str) -> Optional["GEOSGeometry"]:
        params = {
            "q": f"{name}, Côte d'Ivoire",
            "format": "json",
            "polygon_geojson": 1,
            "limit": 1,
            "countrycodes": "ci",
        }
        url = f"{NOMINATIM_URL}?{urlencode(params)}"
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        results = r.json()
        if not results:
            return None
        geojson = results[0].get("geojson")
        if not geojson:
            return None
        geom = GEOSGeometry(json.dumps(geojson), srid=4326)
        # Convertir Polygon → MultiPolygon pour matcher le champ du modèle
        if geom.geom_type == "Polygon":
            geom = MultiPolygon(geom, srid=4326)
        if geom.geom_type != "MultiPolygon":
            return None
        return geom


# ---------------------------------------------------------------------------
# Helper : convertir une relation OSM en GEOSGeometry MultiPolygon
# ---------------------------------------------------------------------------
def _osm_relation_to_geos(element: dict) -> Optional["GEOSGeometry"]:
    """Reconstitue un MultiPolygon à partir des outer ways d'une relation."""
    members = element.get("members", [])
    outer_rings: list[list[tuple[float, float]]] = []

    # Collecter les ways "outer" et leurs coordonnées
    for m in members:
        if m.get("type") != "way":
            continue
        if m.get("role") not in ("outer", ""):
            continue
        geom = m.get("geometry")
        if not geom:
            continue
        ring = [(p["lon"], p["lat"]) for p in geom]
        # Fermer si non fermé
        if ring and ring[0] != ring[-1]:
            ring.append(ring[0])
        if len(ring) >= 4:
            outer_rings.append(ring)

    if not outer_rings:
        return None

    # Construire MultiPolygon WKT
    polygons_wkt = []
    for ring in outer_rings:
        coords = ", ".join(f"{lon} {lat}" for lon, lat in ring)
        polygons_wkt.append(f"(({coords}))")
    wkt = f"MULTIPOLYGON ({', '.join(polygons_wkt)})"

    try:
        return GEOSGeometry(wkt, srid=4326)
    except Exception:
        return None
