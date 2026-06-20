"""Endpoints d'agrégation pour le dashboard national + tracking visites."""
from __future__ import annotations

from collections import OrderedDict
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Avg, Count, F, Q
from django.db.models.functions import ExtractHour, TruncDate
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole
from apps.ebola.models import EbolaInvestigation
from apps.health_pass.models import HealthPass
from apps.quarantine.models import QuarantineRecord, QuarantineStatus
from apps.surveillance.models import HealthAlert
from apps.travelers.models import Traveler

from .models import PageVisit, Portal
from .serializers import VisitTrackSerializer
from .services import detect_country, extract_ip, looks_like_bot


# =========================================================================
#                        DASHBOARD OVERVIEW
# =========================================================================
class DashboardOverviewView(APIView):
    permission_classes = [IsAuthenticated, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
        RoleCode.DISTRICT, RoleCode.ENTRY_POINT, RoleCode.OBSERVER,
    ]

    def get(self, request):
        cache_key = "dashboard:overview:v2"
        data = cache.get(cache_key)
        if data is not None:
            return Response(data)

        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        data = {
            "travelers": {
                "total": Traveler.objects.count(),
                "last_24h": Traveler.objects.filter(created_at__gte=last_24h).count(),
                "by_status": dict(
                    Traveler.objects.values_list("current_health_status").annotate(c=Count("id")).values_list("current_health_status", "c")
                ),
            },
            "ebola": {
                "total": EbolaInvestigation.objects.count(),
                "by_status": dict(
                    EbolaInvestigation.objects.values_list("status").annotate(c=Count("id")).values_list("status", "c")
                ),
                "by_risk": dict(
                    EbolaInvestigation.objects.values_list("risk_level").annotate(c=Count("id")).values_list("risk_level", "c")
                ),
                "last_7d": EbolaInvestigation.objects.filter(created_at__gte=last_7d).count(),
            },
            "quarantines": {
                "active": QuarantineRecord.objects.filter(status=QuarantineStatus.ACTIVE).count(),
                "total": QuarantineRecord.objects.count(),
            },
            "passes": {
                "total": HealthPass.objects.count(),
                "active": HealthPass.objects.filter(status="active").count(),
                "revoked": HealthPass.objects.filter(status="revoked").count(),
            },
            "alerts": {
                "open": HealthAlert.objects.filter(status="open").count(),
                "critical_24h": HealthAlert.objects.filter(severity="critical", created_at__gte=last_24h).count(),
            },
            "visits": {
                "today": PageVisit.objects.filter(is_bot=False, created_at__date=now.date()).count(),
                "last_7d": PageVisit.objects.filter(is_bot=False, created_at__gte=last_7d).count(),
            },
            "generated_at": now.isoformat(),
        }
        cache.set(cache_key, data, timeout=30)
        return Response(data)


