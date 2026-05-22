"""Rattrapage one-shot pour les alertes existantes.

Ce que la commande fait :
  1. Pour chaque HealthAlert dont disease ou entry_point est null,
     retrouve le voyageur cible et renseigne les champs depuis sa
     quarantaine la plus récente + son point d'arrivée.
  2. Dédoublonne les alertes ouvertes : si plusieurs alertes ont la
     même cible (target_ct + target_id) ET la même sévérité ET ont été
     créées dans une fenêtre de 4h, on garde la PLUS RÉCENTE et on
     marque les autres comme DISMISSED avec mention "agrégée dans <id>".
     Le compteur de répétitions est inscrit dans metadata.duplicate_count
     de l'alerte conservée.

Usage :
    python manage.py fix_alerts_metadata             # exécute pour de vrai
    python manage.py fix_alerts_metadata --dry-run   # affiche sans modifier
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


DEDUP_WINDOW = timedelta(hours=4)


class Command(BaseCommand):
    help = "Rattrape les alertes existantes : renseigne disease/entry_point + dédoublonne."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Affiche ce qui serait fait sans toucher à la DB.",
        )

    def handle(self, *args, **options):
        from apps.surveillance.models import HealthAlert
        from apps.travelers.models import Traveler

        dry = options.get("dry_run", False)

        # =====================================================================
        # 1) Renseigner disease + entry_point manquants
        # =====================================================================
        self.stdout.write(self.style.MIGRATE_HEADING(
            "1) Inférence disease / entry_point sur les alertes incomplètes"
        ))
        trv_ct = ContentType.objects.get_for_model(Traveler)
        missing_qs = HealthAlert.objects.filter(target_ct=trv_ct).filter(
            disease__isnull=True
        ) | HealthAlert.objects.filter(target_ct=trv_ct, entry_point__isnull=True)
        missing_qs = missing_qs.distinct()

        n_filled = 0
        traveler_cache: dict[str, Traveler | None] = {}

        for alert in missing_qs:
            if not alert.target_id:
                continue
            # target_id peut être un str de PK ou un str de public_id selon les
            # versions du code. On essaie les 2 cas.
            traveler = traveler_cache.get(alert.target_id)
            if traveler is None and alert.target_id not in traveler_cache:
                traveler = (
                    Traveler.objects.filter(pk=alert.target_id).first()
                    if alert.target_id.isdigit()
                    else None
                )
                if traveler is None:
                    traveler = Traveler.objects.filter(public_id=alert.target_id).first()
                traveler_cache[alert.target_id] = traveler

            if traveler is None:
                self.stdout.write(self.style.WARNING(
                    f"  - alerte {alert.id} : voyageur introuvable (target_id={alert.target_id})"
                ))
                continue

            new_disease = alert.disease
            new_ep = alert.entry_point
            if new_disease is None:
                qr = (
                    traveler.quarantines.order_by("-started_on").first()
                    if hasattr(traveler, "quarantines") else None
                )
                if qr and qr.disease_id:
                    new_disease = qr.disease
            if new_ep is None and getattr(traveler, "entry_point_id", None):
                new_ep = traveler.entry_point

            if new_disease == alert.disease and new_ep == alert.entry_point:
                continue  # rien à mettre à jour

            self.stdout.write(
                f"  - alerte {alert.id} ({alert.severity}/{alert.status}) "
                f"→ disease={new_disease.code if new_disease else '—'} "
                f"entry_point={new_ep.name if new_ep else '—'}"
            )
            if not dry:
                alert.disease = new_disease
                alert.entry_point = new_ep
                alert.save(update_fields=["disease", "entry_point", "updated_at"])
            n_filled += 1

        self.stdout.write(self.style.SUCCESS(
            f"  → {n_filled} alertes complétées."
        ))

        # =====================================================================
        # 2) Dédoublonnage : grouper par (target, severity) sur 4h glissantes
        # =====================================================================
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING(
            "2) Dédoublonnage des alertes ouvertes (fenêtre 4h)"
        ))

        open_alerts = (
            HealthAlert.objects
            .filter(status__in=["open", "ack", "investigating", "OPEN", "ACK", "INVESTIGATING"])
            .filter(target_ct=trv_ct)
            .exclude(target_id__isnull=True)
            .exclude(target_id="")
            .order_by("target_id", "severity", "created_at")
        )

        # Grouper par (target_id, severity)
        groups: dict[tuple[str, str], list[HealthAlert]] = defaultdict(list)
        for a in open_alerts:
            groups[(a.target_id, a.severity)].append(a)

        n_dismissed = 0
        n_groups = 0
        for (target_id, severity), alerts in groups.items():
            if len(alerts) < 2:
                continue

            # On forme des sous-groupes en fenêtre glissante 4h
            alerts.sort(key=lambda x: x.created_at)
            current_window: list[HealthAlert] = [alerts[0]]
            window_start = alerts[0].created_at

            def _flush(window: list[HealthAlert]):
                """Garde le + récent du window, dismiss les autres."""
                nonlocal n_dismissed, n_groups
                if len(window) < 2:
                    return
                # Trier par date pour avoir la + récente en dernier
                window.sort(key=lambda x: x.created_at)
                keeper = window[-1]
                obsoletes = window[:-1]
                n_groups += 1
                self.stdout.write(
                    f"  - cluster ({severity}, target_id={target_id}) : "
                    f"keeper={keeper.id} ({keeper.created_at:%H:%M}), "
                    f"dismiss={[a.id for a in obsoletes]}"
                )
                if not dry:
                    # Met à jour le compteur sur l'alerte conservée
                    meta = keeper.metadata or {}
                    meta["duplicate_count"] = (
                        int(meta.get("duplicate_count") or 0) + len(obsoletes)
                    )
                    repeats = list(meta.get("repeat_reasons") or [])
                    for o in obsoletes:
                        repeats.append({
                            "at": o.created_at.isoformat(),
                            "reasons": (o.description or "").split("\n"),
                            "from_alert_id": o.id,
                        })
                    meta["repeat_reasons"] = repeats[-20:]
                    meta["merged_from"] = (meta.get("merged_from") or []) + [a.id for a in obsoletes]
                    keeper.metadata = meta
                    keeper.save(update_fields=["metadata", "updated_at"])

                    # Marque les obsolètes en DISMISSED
                    HealthAlert.objects.filter(id__in=[a.id for a in obsoletes]).update(
                        status="DISMISSED",
                        metadata=keeper.metadata,  # référence
                    )
                n_dismissed += len(obsoletes)

            for a in alerts[1:]:
                if a.created_at - window_start <= DEDUP_WINDOW:
                    current_window.append(a)
                else:
                    _flush(current_window)
                    current_window = [a]
                    window_start = a.created_at
            _flush(current_window)

        self.stdout.write(self.style.SUCCESS(
            f"  → {n_groups} clusters traités, {n_dismissed} alertes obsolètes marquées DISMISSED."
        ))

        # =====================================================================
        if dry:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "Mode --dry-run : aucune modification appliquée."
            ))
        else:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Rattrapage terminé."))
