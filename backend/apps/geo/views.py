from datetime import timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole, IsAuthenticatedAndActive

from .models import Country, CountryRiskAssessment, EntryPoint, HealthZone
from .serializers import (
    CloseRiskAssessmentSerializer,
    CountryRiskAssessmentSerializer,
    CountrySerializer,
    EntryPointSerializer,
    HealthZoneSerializer,
)
from .services import close_risk_assessment, current_assessments, record_risk_assessment

# Rôles habilités à définir le référentiel pays et les niveaux de risque.
COUNTRY_ADMIN_ROLES = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY]


def _drf_error(exc: DjangoValidationError) -> serializers.ValidationError:
    return serializers.ValidationError(getattr(exc, "message_dict", None) or exc.messages)


class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all().order_by("name")
    serializer_class = CountrySerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["code", "code3", "name", "region"]
    filterset_fields = ["region", "risk_level", "is_monitored"]

    def get_queryset(self):
        return super().get_queryset().prefetch_related(
            Prefetch(
                "risk_assessments",
                queryset=current_assessments().select_related("disease").order_by("disease__code"),
                to_attr="current_assessments_list",
            )
        )

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            self.required_roles = COUNTRY_ADMIN_ROLES
            return [IsAuthenticatedAndActive(), HasRole()]
        return super().get_permissions()

    @action(detail=True, methods=["get"], url_path="risk-history")
    def risk_history(self, request, pk=None):
        """Toutes les évaluations du pays (en vigueur, closes, remplacées)."""
        country = self.get_object()
        qs = (
            CountryRiskAssessment.objects.filter(country=country)
            .select_related("country", "disease", "decided_by", "superseded_by")
            .order_by("-valid_from", "-created_at")
        )
        return Response(CountryRiskAssessmentSerializer(qs, many=True).data)


class CountryRiskAssessmentViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Niveaux de risque par pays et par maladie.

    Pas de modification ni de suppression : un nouveau niveau se saisit en
    créant une évaluation (qui remplace la précédente), une fin de validité
    via l'action `close`. L'historique reste donc complet.
    """

    queryset = CountryRiskAssessment.objects.select_related(
        "country", "disease", "decided_by", "superseded_by", "source_alert",
    ).order_by("-valid_from", "-created_at")
    serializer_class = CountryRiskAssessmentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "uuid"
    filterset_fields = {
        "country__code": ["exact"],
        "disease__code": ["exact"],
        "risk_level": ["exact"],
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if (self.request.query_params.get("current") or "").lower() == "true":
            qs = qs.filter(pk__in=current_assessments().values("pk"))
        return qs

    def get_permissions(self):
        if self.action in {"create", "close"}:
            self.required_roles = COUNTRY_ADMIN_ROLES
            return [IsAuthenticatedAndActive(), HasRole()]
        return super().get_permissions()

    def perform_create(self, serializer):
        data = serializer.validated_data
        try:
            serializer.instance = record_risk_assessment(
                country=data["country"],
                disease=data.get("disease"),
                risk_level=data["risk_level"],
                justification=data.get("justification", ""),
                valid_from=data.get("valid_from"),
                valid_until=data.get("valid_until"),
                source_alert=data.get("source_alert"),
                source_reference=data.get("source_reference", ""),
                decided_by=self.request.user,
            )
        except DjangoValidationError as exc:
            raise _drf_error(exc) from exc

    @action(detail=True, methods=["post"])
    def close(self, request, uuid=None):
        assessment = self.get_object()
        ser = CloseRiskAssessmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            close_risk_assessment(
                assessment,
                valid_until=ser.validated_data.get("valid_until"),
                reason=ser.validated_data["reason"],
            )
        except DjangoValidationError as exc:
            raise _drf_error(exc) from exc
        return Response(self.get_serializer(assessment).data, status=status.HTTP_200_OK)


class EntryPointViewSet(viewsets.ModelViewSet):
    queryset = EntryPoint.objects.select_related("country").all().order_by("name")
    serializer_class = EntryPointSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["code", "name", "city", "country__name", "iata_code"]
    filterset_fields = ["type", "country", "is_active"]

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            self.required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]
            return [IsAuthenticatedAndActive(), HasRole()]
        return super().get_permissions()


class HealthZoneViewSet(viewsets.ModelViewSet):
    """CRUD HealthZone + actions de synthèse pour cartographie & dashboards."""

    queryset = HealthZone.objects.select_related("parent").all().order_by("level", "name")
    serializer_class = HealthZoneSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["level", "risk_level", "parent"]
    search_fields = ["code", "name", "parent__name"]
    lookup_field = "code"
    lookup_value_regex = r"[\w-]+"

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            self.required_roles = [RoleCode.NATIONAL_ADMIN, RoleCode.MINISTRY, RoleCode.INHP]
            return [IsAuthenticatedAndActive(), HasRole()]
        return super().get_permissions()

    # ------------------------------------------------------------------
    # GET /geo/zones/<code>/stats/
    # ------------------------------------------------------------------
    @action(detail=True, methods=["get"])
    def stats(self, request, code=None):
        """Renvoie les indicateurs agrégés d'une zone sanitaire.

        Pour une zone parent (PRES, région, district) : agrège récursivement
        sur tous les voyageurs / alertes / quarantines des descendants.

        La liaison Traveler → HealthZone n'étant pas matérialisée par une
        FK, on approxime par matching de noms géographiques sur les champs
        existants du modèle Traveler :
          - `entry_point.region` (CharField libre sur EntryPoint)
          - `confinement_city`
          - `confinement_commune`
          - `confinement_neighborhood`

        Les alertes sont matchées via `HealthAlert.zone` (FK directe) OU
        via les voyageurs liés ci-dessus.
        """
        from apps.quarantine.models import DailyCheck, QuarantineRecord
        from apps.surveillance.models import HealthAlert
        from apps.travelers.models import Traveler

        zone = self.get_object()

        # ── 1) Collecter récursivement tous les descendants (incluant la zone)
        all_zones = _descendants_with_self(zone)
        zone_ids = [z.id for z in all_zones]
        zone_names = [z.name for z in all_zones]

        # ── 2) Périmètre temporel (30 jours par défaut, plafonné à 5 ans)
        try:
            days = max(1, min(1825, int(request.query_params.get("days", 30))))
        except (TypeError, ValueError):
            days = 30
        since = timezone.now() - timedelta(days=days)

        # ── 3) Voyageurs liés via matching sur les vrais champs Traveler
        #     (entry_point.region OU confinement_city/commune/quartier)
        trav_filter = (
            Q(entry_point__region__in=zone_names)
            | Q(confinement_city__in=zone_names)
            | Q(confinement_commune__in=zone_names)
            | Q(confinement_neighborhood__in=zone_names)
        )
        trav_qs = Traveler.objects.filter(trav_filter).distinct()
        n_travelers = trav_qs.count()
        n_travelers_recent = trav_qs.filter(arrival_date__gte=since.date()).count()

        # ── 4) Alertes : via zone FK directe OU via voyageurs ciblés
        #     Note : target_id est CharField → on convertit les PK en str
        trav_pks_str = [str(pk) for pk in trav_qs.values_list("pk", flat=True)[:5000]]
        alert_qs = HealthAlert.objects.filter(
            Q(zone_id__in=zone_ids)
            | Q(target_ct__model="traveler", target_id__in=trav_pks_str)
        ).distinct()
        n_alerts_total = alert_qs.count()
        OPEN_STATUSES = ["OPEN", "ACK", "INVESTIGATING", "open", "ack", "investigating"]
        n_alerts_open = alert_qs.filter(status__in=OPEN_STATUSES).count()
        n_alerts_critical = alert_qs.filter(
            status__in=OPEN_STATUSES,
            severity__in=["critical", "CRITICAL", "high", "HIGH"],
        ).count()

        # ── 5) Quarantaines : via voyageurs
        qr_qs = QuarantineRecord.objects.filter(traveler__in=trav_qs)
        n_quarantines_total = qr_qs.count()
        n_quarantines_active = qr_qs.filter(status__in=["active", "extended"]).count()
        n_quarantines_completed = qr_qs.filter(
            status__in=["completed", "broken", "cancelled"]
        ).count()

        # ── 6) Check-ins quotidiens sur la période
        check_qs = DailyCheck.objects.filter(
            quarantine__in=qr_qs, check_date__gte=since.date()
        )
        n_checkins = check_qs.count()
        n_checkins_symptomatic = check_qs.filter(has_symptoms=True).count()

        # ── 7) Ventilation par sévérité d'alerte
        by_severity = list(
            alert_qs.values("severity").annotate(n=Count("id")).order_by("-n")
        )
        # ── 8) Ventilation par status quarantaine
        by_qr_status = list(
            qr_qs.values("status").annotate(n=Count("id")).order_by("-n")
        )

        # ── 9) Enfants directs (pour drill-down côté front)
        children = [
            {
                "code": c.code,
                "name": c.name,
                "level": c.level,
                "risk_level": c.risk_level,
                "population": c.population,
            }
            for c in HealthZone.objects.filter(parent=zone).order_by("name")[:50]
        ]

        # ── 10) Chemin (breadcrumb)
        breadcrumb = []
        cur = zone
        seen_ids = set()
        while cur and cur.id not in seen_ids:
            seen_ids.add(cur.id)
            breadcrumb.insert(0, {
                "code": cur.code,
                "name": cur.name,
                "level": cur.level,
            })
            cur = cur.parent

        return Response({
            "zone": {
                "code": zone.code,
                "name": zone.name,
                "level": zone.level,
                "level_display": zone.get_level_display(),
                "risk_level": zone.risk_level,
                "population": zone.population,
                "has_geometry": zone.geometry is not None,
                "n_descendants": len(all_zones) - 1,
            },
            "breadcrumb": breadcrumb,
            "period_days": days,
            "kpis": {
                "travelers_total": n_travelers,
                "travelers_recent": n_travelers_recent,
                "alerts_total": n_alerts_total,
                "alerts_open": n_alerts_open,
                "alerts_critical": n_alerts_critical,
                "quarantines_total": n_quarantines_total,
                "quarantines_active": n_quarantines_active,
                "quarantines_completed": n_quarantines_completed,
                "checkins": n_checkins,
                "checkins_symptomatic": n_checkins_symptomatic,
            },
            "by_severity": by_severity,
            "by_quarantine_status": by_qr_status,
            "children": children,
        })

    # ------------------------------------------------------------------
    # GET /geo/zones/geojson/
    # ------------------------------------------------------------------
    @action(detail=False, methods=["get"])
    def geojson(self, request):
        """Retourne tous les polygones HealthZone en FeatureCollection GeoJSON.

        Filtres :
            ?level=region|district|commune|quartier  (défaut: tous sauf country/pres/custom)
            ?with_risk=true   ajoute risk_level dans les properties (défaut: oui)

        Performance : ce endpoint peut être lourd (jusqu'à 370 zones avec
        polygones complexes). On peut le mettre en cache 5 minutes si besoin.
        """
        level = request.query_params.get("level")
        qs = HealthZone.objects.filter(geometry__isnull=False).select_related("parent")
        if level:
            qs = qs.filter(level=level)
        else:
            qs = qs.exclude(level__in=["country", "pres", "custom"])

        features = []
        for z in qs:
            features.append({
                "type": "Feature",
                "id": z.code,
                "geometry": {
                    "type": "MultiPolygon",
                    # Convertit la geometry PostGIS en coordonnées GeoJSON
                    "coordinates": list(z.geometry.coords),
                },
                "properties": {
                    "code": z.code,
                    "name": z.name,
                    "level": z.level,
                    "level_display": z.get_level_display(),
                    "risk_level": z.risk_level,
                    "population": z.population,
                    "parent_name": z.parent.name if z.parent_id else None,
                    "parent_code": z.parent.code if z.parent_id else None,
                },
            })

        return Response({
            "type": "FeatureCollection",
            "features": features,
            "count": len(features),
        })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _descendants_with_self(zone, _seen=None) -> list:
    """Renvoie la liste plate de la zone + tous ses descendants récursivement.

    Garde-fou anti-boucle au cas où la hiérarchie est circulaire (improbable
    mais possible si quelqu'un édite parent en admin).
    """
    if _seen is None:
        _seen = set()
    if zone.id in _seen:
        return []
    _seen.add(zone.id)
    out = [zone]
    for c in zone.children.all():
        out.extend(_descendants_with_self(c, _seen))
    return out
