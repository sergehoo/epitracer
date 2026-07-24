"""Agrégateur de rapport hebdomadaire — fonction pure.

Prend une période (start, end) en datetime **timezone-aware** et retourne
un dict avec TOUTES les KPI du rapport. Aucun effet de bord : ne persiste
rien, n'envoie rien.

Invariants respectés (voir intent-compile Phase 1) :
  #1 Fuseau : toutes les périodes attendues en Africa/Abidjan (le caller
     doit convertir). L'agrégateur trust le tz de la période fournie.
  #3 Pas de PII : uniquement des compteurs, jamais de valeurs individuelles
     (noms, téléphones, IDs voyageur).
  #5 Perf : agrégations SQL (Count + values). Aucun `for x in Model.objects.all()`.
  #10 Défensif : chaque section wrappée en try/except pour survivre à une
      évolution de schéma d'une app dépendante.

Utilisation :
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("Africa/Abidjan")
    start = datetime(2026, 6, 8, 0, 0, tzinfo=tz)
    end   = datetime(2026, 6, 14, 23, 59, 59, tzinfo=tz)
    agg = aggregate_weekly(start, end)
    # agg["travelers"]["registered"] == 1245 par exemple
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from django.db.models import Count, Q
from django.utils import timezone as django_tz

logger = logging.getLogger("epidemitracker.reports.aggregator")


# ---------------------------------------------------------------------------
# Constantes de mapping — externalisées pour être testables
# ---------------------------------------------------------------------------

# Mapping niveau de risque : les codes réels en DB peuvent varier selon
# les migrations historiques. Cette map les regroupe en 4 buckets canoniques.
RISK_LEVEL_BUCKETS = {
    "critical": {"critical", "very_high", "urgent"},
    "high": {"high", "elevated"},
    "moderate": {"moderate", "medium", "med"},
    "normal": {"low", "normal", "none", ""},
}

# Mapping classification épidémiologique (CaseClassificationCode)
CLASSIFICATION_BUCKETS = {
    "suspect": {"suspect"},
    "probable": {"probable"},
    "confirmed": {"confirmed"},
    "discarded": {"not_suspect", "discarded", "excluded", "ruled_out"},
}


# ---------------------------------------------------------------------------
# Structure de retour (typé pour aide IDE)
# ---------------------------------------------------------------------------
@dataclass
class WeekPeriod:
    """Descripteur d'une semaine ISO 8601."""
    start: datetime
    end: datetime

    @property
    def iso_year(self) -> int:
        return self.start.isocalendar()[0]

    @property
    def iso_week(self) -> int:
        return self.start.isocalendar()[1]

    @property
    def label(self) -> str:
        return f"S{self.iso_week:02d} ({self.start:%d %b} → {self.end:%d %b %Y})"

    def to_dict(self) -> dict:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "iso_year": self.iso_year,
            "iso_week": self.iso_week,
            "label": self.label,
        }


# ---------------------------------------------------------------------------
# Helpers de comptage — defensifs (retournent 0 + not_available si le modèle manque)
# ---------------------------------------------------------------------------
def _safe_count(callback, default: int = 0) -> int:
    """Exécute un callback de comptage, retourne 0 si le modèle n'existe pas."""
    try:
        return int(callback() or 0)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Agrégation partielle : %s", exc)
        return default


def _pct(part: int, total: int) -> float:
    """Pourcentage arrondi à 1 décimale."""
    if not total:
        return 0.0
    return round((part / total) * 100, 1)


def _delta_pct(current: int, previous: int) -> float:
    """Évolution % : (curr - prev) / prev * 100, arrondi 1 décimale.

    Retourne 0.0 si prev == 0 pour éviter la division par zéro (le rapport
    doit indiquer 'N/A' ou 'nouveau' dans ce cas via le renderer)."""
    if not previous:
        return 0.0 if not current else 100.0
    return round(((current - previous) / previous) * 100, 1)


# ---------------------------------------------------------------------------
# Sections d'agrégation — 1 fonction par domaine
# ---------------------------------------------------------------------------

def _count_travelers(period: WeekPeriod) -> dict:
    """Voyageurs enregistrés + en suivi actif."""
    from apps.travelers.models import Traveler

    registered = _safe_count(lambda: Traveler.objects.filter(
        created_at__gte=period.start, created_at__lte=period.end,
    ).count())

    # En suivi actif = quarantine en cours à la fin de la période
    active_followup = 0
    try:
        from apps.quarantine.models import QuarantineRecord, QuarantineStatus
        active_followup = QuarantineRecord.objects.filter(
            status=QuarantineStatus.ONGOING,
            created_at__lte=period.end,
        ).count()
    except Exception:  # noqa: BLE001
        pass

    return {"registered": registered, "active_followup": active_followup}


