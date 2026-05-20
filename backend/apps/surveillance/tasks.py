"""Tâches Celery périodiques pour la surveillance épidémiologique."""
from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.diseases.models import Disease
from apps.ebola.models import EbolaInvestigation
from apps.ebola.services import apply_risk_outcome

from .services import trigger_alert


@shared_task(name="surveillance.daily_risk_refresh")
def daily_risk_refresh():
    """Recalcule chaque jour les scores des enquêtes actives."""
    qs = EbolaInvestigation.objects.exclude(status__in=["closed", "recovered", "deceased"])
    for inv in qs.iterator(chunk_size=500):
        apply_risk_outcome(inv)
    return {"refreshed": qs.count()}


@shared_task(name="surveillance.cluster_detection")
def cluster_detection(threshold: int = 5, hours: int = 24):
    """Détecte un cluster (>= threshold cas suspects/probables sur la même fenêtre)."""
    since = timezone.now() - timedelta(hours=hours)
    qs = (
        EbolaInvestigation.objects
        .filter(created_at__gte=since, risk_level__in=["high", "critical"])
        .values("entry_point").order_by()
    )
    counts: dict = {}
    for row in qs:
        counts[row["entry_point"]] = counts.get(row["entry_point"], 0) + 1

    for ep_id, count in counts.items():
        if count >= threshold:
            trigger_alert(
                code="ebola_cluster",
                title=f"Cluster Ebola détecté au point d'entrée #{ep_id}",
                description=f"{count} cas à haut risque détectés en {hours}h.",
                severity="high",
                disease=Disease.objects.filter(code="EBOLA").first(),
                metadata={"entry_point_id": ep_id, "count": count, "window_hours": hours},
            )
    return {"clusters_evaluated": len(counts)}
