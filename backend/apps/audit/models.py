"""Modèle d'audit applicatif (en complément de simple_history sur les entités sensibles)."""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from apps.core.models import TimestampedModel


class AuditAction(models.TextChoices):
    CREATE = "create", "Création"
    UPDATE = "update", "Modification"
    DELETE = "delete", "Suppression"
    READ = "read", "Lecture"
    LOGIN = "login", "Connexion"
    LOGOUT = "logout", "Déconnexion"
    EXPORT = "export", "Export"
    QR_GENERATE = "qr_generate", "Génération QR"
    QR_VERIFY = "qr_verify", "Vérification QR"
    QR_REVOKE = "qr_revoke", "Révocation QR"
    QUARANTINE_START = "quarantine_start", "Démarrage quarantaine"
    QUARANTINE_END = "quarantine_end", "Fin quarantaine"
    ALERT = "alert", "Alerte"
    OTHER = "other", "Autre"


class AuditLog(TimestampedModel):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_logs"
    )
    action = models.CharField(max_length=40, choices=AuditAction.choices, db_index=True)
    target_ct = models.ForeignKey(ContentType, null=True, blank=True, on_delete=models.SET_NULL)
    target_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    target = GenericForeignKey("target_ct", "target_id")
    summary = models.CharField(max_length=255)
    payload = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=400, blank=True)
    request_id = models.CharField(max_length=64, blank=True, db_index=True)

    class Meta:
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journaux d'audit"
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["target_ct", "target_id"]),
        ]

    def __str__(self) -> str:
        return f"[{self.action}] {self.summary}"
