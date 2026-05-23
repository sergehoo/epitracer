"""Normalise les champs `status` et `severity` des HealthAlert existantes.

Historique : le service de création d'alertes écrivait à un moment les
valeurs en MAJUSCULE (`status="OPEN"`, `severity="CRITICAL"`), alors que
les choices du modèle (`AlertStatus`, `AlertSeverity`) sont définies en
MINUSCULE.

Ce mismatch fait que :
  - Les filtres `status=OPEN` du backend ne matchent pas
    (les filtres DRF utilisent exactement la valeur stockée)
  - Les boutons d'action admin envoient des PATCH avec status majuscule,
    rejetés par la validation des choices DRF → 400 "Erreur de requête."

La commande lit toutes les alertes et normalise les valeurs.

Usage :
    python manage.py normalize_alert_case
    python manage.py normalize_alert_case --dry-run
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction


STATUS_MAP = {
    "OPEN": "open",
    "ACK": "ack",
    "INVESTIGATING": "investigating",
    "RESOLVED": "resolved",
    "DISMISSED": "dismissed",
}

SEVERITY_MAP = {
    "INFO": "info",
    "LOW": "low",
    "MEDIUM": "medium",
    "HIGH": "high",
    "CRITICAL": "critical",
}


class Command(BaseCommand):
    help = "Normalise (majuscule → minuscule) les status et severity des HealthAlert existantes."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        from apps.surveillance.models import HealthAlert

        dry = opts.get("dry_run", False)
        n_status = 0
        n_severity = 0

        with transaction.atomic():
            for upper, lower in STATUS_MAP.items():
                qs = HealthAlert.objects.filter(status=upper)
                count = qs.count()
                if count:
                    self.stdout.write(f"  status: {upper} → {lower}  : {count} alertes")
                    if not dry:
                        qs.update(status=lower)
                    n_status += count

            for upper, lower in SEVERITY_MAP.items():
                qs = HealthAlert.objects.filter(severity=upper)
                count = qs.count()
                if count:
                    self.stdout.write(f"  severity: {upper} → {lower} : {count} alertes")
                    if not dry:
                        qs.update(severity=lower)
                    n_severity += count

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Normalisation terminée : {n_status} status corrigés, {n_severity} severity corrigés."
        ))
        if dry:
            self.stdout.write(self.style.WARNING("Mode --dry-run : aucune écriture en base."))