def _count_followups(period: WeekPeriod) -> dict:
    """Nouveaux suivis + suivis terminés dans la période."""
    result = {"new": 0, "completed": 0}
    try:
        from apps.quarantine.models import QuarantineRecord, QuarantineStatus
        result["new"] = QuarantineRecord.objects.filter(
            created_at__gte=period.start, created_at__lte=period.end,
        ).count()
        result["completed"] = QuarantineRecord.objects.filter(
            status=QuarantineStatus.COMPLETED,
            updated_at__gte=period.start, updated_at__lte=period.end,
        ).count()
    except Exception as exc:  # noqa: BLE001
        logger.debug("QuarantineRecord agg failed: %s", exc)
    return result


def _count_checkins(period: WeekPeriod) -> dict:
    """Check-ins reçus vs manqués dans la période."""
    result = {"received": 0, "missed": 0}
    try:
        from apps.quarantine.models import DailyCheck, DailyCheckStatus
        base = DailyCheck.objects.filter(
            check_date__gte=period.start.date(),
            check_date__lte=period.end.date(),
        )
        result["received"] = base.filter(status=DailyCheckStatus.COMPLETED).count()
        result["missed"] = base.filter(status=DailyCheckStatus.MISSED).count()
    except Exception as exc:  # noqa: BLE001
        logger.debug("DailyCheck agg failed: %s", exc)
    return result


def _count_assistance(period: WeekPeriod) -> dict:
    """Demandes d'assistance dans la période."""
    result = {"requests": 0}
    try:
        from apps.medical.models import MedicalSymptomReport
        result["requests"] = MedicalSymptomReport.objects.filter(
            created_at__gte=period.start, created_at__lte=period.end,
        ).count()
    except Exception:  # noqa: BLE001
        pass
    return result


def _count_alerts(period: WeekPeriod) -> dict:
    """Alertes sanitaires — créées, ouvertes, résolues."""
    result = {"created": 0, "open": 0, "resolved": 0}
    try:
        from apps.surveillance.models import HealthAlert, AlertStatus
        base = HealthAlert.objects.filter(
            created_at__gte=period.start, created_at__lte=period.end,
        )
        result["created"] = base.count()
        # Ouvertes/résolues sur la période même (pas seulement créées la semaine)
        result["open"] = HealthAlert.objects.filter(
            status=AlertStatus.OPEN,
        ).count()
        result["resolved"] = base.filter(status=AlertStatus.RESOLVED).count()
    except Exception:  # noqa: BLE001
        pass
    return result


def _count_risk_levels(period: WeekPeriod) -> dict:
    """Répartition par niveau de risque des voyageurs enregistrés
    dans la période (source : Traveler.current_health_status OU
    HealthPass.risk_level selon disponibilité)."""
    from apps.travelers.models import Traveler

    # Comptage par current_health_status
    by_status = {}
    try:
        rows = (
            Traveler.objects.filter(
                created_at__gte=period.start, created_at__lte=period.end,
            )
            .values("current_health_status")
            .annotate(c=Count("id"))
        )
        for row in rows:
            key = (row["current_health_status"] or "").lower().strip()
            by_status[key] = row["c"]
    except Exception:  # noqa: BLE001
        pass

    # Regroupement en 4 buckets canoniques
    buckets = {name: 0 for name in RISK_LEVEL_BUCKETS}
    for status, cnt in by_status.items():
        for bucket_name, codes in RISK_LEVEL_BUCKETS.items():
            if status in codes:
                buckets[bucket_name] += cnt
                break
        else:
            # Status inconnu → catégorie "normal" par défaut
            buckets["normal"] += cnt

    total = sum(buckets.values())
    return {
        "critical": {"count": buckets["critical"], "pct": _pct(buckets["critical"], total)},
        "high": {"count": buckets["high"], "pct": _pct(buckets["high"], total)},
        "moderate": {"count": buckets["moderate"], "pct": _pct(buckets["moderate"], total)},
        "normal": {"count": buckets["normal"], "pct": _pct(buckets["normal"], total)},
        "total": total,
    }


def _count_case_classifications(period: WeekPeriod) -> dict:
    """Classifications épidémiologiques attribuées dans la période."""
    buckets = {name: 0 for name in CLASSIFICATION_BUCKETS}
    try:
        from apps.medical.models import CaseClassification
        rows = (
            CaseClassification.objects.filter(
                classified_at__gte=period.start, classified_at__lte=period.end,
            )
            .values("classification")
            .annotate(c=Count("id"))
        )
        for row in rows:
            code = (row["classification"] or "").lower().strip()
            for bucket_name, codes in CLASSIFICATION_BUCKETS.items():
                if code in codes:
                    buckets[bucket_name] += row["c"]
                    break
    except Exception:  # noqa: BLE001
        pass
    return buckets


