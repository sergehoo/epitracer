"""Configuration Celery pour EpidemiTracker."""
from __future__ import annotations

import os

from celery import Celery
from celery.signals import setup_logging  # noqa: F401

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

app = Celery("epidemitracker")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):  # pragma: no cover
    print(f"Request: {self.request!r}")
