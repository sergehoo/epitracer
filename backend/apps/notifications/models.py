"""Modèles de notifications : templates + journal d'envoi."""
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Channel(models.TextChoices):
    SMS = "sms", _("SMS")
    EMAIL = "email", _("Email")
    WHATSAPP = "whatsapp", _("WhatsApp")
    PUSH = "push", _("Push notification")
    INTERNAL = "internal", _("Notification interne")


class NotificationStatus(models.TextChoices):
    PENDING = "pending", _("En attente")
    SENT = "sent", _("Envoyée")
    DELIVERED = "delivered", _("Délivrée")
    FAILED = "failed", _("Échec")
    READ = "read", _("Lue")


class NotificationTemplate(BaseModel):
    code = models.SlugField(max_length=80, unique=True, db_index=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField(help_text=_("Variables {var} interpolées avec str.format(**context)."))
    channels = models.JSONField(default=list, help_text=_("Canaux supportés par ce template."))
    is_active = models.BooleanField(default=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Modèle de notification")
        verbose_name_plural = _("Modèles de notification")


class Notification(BaseModel):
    channel = models.CharField(max_length=20, choices=Channel.choices, db_index=True)
    template = models.ForeignKey(
        NotificationTemplate, null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications"
    )
    recipient = models.CharField(max_length=200, help_text=_("Téléphone, email, FCM token, etc."))
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    context = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20, choices=NotificationStatus.choices, default=NotificationStatus.PENDING, db_index=True
    )
    provider = models.CharField(max_length=40, blank=True)
    provider_id = models.CharField(max_length=200, blank=True)
    error = models.TextField(blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        indexes = [
            models.Index(fields=["channel", "status"]),
        ]
