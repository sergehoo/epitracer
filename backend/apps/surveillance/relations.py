"""Mise en relation des voyageurs (contact-tracing).

Construit des « clusters » de voyageurs qui partagent un attribut sensible
pour l'épidémiologie :

  * vol / moyen de transport
  * numéro de téléphone (mobile ou urgence CI)
  * pays de provenance (Section 3 du formulaire INHP)
  * cas-contact déclaré (CompanionLink)
  * lieu de résidence à Abidjan (hôtel + commune + quartier)

Renvoie une structure prête pour une vue tree côté front.
"""
from __future__ import annotations

import re
from collections import defaultdict

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole
from apps.ebola.models import EbolaInvestigation
from apps.travelers.models import CompanionLink, Traveler, TravelHistoryEntry


# =========================================================================
#                                Helpers
# =========================================================================

_PHONE_RE = re.compile(r"[^0-9+]")


def _normalize_phone(raw: str) -> str:
    """Réduit un numéro à ses chiffres + éventuel +.

    « +225 07 12 34 56 78 » et « 0712345678 » sont alors comparables si
    on garde les 8 derniers chiffres. C'est ce qu'on indexe.
    """
    if not raw:
        return ""
    cleaned = _PHONE_RE.sub("", str(raw))
    return cleaned[-9:] if len(cleaned) >= 9 else cleaned


def _normalize_label(raw: str) -> str:
    if not raw:
        return ""
    return " ".join(str(raw).strip().split()).lower()


def _residence_key(t: Traveler) -> tuple[str, str]:
    """Construit une clé de regroupement « résidence Abidjan »."""
    parts = [
        _normalize_label(t.confinement_hotel),
        _normalize_label(t.confinement_neighborhood),
        _normalize_label(t.confinement_commune),
        _normalize_label(t.confinement_city),
    ]
    key = "|".join(p for p in parts if p)
    label = ", ".join(
        p for p in [
            t.confinement_hotel,
            t.confinement_neighborhood,
            t.confinement_commune,
            t.confinement_city,
        ] if p
    )
    return key, label


def _traveler_payload(t: Traveler, risk_index: dict[int, dict]) -> dict:
    risk = risk_index.get(t.id) or {}
    return {
        "public_id": t.public_id,
        "full_name": t.full_name,
        "status": t.current_health_status,
        "risk_level": risk.get("risk_level"),
        "risk_score": risk.get("risk_score"),
        "phone": t.phone_mobile or t.emergency_phone_ci,
        "flight": t.flight_or_voyage_number,
        "arrival_date": t.arrival_date.isoformat() if t.arrival_date else None,
        "entry_point": t.entry_point.name if t.entry_point_id else None,
        "nationality": t.nationality.code if t.nationality_id else None,
        "hotel": t.confinement_hotel,
        "commune": t.confinement_commune,
    }


