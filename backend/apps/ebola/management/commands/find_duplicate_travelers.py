"""Repérage des fiches voyageurs en double (LECTURE SEULE).

Regroupe les fiches non supprimées partageant :
  - « pièce »    : même n° de pièce d'identité (espaces, tirets, points ignorés)
                   et même date d'arrivée ;
  - « identité » : même nom, même prénom, même n° de vol et même date
                   d'arrivée (n° de pièce saisi différemment).

L'écart entre deux fiches d'un groupe aide à en trouver l'origine : quelques
secondes à deux minutes → retry automatique du formulaire (timeout, coupure
réseau, 502/504) ; davantage → resoumission manuelle du brouillon.

Rien n'est fusionné, modifié ni supprimé (données de santé) : la décision
revient à un agent habilité. En PostgreSQL, la commande s'exécute dans une
transaction déclarée READ ONLY.

    python manage.py find_duplicate_travelers [--since AAAA-MM-JJ] [--csv]
"""

from __future__ import annotations

import csv
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import Count, Q
from django.db.models.functions import Trim, Upper

from apps.ebola.registration_dedup import normalized_document_expr
from apps.travelers.models import Traveler

_ACTIVE_FOLLOWUP = ["active", "extended", "ACTIVE", "EXTENDED"]
_CRITERIA = {
    "pièce": ("doc_key", "arrival_date"),
    "identité": ("last_key", "first_key", "flight_key", "arrival_date"),
}


class Command(BaseCommand):
    help = (
        "Liste les fiches voyageurs en double (même pièce ou même identité + vol, "
        "même arrivée). Lecture seule."
    )

    def add_arguments(self, parser):
        parser.add_argument("--since", help="Date d'arrivée minimale (AAAA-MM-JJ).")
        parser.add_argument("--csv", action="store_true", help="Sortie CSV (une ligne par fiche).")

    def handle(self, *args, **opts):
        since = None
        if opts.get("since"):
            try:
                since = date.fromisoformat(opts["since"])
            except ValueError as exc:
                raise CommandError("--since attend une date AAAA-MM-JJ.") from exc

        # Dans une transaction englobante (tests), SET TRANSACTION n'est plus permis.
        outer = connection.in_atomic_block
        with transaction.atomic():
            if connection.vendor == "postgresql" and not outer:
                with connection.cursor() as cursor:
                    cursor.execute("SET TRANSACTION READ ONLY")
            groups = _duplicate_groups(since)

        if opts.get("csv"):
            self._write_csv(groups)
        else:
            self._write_text(groups)

    def _write_text(self, groups):
        extra = sum(len(members) - 1 for _, _, members in groups)
        followed = sum(1 for _, _, members in groups for t in members[1:] if t.active_followups)
        for criterion, label, members in groups:
            self.stdout.write(f"\n[{criterion}] {label} — {len(members)} fiches")
            previous = None
            for t in members:
                gap = "" if previous is None else f"+{_seconds(t.created_at - previous)}"
                previous = t.created_at
                self.stdout.write(
                    f"  {t.public_id:<16} créée {t.created_at:%Y-%m-%d %H:%M:%S} {gap:>9}  "
                    f"vol {t.flight_or_voyage_number or '—':<8} tél {_mask(t.phone_mobile):<8} "
                    f"pass {t.passes}  suivis actifs {t.active_followups}  {t.full_name}"
                )
        self.stdout.write(
            f"\n{len(groups)} groupe(s), {extra} fiche(s) en surnombre "
            f"dont {followed} avec un suivi actif (rappels SMS). Aucune donnée modifiée."
        )

    def _write_csv(self, groups):
        writer = csv.writer(self.stdout)
        writer.writerow(
            [
                "critere",
                "groupe",
                "public_id",
                "created_at",
                "ecart_s",
                "arrival_date",
                "vol",
                "telephone_masque",
                "pass",
                "suivis_actifs",
            ]
        )
        for criterion, label, members in groups:
            previous = None
            for t in members:
                gap = "" if previous is None else _seconds(t.created_at - previous)
                previous = t.created_at
                writer.writerow(
                    [
                        criterion,
                        label,
                        t.public_id,
                        t.created_at.isoformat(),
                        gap,
                        t.arrival_date,
                        t.flight_or_voyage_number,
                        _mask(t.phone_mobile),
                        t.passes,
                        t.active_followups,
                    ]
                )


def _duplicate_groups(since: date | None) -> list[tuple[str, str, list[Traveler]]]:
    base = Traveler.objects.filter(arrival_date__isnull=False).annotate(
        doc_key=normalized_document_expr(),
        last_key=Upper(Trim("last_name")),
        first_key=Upper(Trim("first_name")),
        flight_key=Upper(Trim("flight_or_voyage_number")),
    )
    if since:
        base = base.filter(arrival_date__gte=since)

    groups, seen = [], set()
    for criterion, fields in _CRITERIA.items():
        non_empty = base
        for f in fields:
            if f != "arrival_date":
                non_empty = non_empty.exclude(**{f: ""})
        keys = (
            non_empty.values(*fields)
            .annotate(n=Count("id"))
            .filter(n__gt=1)
            .order_by("-n", *fields)
        )
        for key in keys:
            members = list(
                non_empty.filter(**{f: key[f] for f in fields})
                .annotate(
                    passes=Count("health_passes", distinct=True),
                    active_followups=Count(
                        "quarantines",
                        filter=Q(quarantines__status__in=_ACTIVE_FOLLOWUP),
                        distinct=True,
                    ),
                )
                .order_by("created_at")
            )
            ids = frozenset(t.pk for t in members)
            if ids in seen:  # même groupe déjà signalé par le critère « pièce »
                continue
            seen.add(ids)
            label = " · ".join(str(key[f]) for f in fields)
            groups.append((criterion, label, members))
    return groups


def _seconds(delta) -> int:
    return int(delta.total_seconds())


def _mask(phone: str) -> str:
    digits = "".join(c for c in phone or "" if c.isdigit())
    return f"…{digits[-4:]}" if digits else "—"
