"""Rattrape les voyageurs existants qui n'ont pas de QuarantineRecord.

Suite à un bug historique, `open_quarantine_for_investigation` n'était
appelé que pour les enquêtes high/critical. Tous les autres voyageurs
n'avaient donc pas de dossier de suivi 21j → ils n'apparaissaient pas
dans `/dashboard/suivi-voyageurs` ni dans le centre de check-ins.

Cette commande crée un QuarantineRecord rétroactif pour chaque voyageur
ayant une EbolaInvestigation et n'ayant aucune quarantaine. Idempotente.

Usage :
    python manage.py backfill_quarantines
    python manage.py backfill_quarantines --dry-run
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.diseases.models import Disease
from apps.ebola.models import EbolaInvestigation
from apps.quarantine.models import QuarantineRecord, QuarantineStatus


class Command(BaseCommand):
    help = "Crée des QuarantineRecord rétroactifs pour les voyageurs sans dossier de suivi."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        ebola = Disease.objects.filter(code__iexact="EBOLA").first()
        if not ebola:
            self.stdout.write(self.style.ERROR("Maladie EBOLA introuvable. Lancez seed_reference_data d'abord."))
            return

        days = ebola.quarantine_days or 21
        created = 0
        skipped = 0
        today = timezone.now().date()

        investigations = EbolaInvestigation.objects.select_related("traveler").all()
        for inv in investigations:
            traveler = inv.traveler
            if not traveler:
                skipped += 1
                continue
            existing = QuarantineRecord.objects.filter(
                traveler=traveler,
                disease=ebola,
            ).first()
            if existing:
                skipped += 1
                continue

            started = (
                inv.surveillance_start
                or (traveler.arrival_date if traveler.arrival_date else None)
                or inv.created_at.date()
            )
            ended = started + timedelta(days=days)
            status = (
                QuarantineStatus.ACTIVE if ended >= today else QuarantineStatus.COMPLETED
            )

            if dry:
                self.stdout.write(
                    f"[DRY] Would create quarantine for {traveler.public_id} "
                    f"(started={started}, end={ended}, status={status})"
                )
                created += 1
                continue

            QuarantineRecord.objects.create(
                traveler=traveler,
                disease=ebola,
                investigation_ref=getattr(inv, "case_number", ""),
                started_on=started,
                expected_end_on=ended,
                actual_end_on=ended if status == QuarantineStatus.COMPLETED else None,
                address=traveler.confinement_address or "",
                location=traveler.confinement_location,
                status=status,
            )
            created += 1

        msg = f"Rattrapage terminé : {created} créés, {skipped} ignorés (déjà OK)."
        if dry:
            msg = "[DRY-RUN] " + msg
        self.stdout.write(self.style.SUCCESS(msg))
