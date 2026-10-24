"""Colonnes « itinéraire et séjour » des exports voyageurs (CSV, Excel, PDF, hebdomadaire).

Source unique pour les trois formats et pour le rapport automatisé : chaque
valeur est calculée ici, une fois, à partir des champs existants — aucune
valeur n'est inventée ; une donnée absente vaut « Non renseigné ».

  Date d'enregistrement          Traveler.created_at (heure locale)
  Pays de provenance             étape d'itinéraire « provenance »
  Pays de séjour récent          étapes « autre pays visité » hors destination, plus récente d'abord
  Ville ou province de provenance  ville / province de l'étape « provenance »
  Pays de destination            pays du point d'entrée déclaré
  Ville de destination           ville de résidence déclarée en Côte d'Ivoire
  Durée du séjour en CI (jours)  départ − arrivée, si les deux dates sont connues

Date de départ : celle déclarée dans le formulaire (« date de départ prévue
de Côte d'Ivoire ») ; à défaut, une étape d'itinéraire dans le pays de
destination portant une date de départ (saisie agent, par exemple).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from django.db.models import Prefetch
from django.utils import timezone

NOT_PROVIDED = "Non renseigné"

ITINERARY_HEADERS = [
    "Date d'enregistrement",
    "Pays de provenance",
    "Pays de séjour récent",
    "Ville ou province de provenance",
    "Pays de destination",
    "Ville de destination",
    "Durée du séjour en Côte d'Ivoire (jours)",
]

# Valeurs pouvant déclencher une formule à l'ouverture dans un tableur (CSV injection).
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _text(value: str | None) -> str:
    """Texte libre saisi par le voyageur : « Non renseigné » si vide, formule neutralisée."""
    value = (value or "").strip()
    if not value:
        return NOT_PROVIDED
    return f"'{value}" if value.startswith(_FORMULA_PREFIXES) else value


def stay_duration_days(arrival: date | None, departure: date | None) -> int | None:
    """Nombre de jours entre l'arrivée et le départ (0 si même jour).

    None si une date manque ou si le départ précède l'arrivée (donnée incohérente).
    """
    if not arrival or not departure or departure < arrival:
        return None
    return (departure - arrival).days


def with_itinerary(queryset, prefix: str = ""):
    """Précharge ce que les colonnes lisent (évite une requête par voyageur).

    `prefix` : chemin vers le voyageur depuis le modèle exporté (ex. "traveler__").
    """
    from apps.travelers.models import TravelHistoryEntry

    return queryset.select_related(f"{prefix}entry_point__country").prefetch_related(
        Prefetch(
            f"{prefix}travel_history",
            queryset=TravelHistoryEntry.objects.select_related("country"),
        )
    )


@dataclass
class ItineraryInfo:
    """Valeurs structurées (agrégation) ; `row()` les met en forme pour les exports."""

    registered_on: date | None = None
    origin_country: str | None = None
    recent_stay_countries: list[str] = field(default_factory=list)
    origin_place: str | None = None
    destination_country: str | None = None
    destination_city: str | None = None
    stay_days: int | None = None

    def row(self) -> list:
        return [
            self.registered_on.strftime("%d/%m/%Y") if self.registered_on else NOT_PROVIDED,
            self.origin_country or NOT_PROVIDED,
            ", ".join(self.recent_stay_countries) or NOT_PROVIDED,
            _text(self.origin_place),
            self.destination_country or NOT_PROVIDED,
            _text(self.destination_city),
            self.stay_days if self.stay_days is not None else NOT_PROVIDED,
        ]


def _recency(entry) -> date:
    return entry.departure_date or entry.arrival_date or date.min


def itinerary_info(traveler) -> ItineraryInfo:
    """Calcule les 7 informations d'un voyageur (itinéraire préchargé de préférence)."""
    if traveler is None:
        return ItineraryInfo()
    entries = list(traveler.travel_history.all())
    destination = None
    if traveler.entry_point_id and traveler.entry_point.country_id:
        destination = traveler.entry_point.country
    destination_id = destination.id if destination is not None else None

    origins = sorted((e for e in entries if e.role == "origin"), key=_recency, reverse=True)
    origin = origins[0] if origins else None
    # Séjours récents : pays visités AVANT l'arrivée (hors pays de destination, hors transit)
    visited = sorted(
        (e for e in entries if e.role == "visited" and e.country_id != destination_id),
        key=_recency,
        reverse=True,
    )

    # Séjour en Côte d'Ivoire : arrivée déclarée + étape d'itinéraire dans le
    # pays de destination portant une date de départ (si elle existe).
    stay_days = None
    if traveler.planned_departure_date:
        stay_days = stay_duration_days(traveler.arrival_date, traveler.planned_departure_date)
    elif destination is not None:
        stays = sorted(
            (e for e in entries if e.country_id == destination.id and e.departure_date),
            key=_recency,
            reverse=True,
        )
        if stays:
            stay = stays[0]
            stay_days = stay_duration_days(
                traveler.arrival_date or stay.arrival_date, stay.departure_date
            )

    origin_place = None
    if origin is not None:
        parts = [p.strip() for p in (origin.city, origin.province) if p and p.strip()]
        origin_place = ", ".join(dict.fromkeys(parts)) or None

    return ItineraryInfo(
        registered_on=(
            timezone.localtime(traveler.created_at).date() if traveler.created_at else None
        ),
        origin_country=origin.country.name if origin is not None else None,
        recent_stay_countries=list(dict.fromkeys(e.country.name for e in visited)),
        origin_place=origin_place,
        destination_country=destination.name if destination is not None else None,
        destination_city=(traveler.confinement_city or "").strip() or None,
        stay_days=stay_days,
    )


def itinerary_row(traveler) -> list:
    """Les 7 cellules, dans l'ordre de ITINERARY_HEADERS, identiques dans tous les formats."""
    return itinerary_info(traveler).row()