def _count_samples_and_analyses(period: WeekPeriod) -> dict:
    """Prélèvements demandés/réalisés + analyses en attente/pos/neg."""
    samples = {"requested": 0, "collected": 0}
    analyses = {"pending": 0, "positive": 0, "negative": 0, "in_progress": 0}

    try:
        from apps.medical.models import MedicalSample
        samples["requested"] = MedicalSample.objects.filter(
            created_at__gte=period.start, created_at__lte=period.end,
        ).count()
        samples["collected"] = MedicalSample.objects.filter(
            collected_at__gte=period.start, collected_at__lte=period.end,
        ).count()
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.medical.models import LabAnalysis, LabAnalysisStatus, LabAnalysisResult
        base = LabAnalysis.objects.filter(
            created_at__gte=period.start, created_at__lte=period.end,
        )
        analyses["pending"] = base.filter(status=LabAnalysisStatus.PENDING).count()
        analyses["in_progress"] = base.filter(status=LabAnalysisStatus.IN_PROGRESS).count()
        analyses["positive"] = base.filter(result=LabAnalysisResult.POSITIVE).count()
        analyses["negative"] = base.filter(result=LabAnalysisResult.NEGATIVE).count()
    except Exception:  # noqa: BLE001
        pass

    return {"samples": samples, "analyses": analyses}


