"""Référentiel des pays suivis (codes ISO 3166-1), partagé par la migration et le seed.

Les fonctions prennent la classe du modèle Country en paramètre pour fonctionner aussi
bien avec le modèle courant qu'avec le modèle historique d'une migration.
Aucun niveau de risque n'est défini ici : il est porté par les
CountryRiskAssessment, saisies à partir d'alertes sanitaires validées.
"""

from __future__ import annotations

WEST_AFRICA_REGION = "Afrique de l'Ouest"
CENTRAL_AFRICA_REGION = "Afrique centrale"

# (ISO-2, ISO-3, nom, région, pays surveillé)
REFERENCE_COUNTRIES: list[tuple[str, str, str, str, bool]] = [
    # Sous-région ouest-africaine
    ("CI", "CIV", "Côte d'Ivoire", WEST_AFRICA_REGION, True),
    ("GH", "GHA", "Ghana", WEST_AFRICA_REGION, True),
    ("TG", "TGO", "Togo", WEST_AFRICA_REGION, True),
    ("BJ", "BEN", "Bénin", WEST_AFRICA_REGION, True),
    ("BF", "BFA", "Burkina Faso", WEST_AFRICA_REGION, True),
    ("ML", "MLI", "Mali", WEST_AFRICA_REGION, True),
    ("NE", "NER", "Niger", WEST_AFRICA_REGION, True),
    ("NG", "NGA", "Nigeria", WEST_AFRICA_REGION, True),
    ("GN", "GIN", "Guinée", WEST_AFRICA_REGION, True),
    ("GW", "GNB", "Guinée-Bissau", WEST_AFRICA_REGION, True),
    ("LR", "LBR", "Liberia", WEST_AFRICA_REGION, True),
    ("SL", "SLE", "Sierra Leone", WEST_AFRICA_REGION, True),
    ("SN", "SEN", "Sénégal", WEST_AFRICA_REGION, True),
    ("GM", "GMB", "Gambie", WEST_AFRICA_REGION, True),
    ("CV", "CPV", "Cap-Vert", WEST_AFRICA_REGION, True),
    ("MR", "MRT", "Mauritanie", WEST_AFRICA_REGION, True),
    # Pays déjà présents dans le référentiel initial
    ("CD", "COD", "République démocratique du Congo", CENTRAL_AFRICA_REGION, True),
    ("CG", "COG", "République du Congo", CENTRAL_AFRICA_REGION, True),
    ("UG", "UGA", "Ouganda", "Afrique de l'Est", False),
    ("FR", "FRA", "France", "Europe", False),
    ("US", "USA", "États-Unis", "Amérique", False),
]

WEST_AFRICA_CODES = [c[0] for c in REFERENCE_COUNTRIES if c[3] == WEST_AFRICA_REGION]
MONITORED_CODES = [c[0] for c in REFERENCE_COUNTRIES if c[4]]

# Valeur générique posée par l'ancien seed : on peut l'affiner sans perte.
_GENERIC_REGIONS = {"", "Afrique"}


def find_country(country_model, code2: str, code3: str = ""):
    """Retrouve un pays par ISO-2 ou ISO-3, sans tenir compte de la casse ni des suppressions."""
    manager = getattr(country_model, "all_objects", country_model.objects)
    obj = manager.filter(code__iexact=code2).order_by("id").first()
    if obj is None and code3:
        obj = manager.filter(code3__iexact=code3).order_by("id").first()
    return obj


def sync_reference_countries(country_model) -> dict[str, int]:
    """Crée les pays manquants et complète les existants, sans doublon ni écrasement.

    Idempotent. Pour un pays existant, seuls les champs vides sont complétés
    (ISO-3, nom) et la région générique « Afrique » est précisée. Le niveau de
    risque, le nom saisi et le statut « surveillé » existants ne sont jamais modifiés.
    """
    manager = getattr(country_model, "all_objects", country_model.objects)
    created = updated = 0
    for code2, code3, name, region, monitored in REFERENCE_COUNTRIES:
        obj = find_country(country_model, code2, code3)
        if obj is None:
            country_model.objects.create(
                code=code2,
                code3=code3,
                name=name,
                region=region,
                is_monitored=monitored,
            )
            created += 1
            continue
        changed = []
        if not obj.code3 and not manager.filter(code3__iexact=code3).exclude(pk=obj.pk).exists():
            obj.code3 = code3
            changed.append("code3")
        if not obj.name:
            obj.name = name
            changed.append("name")
        if obj.region in _GENERIC_REGIONS and obj.region != region:
            obj.region = region
            changed.append("region")
        if changed:
            obj.save(update_fields=changed)
            updated += 1
    return {"created": created, "updated": updated}
