"""URLs racine d'EpidemiTracker."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)


def healthcheck(_request):
    """Health probe : utilisée par K8s liveness/readiness et Traefik."""
    return JsonResponse({"status": "ok", "service": "epidemitracker-api"})


api_v1_patterns = [
    # --- Auth ---
    path("auth/", include("apps.accounts.urls")),

    # --- Maladies & formulaires dynamiques ---
    path("diseases/", include("apps.diseases.urls")),
    path("forms/", include("apps.forms.urls")),

    # --- Géo / points d'entrée ---
    path("geo/", include("apps.geo.urls")),

    # --- Voyageurs ---
    path("travelers/", include("apps.travelers.urls")),

    # --- Module Ebola ---
    path("ebola/", include("apps.ebola.urls")),

    # --- Health Pass / QR ---
    path("passes/", include("apps.health_pass.urls")),

    # --- Quarantaine / suivi 21 jours ---
    path("quarantine/", include("apps.quarantine.urls")),

    # --- Surveillance / scoring ---
    path("surveillance/", include("apps.surveillance.urls")),

    # --- Notifications ---
    path("notifications/", include("apps.notifications.urls")),

    # --- Analytics / dashboards ---
    path("analytics/", include("apps.analytics.urls")),

    # --- Audit ---
    path("audit/", include("apps.audit.urls")),

    # --- Companion (PWA voyageur : check-in, géoloc, push, consentement) ---
    path("public/", include("apps.companion.urls")),

    # --- Companion ADMIN (suivi voyageurs, itinéraire, carte) ---
    path("admin/companion/", include("apps.companion.admin_urls")),

    # --- Centre de rapports (exports CSV / PDF) ---
    path("reports/", include("apps.reports.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz/", healthcheck, name="healthcheck"),
    path("metrics/", include("django_prometheus.urls")),

    # OpenAPI / Swagger / Redoc
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # API v1
    path("api/v1/", include((api_v1_patterns, "v1"), namespace="v1")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