def _breakdown_entry_point(period: WeekPeriod, limit: int = 15) -> list:
    """Top N points d'entrée par nombre de voyageurs enregistrés."""
    from apps.travelers.models import Traveler
    try:
        rows = (
            Traveler.objects.filter(
                created_at__gte=period.start, created_at__lte=period.end,
                entry_point__isnull=False,
            )
            .values("entry_point__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit]
        )
        return [
            {"name": r["entry_point__name"] or "—", "count": r["count"]}
            for r in rows
        ]
    except Exception:  # noqa: BLE001
        return []


def _breakdown_district(period: WeekPeriod, limit: int = 15) -> list:
    """Top N districts par nombre de voyageurs (via entry_point→zone)."""
    from apps.travelers.models import Traveler
    # Le district n'est pas forcément direct sur Traveler ; on tente 2 stratégies :
    for path in ("entry_point__zone__name", "confinement_district__name"):
        try:
            rows = (
                Traveler.objects.filter(
                    created_at__gte=period.start, created_at__lte=period.end,
                )
                .exclude(**{path: ""})
                .values(path)
                .annotate(count=Count("id"))
                .order_by("-count")[:limit]
            )
            result = [{"name": r[path] or "—", "count": r["count"]} for r in rows]
            if result:
                return result
        except Exception:  # noqa: BLE001
            continue
    return []


def _breakdown_disease(period: WeekPeriod, limit: int = 10) -> list:
    """Top maladies surveillées via QuarantineRecord.disease."""
    try:
        from apps.quarantine.models import QuarantineRecord
        rows = (
            QuarantineRecord.objects.filter(
                created_at__gte=period.start, created_at__lte=period.end,
                disease__isnull=False,
            )
            .values("disease__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:limit]
        )
        return [{"name": r["disease__name"] or "—", "count": r["count"]} for r in rows]
    except Exception:  # noqa: BLE001
        return []


def _top_events(period: WeekPeriod, limit: int = 10) -> list:
    """Événements marquants — alertes CRITIQUES/ÉLEVÉES + cas confirmés."""
    events = []
    try:
        from apps.surveillance.models import HealthAlert
        alerts = (
            HealthAlert.objects
            .filter(created_at__gte=period.start, created_at__lte=period.end,
                    severity__in=["critical", "high"])
            .order_by("-created_at")[:limit]
        )
        for a in alerts:
            events.append({
                "type": "alert",
                "severity": a.severity,
                "title": (a.title if hasattr(a, "title") else str(a))[:120],
                "at": a.created_at.isoformat() if a.created_at else "",
            })
    except Exception:  # noqa: BLE001
        pass

    try:
        from apps.medical.models import CaseClassification
        confirmed = (
            CaseClassification.objects
            .filter(classified_at__gte=period.start, classified_at__lte=period.end,
                    classification="confirmed")
            .order_by("-classified_at")[:limit]
        )
        for c in confirmed:
            events.append({
                "type": "case_confirmed",
                "title": f"Cas confirmé #{c.followup_case_id}",
                "at": c.classified_at.isoformat() if c.classified_at else "",
            })
    except Exception:  # noqa: BLE001
        pass

    # Trier par date desc et couper au limit
    events.sort(key=lambda e: e.get("at", ""), reverse=True)
    return events[:limit]


# ---------------------------------------------------------------------------
# Fonction principale
# ---------------------------------------------------------------------------
def aggregate_weekly(period_start: datetime, period_end: datetime) -> dict:
    """Retourne toutes les KPI du rapport hebdomadaire pour [period_start, period_end].

    Args:
        period_start : datetime timezone-aware (préférable Africa/Abidjan)
        period_end   : datetime timezone-aware, inclus

    Returns:
        dict prêt à sérialiser en JSON dans GeneratedReport.summary_data.
        Structure documentée dans feature-weekly-reports-2026-07-24.md.
    """
    t0 = time.monotonic()

    if not django_tz.is_aware(period_start) or not django_tz.is_aware(period_end):
        raise ValueError(
            "aggregate_weekly requiert des datetimes timezone-aware "
            "(utiliser django.utils.timezone.make_aware ou zoneinfo)."
        )
    if period_start >= period_end:
        raise ValueError("period_start doit être strictement < period_end.")

    period = WeekPeriod(start=period_start, end=period_end)

    # Période précédente : même durée juste avant
    duration = period_end - period_start
    prev_start = period_start - duration - timedelta(seconds=1)
    prev_end = period_start - timedelta(seconds=1)
    prev_period = WeekPeriod(start=prev_start, end=prev_end)

    # Agrégations courantes
    travelers = _count_travelers(period)
    followups = _count_followups(period)
    checkins = _count_checkins(period)
    assistance = _count_assistance(period)
    alerts = _count_alerts(period)
    risk_levels = _count_risk_levels(period)
    cases = _count_case_classifications(period)
    lab = _count_samples_and_analyses(period)

    # Agrégations période précédente (pour comparaison)
    prev_travelers = _count_travelers(prev_period)
    prev_followups = _count_followups(prev_period)
    prev_checkins = _count_checkins(prev_period)
    prev_alerts = _count_alerts(prev_period)

    duration_ms = int((time.monotonic() - t0) * 1000)

    return {
        "period": period.to_dict(),
        "previous_period": prev_period.to_dict(),

        "travelers": travelers,
        "followups": followups,
        "checkins": checkins,
        "assistance": assistance,
        "alerts": alerts,
        "risk_levels": risk_levels,
        "cases": cases,
        "samples": lab["samples"],
        "analyses": lab["analyses"],

        "by_entry_point": _breakdown_entry_point(period),
        "by_district": _breakdown_district(period),
        "by_disease": _breakdown_disease(period),
        "top_events": _top_events(period),

        "comparison": {
            "travelers": {
                "current": travelers["registered"],
                "previous": prev_travelers["registered"],
                "delta_pct": _delta_pct(travelers["registered"], prev_travelers["registered"]),
            },
            "followups_new": {
                "current": followups["new"],
                "previous": prev_followups["new"],
                "delta_pct": _delta_pct(followups["new"], prev_followups["new"]),
            },
            "checkins_received": {
                "current": checkins["received"],
                "previous": prev_checkins["received"],
                "delta_pct": _delta_pct(checkins["received"], prev_checkins["received"]),
            },
            "alerts_created": {
                "current": alerts["created"],
                "previous": prev_alerts["created"],
                "delta_pct": _delta_pct(alerts["created"], prev_alerts["created"]),
            },
        },

        "meta": {
            "generated_at": django_tz.now().isoformat(),
            "generation_ms": duration_ms,
            "tz": str(django_tz.get_current_timezone()),
            "schema_version": 1,
        },
    }


# ---------------------------------------------------------------------------
# Helper : calculer la période "semaine précédente" (lun→dim en Africa/Abidjan)
# ---------------------------------------------------------------------------
def previous_week_period(now: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Retourne (start, end) de la semaine ISO précédente en Africa/Abidjan.

    Ex. si now = mercredi 24 juin 2026 08:00 Abidjan :
      start = lundi 15 juin 2026 00:00:00 Abidjan
      end   = dimanche 21 juin 2026 23:59:59.999999 Abidjan
    """
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo("Africa/Abidjan")
    except Exception:
        tz = django_tz.get_current_timezone()

    if now is None:
        now = django_tz.now().astimezone(tz)
    elif django_tz.is_aware(now):
        now = now.astimezone(tz)

    # Lundi de la semaine courante (ISO 8601 : weekday()==0 → lundi)
    today = now.date()
    monday_this_week = today - timedelta(days=today.weekday())
    monday_prev_week = monday_this_week - timedelta(days=7)
    sunday_prev_week = monday_prev_week + timedelta(days=6)

    start = datetime(monday_prev_week.year, monday_prev_week.month,
                     monday_prev_week.day, 0, 0, 0, tzinfo=tz)
    end = datetime(sunday_prev_week.year, sunday_prev_week.month,
                   sunday_prev_week.day, 23, 59, 59, 999999, tzinfo=tz)
    return start, end
