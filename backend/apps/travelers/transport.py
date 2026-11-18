"""Cohérence « moyen de transport » ↔ catégorie du point d'entrée.

Règle unique appliquée au formulaire public, à l'API des agents et à l'admin.
Le formulaire web en garde une copie (frontend/lib/entryPoints.ts).
"""
from __future__ import annotations

from apps.geo.models import EntryPoint, EntryPointType

from .models import TransportMode

# Catégories de points d'entrée admises pour chaque moyen de transport.
# « Autre » (ou transport non renseigné) : aucune restriction.
ENTRY_TYPES_BY_TRANSPORT: dict[str, frozenset[str]] = {
    TransportMode.PLANE: frozenset({EntryPointType.AIRPORT}),
    TransportMode.BOAT: frozenset({EntryPointType.SEAPORT, EntryPointType.RIVER}),
    TransportMode.CAR: frozenset({EntryPointType.LAND}),
    TransportMode.BUS: frozenset({EntryPointType.LAND}),
    TransportMode.FOOT: frozenset({EntryPointType.LAND}),
    TransportMode.TRAIN: frozenset({EntryPointType.RAIL}),
}


def entry_point_error(
    transport_mode: str | None, entry_point: EntryPoint | None, *, check_active: bool = True,
) -> str | None:
    """Motif de refus du point d'entrée pour ce transport, ou None s'il est admis."""
    if entry_point is None:
        return None
    if check_active and not entry_point.is_active:
        return f"Le point d'entrée « {entry_point.name} » n'est plus ouvert."
    allowed = ENTRY_TYPES_BY_TRANSPORT.get(transport_mode or "")
    if allowed and entry_point.type not in allowed:
        transport = TransportMode(transport_mode).label
        return (
            f"Le point d'entrée « {entry_point.name} » ({entry_point.get_type_display()}) "
            f"n'est pas compatible avec le moyen de transport « {transport} »."
        )
    return None