class NationalDashboardView(APIView):
    """Endpoint d'agrégation COMPLET pour le tableau de bord national.

    GET /api/v1/analytics/national/

    Une seule requête HTTP renvoie tout ce dont la page /dashboard a besoin :
    KPIs, série temporelle 14j, top 5 points d'entrée, répartitions, alertes
    récentes. Cache 60s pour éviter la pression DB en cas de rechargement
    répété de la page.
    """

    permission_classes = [IsAuthenticated, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
        RoleCode.DISTRICT, RoleCode.ENTRY_POINT, RoleCode.OBSERVER,
    ]

    def get(self, request):
        # ---- Lecture des filtres ----
        try:
            period_days = int(request.query_params.get("period", "30"))
        except ValueError:
            period_days = 30
        period_days = max(1, min(period_days, 365))

        risk_filter = (request.query_params.get("risk") or "").strip().lower()
        country_filter = (request.query_params.get("country") or "").strip().upper()
        entry_point_filter = (request.query_params.get("entry_point") or "").strip()
        followup_filter = (request.query_params.get("followup") or "").strip().lower()
        compare = (request.query_params.get("compare") or "true").lower() != "false"

        cache_key = (
            f"dashboard:national:v4:p={period_days}:r={risk_filter}"
            f":c={country_filter}:e={entry_point_filter}:f={followup_filter}:cmp={compare}"
        )
        data = cache.get(cache_key)
        if data is not None:
            return Response(data)

        now = timezone.now()
        today = now.date()
        last_24h = now - timedelta(hours=24)
        last_48h = now - timedelta(hours=48)
        period_start = now - timedelta(days=period_days)
        prev_period_start = now - timedelta(days=period_days * 2)
        last_7d = now - timedelta(days=7)
        last_14d = now - timedelta(days=14)

        # Filtre voyageurs partagé selon les query params
        travelers_qs = Traveler.objects.all()
        if country_filter:
            try:
                from apps.travelers.models import TravelHistoryEntry
                tids = TravelHistoryEntry.objects.filter(
                    role="origin", country__code=country_filter,
                ).values_list("traveler_id", flat=True)
                travelers_qs = travelers_qs.filter(id__in=tids)
            except Exception:
                pass
        if entry_point_filter and entry_point_filter.isdigit():
            travelers_qs = travelers_qs.filter(entry_point_id=int(entry_point_filter))

        # Filtre Ebola investigations selon risque
        invest_qs = EbolaInvestigation.objects.all()
        if risk_filter in {"low", "moderate", "high", "critical"}:
            invest_qs = invest_qs.filter(risk_level=risk_filter)
        # Si on filtre par pays, restreindre aux voyageurs concernés
        if country_filter:
            invest_qs = invest_qs.filter(traveler__in=travelers_qs)

        # Filtre quarantaines selon "followup"
        quars_qs = QuarantineRecord.objects.all()
        if followup_filter == "active":
            quars_qs = quars_qs.filter(
                status__in=[QuarantineStatus.ACTIVE, "EXTENDED"],
            )
        elif followup_filter == "missed":
            quars_qs = quars_qs.filter(
                status__in=[QuarantineStatus.ACTIVE, "EXTENDED"],
            ).exclude(daily_checks__check_date__gte=last_48h.date())
        elif followup_filter == "closed":
            quars_qs = quars_qs.filter(
                status__in=["COMPLETED", "CLOSED", "RELEASED"],
            )
        if country_filter or entry_point_filter:
            quars_qs = quars_qs.filter(traveler__in=travelers_qs)

        # ------------------------------------------------------------------
        # KPIs principaux (sur la période filtrée)
        # ------------------------------------------------------------------
        period_travelers = travelers_qs.filter(created_at__gte=period_start)
        period_invests = invest_qs.filter(created_at__gte=period_start)
        prev_period_travelers = travelers_qs.filter(
            created_at__gte=prev_period_start, created_at__lt=period_start,
        )
        prev_period_invests = invest_qs.filter(
            created_at__gte=prev_period_start, created_at__lt=period_start,
        )

        kpis = {
            "travelers_today": travelers_qs.filter(created_at__date=today).count(),
            "travelers_period": period_travelers.count(),
            "travelers_total": travelers_qs.count(),
            "active_followups": quars_qs.filter(
                status__in=[QuarantineStatus.ACTIVE, "EXTENDED"],
            ).count(),
            "passes_issued": HealthPass.objects.count(),
            "passes_active": HealthPass.objects.filter(status="active").count(),
            "alerts_open": HealthAlert.objects.filter(
                status__in=["OPEN", "ACK", "INVESTIGATING"]
            ).count(),
            "alerts_critical_24h": HealthAlert.objects.filter(
                severity__iexact="critical", created_at__gte=last_24h,
            ).count(),
            "high_risk_travelers": travelers_qs.filter(
                current_health_status__in=["suspect", "confirmed"],
            ).count(),
            "cases_critical_period": period_invests.filter(risk_level="critical").count(),
            "cases_high_period": period_invests.filter(risk_level="high").count(),
        }

        # Comparaison période vs période précédente
        if compare:
            def _trend(curr: int, prev: int) -> dict:
                if prev == 0:
                    return {"current": curr, "previous": 0, "trend_pct": 100 if curr > 0 else 0}
                pct = round((curr - prev) / prev * 100, 1)
                return {"current": curr, "previous": prev, "trend_pct": pct}

            kpis["comparison"] = {
                "travelers": _trend(
                    period_travelers.count(), prev_period_travelers.count(),
                ),
                "cases_critical": _trend(
                    period_invests.filter(risk_level="critical").count(),
                    prev_period_invests.filter(risk_level="critical").count(),
                ),
                "cases_high": _trend(
                    period_invests.filter(risk_level="high").count(),
                    prev_period_invests.filter(risk_level="high").count(),
                ),
            }

        # Check-ins (DailyCheck via quarantine)
        try:
            from apps.quarantine.models import DailyCheck
            kpis["checkins_today"] = DailyCheck.objects.filter(check_date=today).count()
            kpis["checkins_with_symptoms_today"] = DailyCheck.objects.filter(
                check_date=today, has_symptoms=True,
            ).count()
            # Missed = quarantines actives sans daily_check récent
            active_quars = QuarantineRecord.objects.filter(
                status__in=[QuarantineStatus.ACTIVE, "EXTENDED"],
            )
            kpis["checkins_missed_48h"] = active_quars.exclude(
                daily_checks__check_date__gte=last_48h.date(),
            ).count()
        except Exception:  # noqa: BLE001
            kpis["checkins_today"] = 0
            kpis["checkins_with_symptoms_today"] = 0
            kpis["checkins_missed_48h"] = 0

        # ------------------------------------------------------------------
        # Série temporelle sur la période choisie
        # ------------------------------------------------------------------
        timeline_raw = (
            period_travelers
            .annotate(d=TruncDate("created_at"))
            .values("d").annotate(count=Count("id")).order_by("d")
        )
        timeline_map = {row["d"].isoformat(): row["count"] for row in timeline_raw}

        # Cas confirmés/suspects par jour (Ebola investigations)
        cases_raw = (
            period_invests
            .annotate(d=TruncDate("created_at"))
            .values("d", "risk_level").annotate(count=Count("id")).order_by("d")
        )
        cases_map: dict[str, dict[str, int]] = {}
        for row in cases_raw:
            key = row["d"].isoformat()
            cases_map.setdefault(key, {"low": 0, "moderate": 0, "high": 0, "critical": 0})
            cases_map[key][row["risk_level"]] = row["count"]

        timeline = []
        for i in range(period_days, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            row = {
                "date": d,
                "travelers": timeline_map.get(d, 0),
                "cases_low": cases_map.get(d, {}).get("low", 0),
                "cases_moderate": cases_map.get(d, {}).get("moderate", 0),
                "cases_high": cases_map.get(d, {}).get("high", 0),
                "cases_critical": cases_map.get(d, {}).get("critical", 0),
            }
            timeline.append(row)

        # ------------------------------------------------------------------
        # Top points d'entrée sur la période
        # ------------------------------------------------------------------
        top_entry_points = list(
            period_travelers.filter(entry_point__isnull=False)
            .values("entry_point__name", "entry_point__code")
            .annotate(count=Count("id")).order_by("-count")[:8]
        )

        # ------------------------------------------------------------------
        # Top pays/nationalités sur la période
        # ------------------------------------------------------------------
        try:
            from apps.travelers.models import TravelHistoryEntry
            top_origins = list(
                TravelHistoryEntry.objects.filter(
                    role="origin", traveler__in=period_travelers,
                ).values("country__code", "country__name")
                .annotate(count=Count("id")).order_by("-count")[:10]
            )
        except Exception:  # noqa: BLE001
            top_origins = []

        # nationality est une FK vers Country — on resort code + name comme top_origins.
        # .exclude(nationality__isnull=True) suffit ; pas de .exclude(nationality="")
        # qui castait "" en int et crashait avec ValueError sur FK.
        top_nationalities = list(
            period_travelers.exclude(nationality__isnull=True)
            .values("nationality__code", "nationality__name")
            .annotate(count=Count("id")).order_by("-count")[:10]
        )

        # ------------------------------------------------------------------
        # Répartition statuts sanitaires (sur voyageurs filtrés)
        # ------------------------------------------------------------------
        statuses = dict(
            travelers_qs.values_list("current_health_status")
            .annotate(c=Count("id")).values_list("current_health_status", "c")
        )

        # ------------------------------------------------------------------
        # Répartition niveau de risque (Ebola, filtré période)
        # ------------------------------------------------------------------
        risk_levels = dict(
            period_invests.values_list("risk_level")
            .annotate(c=Count("id")).values_list("risk_level", "c")
        )

        # ------------------------------------------------------------------
        # Funnel : arrivées → pass émis → suivi actif → check-in fait → clôturé
        # ------------------------------------------------------------------
        funnel_total_arrivals = period_travelers.count()
        funnel_with_pass = HealthPass.objects.filter(
            traveler__in=period_travelers,
        ).count()
        funnel_followup = quars_qs.filter(traveler__in=period_travelers).count()
        try:
            from apps.quarantine.models import DailyCheck
            funnel_checked = DailyCheck.objects.filter(
                quarantine__traveler__in=period_travelers,
            ).values("quarantine_id").distinct().count()
        except Exception:
            funnel_checked = 0
        funnel_closed = quars_qs.filter(
            traveler__in=period_travelers,
            status__in=["COMPLETED", "CLOSED", "RELEASED"],
        ).count()
        funnel = [
            {"step": "Arrivées", "count": funnel_total_arrivals},
            {"step": "Pass émis", "count": funnel_with_pass},
            {"step": "Suivi enregistré", "count": funnel_followup},
            {"step": "Au moins 1 check-in", "count": funnel_checked},
            {"step": "Clôturé", "count": funnel_closed},
        ]

        # ------------------------------------------------------------------
        # Heatmap arrivées par heure de la journée (24 buckets)
        # ------------------------------------------------------------------
        try:
            hourly_raw = (
                period_travelers
                .annotate(h=ExtractHour("created_at"))
                .values("h").annotate(c=Count("id")).order_by("h")
            )
            hourly_map = {row["h"]: row["c"] for row in hourly_raw}
            arrivals_by_hour = [
                {"hour": h, "count": hourly_map.get(h, 0)} for h in range(24)
            ]
        except Exception:
            arrivals_by_hour = [{"hour": h, "count": 0} for h in range(24)]

        # ------------------------------------------------------------------
        # Observance check-in : % de quarantaines actives avec check-in <48h
        # ------------------------------------------------------------------
        try:
            from apps.quarantine.models import DailyCheck
            active_q = quars_qs.filter(
                status__in=[QuarantineStatus.ACTIVE, "EXTENDED"],
            )
            total_active = active_q.count()
            with_recent = active_q.filter(
                daily_checks__check_date__gte=last_48h.date(),
            ).distinct().count()
            checkin_compliance_pct = round(
                (with_recent / total_active * 100) if total_active else 0, 1,
            )
        except Exception:
            checkin_compliance_pct = 0
            total_active = 0
            with_recent = 0

        # ------------------------------------------------------------------
        # Alertes récentes (10 dernières non clôturées)
        # ------------------------------------------------------------------
        recent_alerts = [
            {
                "id": str(a.uuid),
                "code": a.code,
                "title": a.title,
                "severity": a.severity,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in HealthAlert.objects.filter(
                status__in=["OPEN", "ACK", "INVESTIGATING"],
            ).order_by("-created_at")[:10]
        ]

        data = {
            "filters": {
                "period_days": period_days,
                "risk": risk_filter or None,
                "country": country_filter or None,
                "entry_point": entry_point_filter or None,
                "followup": followup_filter or None,
            },
            "kpis": kpis,
            "timeline": timeline,
            "top_entry_points": top_entry_points,
            "top_origins": top_origins,
            "top_nationalities": top_nationalities,
            "statuses": statuses,
            "risk_levels": risk_levels,
            "funnel": funnel,
            "arrivals_by_hour": arrivals_by_hour,
            "checkin_compliance": {
                "pct": checkin_compliance_pct,
                "with_recent": with_recent,
                "total_active": total_active,
            },
            "recent_alerts": recent_alerts,
            "generated_at": now.isoformat(),
        }
        cache.set(cache_key, data, timeout=60)
        return Response(data)


class EntryPointFlowsView(APIView):
    permission_classes = [IsAuthenticated, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
        RoleCode.DISTRICT, RoleCode.ENTRY_POINT, RoleCode.OBSERVER,
    ]

    def get(self, request):
        since = timezone.now().date() - timedelta(days=7)
        data = (
            Traveler.objects.filter(arrival_date__gte=since)
            .values("entry_point__name").annotate(count=Count("id")).order_by("-count")
        )
        return Response(list(data))


class HeatmapView(APIView):
    """Liste enrichie des voyageurs géolocalisés pour la carte admin."""

    permission_classes = [IsAuthenticated, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP,
        RoleCode.DISTRICT, RoleCode.OBSERVER,
    ]

    def get(self, request):
        qs = (
            Traveler.objects
            .exclude(confinement_location__isnull=True)
            .select_related("entry_point", "nationality")
            .prefetch_related("ebola_investigations")
        )

        # Filtres optionnels côté serveur — DOIVENT être appliqués AVANT le slice,
        # sinon Django lève : "Cannot filter a query once a slice has been taken".
        status = request.query_params.get("status")
        if status:
            qs = qs.filter(current_health_status=status)
        entry_point = request.query_params.get("entry_point")
        if entry_point:
            try:
                qs = qs.filter(entry_point_id=int(entry_point))
            except (TypeError, ValueError):
                pass

        # Tri + limite (slice en dernier)
        qs = qs.order_by("-created_at")[:5000]

        out = []
        for t in qs:
            last_inv = t.ebola_investigations.order_by("-created_at").first()
            out.append({
                "public_id": t.public_id,
                "lat": t.confinement_location.y,
                "lng": t.confinement_location.x,
                "status": t.current_health_status,
                "full_name": t.full_name,
                "entry_point": t.entry_point.name if t.entry_point_id else None,
                "entry_point_id": t.entry_point_id,
                "nationality": t.nationality.code if t.nationality_id else None,
                "risk_level": last_inv.risk_level if last_inv else None,
                "risk_score": last_inv.risk_score if last_inv else None,
                "city": t.confinement_city or t.confinement_commune,
                "arrival_date": t.arrival_date.isoformat() if t.arrival_date else None,
            })
        return Response(out)


# =========================================================================
#                         VISITES : TRACKING PUBLIC
# =========================================================================
class TrackVisitView(APIView):
    """POST public — un appel par page-view depuis le front."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "anon"

    def post(self, request):
        ser = VisitTrackSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        ua = request.META.get("HTTP_USER_AGENT", "")[:400]
        bot = looks_like_bot(ua)
        code, name = detect_country(request, fallback_code=d.get("country_code", ""))

        PageVisit.objects.create(
            session_id=d["session_id"][:64],
            portal=d.get("portal") or Portal.PUBLIC,
            host=request.get_host()[:120],
            path=d["path"][:400],
            referrer=d.get("referrer", "")[:500],
            user_agent=ua,
            ip_address=extract_ip(request),
            country_code=code,
            country_name=name,
            language=d.get("language", "")[:12],
            timezone=d.get("timezone", "")[:64],
            is_bot=bot,
            user=request.user if request.user.is_authenticated else None,
        )
        return Response({"recorded": True, "is_bot": bot})


# =========================================================================
#                         VISITES : STATS ADMIN
# =========================================================================
class VisitsOverviewView(APIView):
    """Stats agrégées pour la page d'administration."""

    permission_classes = [IsAuthenticated, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP, RoleCode.OBSERVER,
    ]

    def get(self, request):
        days = int(request.query_params.get("days", 30))
        days = max(1, min(days, 365))
        exclude_bots = request.query_params.get("include_bots") != "1"
        portal = request.query_params.get("portal")

        now = timezone.now()
        start = now - timedelta(days=days)
        previous_start = start - timedelta(days=days)

        base_qs = PageVisit.objects.all()
        if exclude_bots:
            base_qs = base_qs.filter(is_bot=False)
        if portal:
            base_qs = base_qs.filter(portal=portal)

        current_qs = base_qs.filter(created_at__gte=start)
        previous_qs = base_qs.filter(created_at__gte=previous_start, created_at__lt=start)

        today = now.date()
        week_start = today - timedelta(days=today.weekday())
        month_start = today.replace(day=1)

        kpi = {
            "total": base_qs.count(),
            "today": base_qs.filter(created_at__date=today).count(),
            "this_week": base_qs.filter(created_at__date__gte=week_start).count(),
            "this_month": base_qs.filter(created_at__date__gte=month_start).count(),
            "period": current_qs.count(),
            "previous_period": previous_qs.count(),
            "unique_sessions_period": current_qs.values("session_id").distinct().count(),
        }
        prev = kpi["previous_period"] or 1
        kpi["trend_pct"] = round(((kpi["period"] - kpi["previous_period"]) / prev) * 100, 1)

        by_day_qs = (
            current_qs.annotate(day=TruncDate("created_at"))
            .values("day").annotate(count=Count("id")).order_by("day")
        )
        day_map = OrderedDict()
        cur = start.date()
        while cur <= today:
            day_map[cur.isoformat()] = 0
            cur += timedelta(days=1)
        for row in by_day_qs:
            if row["day"]:
                day_map[row["day"].isoformat()] = row["count"]
        by_day = [{"date": k, "count": v} for k, v in day_map.items()]

        top_countries = list(
            current_qs.exclude(country_code="")
            .values("country_code", "country_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:15]
        )
        top_cities = list(
            current_qs.exclude(city="")
            .values("city", "country_code", "country_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:15]
        )
        top_paths = list(
            current_qs.values("path").annotate(count=Count("id")).order_by("-count")[:15]
        )
        by_portal = list(
            current_qs.values("portal").annotate(count=Count("id")).order_by("-count")
        )
        top_languages = list(
            current_qs.exclude(language="")
            .values("language").annotate(count=Count("id")).order_by("-count")[:10]
        )

        return Response({
            "days": days,
            "exclude_bots": exclude_bots,
            "portal_filter": portal,
            "kpi": kpi,
            "by_day": by_day,
            "top_countries": top_countries,
            "top_cities": top_cities,
            "top_paths": top_paths,
            "by_portal": by_portal,
            "top_languages": top_languages,
            "generated_at": now.isoformat(),
        })
