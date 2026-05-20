from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Comptes & RBAC"

    def ready(self):
        # Importer les signaux (audit auth, etc.)
        from . import signals  # noqa: F401
