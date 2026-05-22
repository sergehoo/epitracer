from django.apps import AppConfig


class CompanionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.companion"
    verbose_name = "Accompagnement voyageur (PWA, push, géoloc, consentement)"