# =========================================================================
#                                Endpoint
# =========================================================================
class TravelerRelationsView(APIView):
    """GET /api/v1/surveillance/relations/

    Query params :
      - type       : flight | phone | origin | companion | residence (filtre)
      - search     : limite aux clusters contenant un public_id / nom donné
      - min_size   : seuil minimal de membres par cluster (défaut 2)
      - days       : ne considérer que les arrivées des N derniers jours
    """

    permission_classes = [IsAuthenticated, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
        RoleCode.DISTRICT, RoleCode.ENTRY_POINT, RoleCode.OBSERVER,
    ]

    def get(self, request):
        type_filter = (request.query_params.get("type") or "").lower().strip()
        search = (request.query_params.get("search") or "").lower().strip()
        try:
            min_size = max(2, int(request.query_params.get("min_size", 2)))
        except (TypeError, ValueError):
            min_size = 2
        days = request.query_params.get("days")

        qs = (
            Traveler.objects
            .select_related("entry_point", "nationality")
            .order_by("-created_at")
        )
        if days:
            try:
                from datetime import timedelta
                from django.utils import timezone
                qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=int(days)))
            except (TypeError, ValueError):
                pass

        travelers = list(qs[:5000])
        if not travelers:
            return Response({
                "clusters": [],
                "stats": {"total_travelers": 0, "by_type": {}},
            })

        ids = [t.id for t in travelers]

        # Score / niveau de risque depuis la dernière enquête Ebola
        risk_index: dict[int, dict] = {}
        for inv in EbolaInvestigation.objects.filter(traveler_id__in=ids).order_by("-created_at").only(
            "traveler_id", "risk_level", "risk_score", "created_at",
        ):
            risk_index.setdefault(inv.traveler_id, {
                "risk_level": inv.risk_level,
                "risk_score": inv.risk_score,
            })

        # ------ 1) Flight clusters ------
        flight_groups: dict[str, list[Traveler]] = defaultdict(list)
        for t in travelers:
            if t.flight_or_voyage_number:
                flight_groups[t.flight_or_voyage_number.strip().upper()].append(t)

        # ------ 2) Phone clusters ------
        phone_groups: dict[str, dict] = defaultdict(lambda: {"members": [], "labels": set()})
        for t in travelers:
            for raw in [t.phone_mobile, t.emergency_phone_ci]:
                k = _normalize_phone(raw)
                if k:
                    phone_groups[k]["members"].append(t)
                    if raw:
                        phone_groups[k]["labels"].add(raw.strip())

        # ------ 3) Origin clusters (Section 3 - pays origin/transit/visited) ------
        origin_groups: dict[str, dict] = defaultdict(lambda: {"members": [], "label": ""})
        history_qs = (
            TravelHistoryEntry.objects
            .filter(traveler_id__in=ids)
            .select_related("country")
            .only("traveler_id", "country__code", "country__name", "role")
        )
        for h in history_qs:
            if not h.country_id:
                continue
            code = h.country.code
            if not code:
                continue
            origin_groups[code]["label"] = h.country.name or code
            # Indexer par traveler.id pour le merge plus loin
            origin_groups[code]["members"].append(h.traveler_id)

        # ------ 4) Companion clusters ------
        companion_pairs: list[tuple[int, int]] = list(
            CompanionLink.objects.filter(traveler_id__in=ids)
            .values_list("traveler_id", "companion_id")
        )
        # Construit des composantes connexes (union-find léger)
        parent: dict[int, int] = {}

        def find(x):
            while parent.get(x, x) != x:
                parent[x] = parent.get(parent.get(x, x), parent.get(x, x))
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for a, b in companion_pairs:
            parent.setdefault(a, a)
            parent.setdefault(b, b)
            union(a, b)
        companion_groups: dict[int, list[int]] = defaultdict(list)
        for node in parent:
            companion_groups[find(node)].append(node)

        # ------ 5) Résidence Abidjan ------
        residence_groups: dict[str, dict] = defaultdict(lambda: {"members": [], "label": ""})
        for t in travelers:
            # Restreint à Abidjan / district autonome quand possible
            if t.confinement_city and t.confinement_city.lower().startswith("abidjan"):
                key, label = _residence_key(t)
                if key:
                    residence_groups[key]["members"].append(t)
                    residence_groups[key]["label"] = label

        # ------ Assemblage : clusters[] ------
        id_to_traveler: dict[int, Traveler] = {t.id: t for t in travelers}
        clusters: list[dict] = []

        def make_cluster(cluster_type: str, key: str, label: str, members: list[Traveler]):
            seen = set()
            uniq = []
            for m in members:
                if m.id in seen:
                    continue
                seen.add(m.id)
                uniq.append(m)
            if len(uniq) < min_size:
                return None
            if search:
                hay = " ".join([
                    m.full_name.lower() + " " + (m.public_id or "").lower() for m in uniq
                ]) + " " + label.lower()
                if search not in hay:
                    return None
            return {
                "type": cluster_type,
                "key": f"{cluster_type}:{key}",
                "label": label or key,
                "size": len(uniq),
                "members": [_traveler_payload(m, risk_index) for m in uniq],
            }

        if not type_filter or type_filter == "flight":
            for flight, members in flight_groups.items():
                c = make_cluster("flight", flight, f"Vol {flight}", members)
                if c:
                    clusters.append(c)

        if not type_filter or type_filter == "phone":
            for k, payload in phone_groups.items():
                label_set = payload["labels"]
                label = "Téléphone " + (next(iter(label_set)) if label_set else k)
                c = make_cluster("phone", k, label, payload["members"])
                if c:
                    clusters.append(c)

        if not type_filter or type_filter == "origin":
            for code, payload in origin_groups.items():
                members = [id_to_traveler[i] for i in payload["members"] if i in id_to_traveler]
                c = make_cluster("origin", code, f"Provenance — {payload['label']}", members)
                if c:
                    clusters.append(c)

        if not type_filter or type_filter == "companion":
            for root, member_ids in companion_groups.items():
                members = [id_to_traveler[i] for i in member_ids if i in id_to_traveler]
                if not members:
                    continue
                head = members[0].full_name if members else "Groupe"
                c = make_cluster("companion", str(root), f"Cas-contact — autour de {head}", members)
                if c:
                    clusters.append(c)

        if not type_filter or type_filter == "residence":
            for key, payload in residence_groups.items():
                c = make_cluster(
                    "residence", key,
                    f"Résidence Abidjan — {payload['label']}",
                    payload["members"],
                )
                if c:
                    clusters.append(c)

        # Tri : taille décroissante, puis label
        clusters.sort(key=lambda c: (-c["size"], c["label"]))

        # Stats globales
        by_type: dict[str, dict[str, int]] = {}
        for c in clusters:
            t = c["type"]
            agg = by_type.setdefault(t, {"clusters": 0, "members": 0})
            agg["clusters"] += 1
            agg["members"] += c["size"]

        return Response({
            "clusters": clusters[:200],  # cap à 200 clusters pour la perf front
            "stats": {
                "total_travelers": len(travelers),
                "by_type": by_type,
                "total_clusters": len(clusters),
            },
            "filters": {
                "type": type_filter or None,
                "search": search or None,
                "min_size": min_size,
                "days": int(days) if days and str(days).isdigit() else None,
            },
        })
