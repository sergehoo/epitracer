"""Settings pour pytest - rapide, sans services externes."""
from .base import *  # noqa: F401,F403

DEBUG = False
SECRET_KEY = "test-secret-key-pytest-only"

# DB Postgres/PostGIS de test (utilise le service db de docker-compose)
# Pour tests en CI sans PostGIS, remplacer par spatialite + sqlite si nécessaire.

# Désactiver throttling pendant les tests
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = ()  # noqa: F405

# Email en mémoire
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Channels in-memory pour les tests
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Celery en mode "eager" (exécution synchrone)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Hashers rapides pour tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
