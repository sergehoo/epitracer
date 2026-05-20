from django.apps import AppConfig


class HealthPassConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.health_pass"
    verbose_name = "Pass sanitaires (QR)"
