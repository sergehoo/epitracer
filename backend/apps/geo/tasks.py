"""Tâches Celery du référentiel géographique."""

from __future__ import annotations

from celery import shared_task

from .services import refresh_all_country_risks


@shared_task(name="geo.refresh_country_risk_levels")
def refresh_country_risk_levels():
    """Recalcule les niveaux pays (prise d'effet / fin de validité des évaluations)."""
    return {"countries_refreshed": refresh_all_country_risks()}
