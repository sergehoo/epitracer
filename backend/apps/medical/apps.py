from django.apps import AppConfig


class MedicalConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.medical"
    verbose_name = "Suivi médical & laboratoire"

    def ready(self) -> None:  # pragma: no cover - import side effects
        # Import des handlers de signaux (auto-log FollowUpAction).
        from . import signals  # noqa: F401
