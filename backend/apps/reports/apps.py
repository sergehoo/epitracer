from django.apps import AppConfig


class ReportsConfig(AppConfig):
    """Centre de rapports — export CSV / PDF des données opérationnelles."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reports"
    verbose_name = "Reports"
