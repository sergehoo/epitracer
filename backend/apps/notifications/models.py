"""Modèles de notifications : templates + journal d'envoi + config providers."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class Channel(models.TextChoices):
    SMS = "sms", _("SMS")
    EMAIL = "email", _("Email")
    WHATSAPP = "whatsapp", _("WhatsApp")
    PUSH = "push", _("Push notification")
    TELEGRAM = "telegram", _("Telegram")
    INTERNAL = "internal", _("Notification interne")


class Provider(models.TextChoices):
    """Fournisseurs d'envoi supportés."""
    ORANGE_CI = "orange_ci", _("Orange Côte d'Ivoire")
    TWILIO = "twilio", _("Twilio")
    META_WHATSAPP = "meta_whatsapp", _("Meta WhatsApp Cloud API")
    SYSTEM = "system", _("Système (stub)")
    SMTP = "smtp", _("SMTP / Email")
    FCM = "fcm", _("Firebase Cloud Messaging")
    TELEGRAM_BOT = "telegram_bot", _("Telegram Bot API")


class NotificationStatus(models.TextChoices):
    DRAFT = "draft", _("Brouillon")
    PENDING = "pending", _("En attente")
    QUEUED = "queued", _("En file")
    SENT = "sent", _("Envoyée")
    DELIVERED = "delivered", _("Délivrée")
    FAILED = "failed", _("Échec")
    CANCELLED = "cancelled", _("Annulée")
    READ = "read", _("Lue")


class Direction(models.TextChoices):
    OUTBOUND = "outbound", _("Sortante (admin → voyageur)")
    INBOUND = "inbound", _("Entrante (voyageur → système)")


class MessageType(models.TextChoices):
    """Catégorise les notifications pour reporting et permissions."""
    AUTOMATIC_REMINDER = "automatic_reminder", _("Rappel automatique")
    MANUAL_MESSAGE = "manual_message", _("Message manuel agent")
    SYMPTOM_ALERT = "symptom_alert", _("Alerte symptômes")
    ASSISTANCE = "assistance", _("Demande d'assistance")
    FOLLOWUP_REMINDER = "followup_reminder", _("Rappel suivi 21j")
    FOLLOWUP_COMPLETED = "followup_completed", _("Fin de suivi")
    ADMIN_NOTICE = "admin_notice", _("Notice administrateur")
    LOCATION_REQUEST = "location_request", _("Demande de position")
    EBOLA_PREVENTION = "ebola_prevention", _("Prévention Ebola")
    OTHER = "other", _("Autre")


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
class NotificationTemplate(BaseModel):
    code = models.SlugField(max_length=80, unique=True, db_index=True)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField(help_text=_("Variables {var} interpolées avec str.format(**context)."))
    channels = models.JSONField(default=list, help_text=_("Canaux supportés par ce template."))
    is_active = models.BooleanField(default=True)
    # Optionnel : associer une maladie pour filtrer côté UI
    disease = models.ForeignKey(
        "diseases.Disease", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="notification_templates",
    )
    # Schema documentaire des variables attendues (pour la modal d'édition)
    variables_schema = models.JSONField(
        default=dict, blank=True,
        help_text=_("Schema des variables disponibles dans le template. Ex: {'first_name': 'str', 'checkin_link': 'url'}"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="created_templates",
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Modèle de notification")
        verbose_name_plural = _("Modèles de notification")

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


# ---------------------------------------------------------------------------
# Notification (instance d'envoi)
# ---------------------------------------------------------------------------
class Notification(BaseModel):
    """Une notification envoyée (ou en attente d'envoi).

    Stocke à la fois les notifications automatiques (rappels Celery) et
    les messages manuels saisis par les agents depuis le dashboard.
    """

    channel = models.CharField(max_length=20, choices=Channel.choices, db_index=True)
    template = models.ForeignKey(
        NotificationTemplate, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="notifications",
    )

    # ── Destinataire ──
    traveler = models.ForeignKey(
        "travelers.Traveler", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="notifications",
    )
    recipient = models.CharField(
        max_length=200,
        help_text=_("Adresse brute saisie (téléphone, email, FCM token)."),
    )
    normalized_phone = models.CharField(
        max_length=24, blank=True, db_index=True,
        help_text=_("Numéro normalisé au format E.164 (+225XXXXXXXXXX)."),
    )

    # ── Contenu ──
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    context = models.JSONField(default=dict, blank=True)

    # ── Classification ──
    direction = models.CharField(
        max_length=12, choices=Direction.choices, default=Direction.OUTBOUND, db_index=True,
    )
    message_type = models.CharField(
        max_length=32, choices=MessageType.choices, default=MessageType.AUTOMATIC_REMINDER, db_index=True,
    )

    # ── État ──
    status = models.CharField(
        max_length=20, choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING, db_index=True,
    )
    provider = models.CharField(max_length=40, choices=Provider.choices, blank=True, db_index=True)
    provider_message_id = models.CharField(
        max_length=200, blank=True, db_index=True,
        help_text=_("ID de message côté fournisseur (utilisé pour les webhooks de statut)."),
    )
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    max_retries = models.PositiveSmallIntegerField(default=3)

    # ── Audit & timestamps ──
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="sent_notifications",
        help_text=_("Agent qui a envoyé le message (null pour envois automatiques)."),
    )
    queued_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    # Métadonnées libres (numéro masqué, IP, payload provider, etc.)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        indexes = [
            models.Index(fields=["channel", "status"]),
            models.Index(fields=["traveler", "-created_at"]),
            models.Index(fields=["provider_message_id"]),
        ]

    def __str__(self) -> str:
        return f"[{self.channel}/{self.provider or '?'}] {self.recipient[:30]} · {self.status}"

    @property
    def masked_recipient(self) -> str:
        """Numéro masqué pour les logs : +2250700000000 → +22507****0000."""
        r = self.normalized_phone or self.recipient
        if not r:
            return ""
        if r.startswith("+") and len(r) >= 11:
            return r[:6] + "****" + r[-4:]
        return r


# ---------------------------------------------------------------------------
# Provider config (réglages par fournisseur, modifiable sans redéploiement)
# ---------------------------------------------------------------------------
class NotificationProviderConfig(BaseModel):
    """Configuration d'un fournisseur d'envoi.

    Permet d'activer/désactiver un provider sans redéploiement et de
    définir une priorité de routage.
    """

    provider = models.CharField(max_length=40, choices=Provider.choices, db_index=True)
    channel = models.CharField(max_length=20, choices=Channel.choices, db_index=True)
    is_enabled = models.BooleanField(default=True, db_index=True)
    priority = models.PositiveSmallIntegerField(
        default=100,
        help_text=_("Ordre de préférence si plusieurs providers couvrent le même canal. Plus bas = prioritaire."),
    )
    country_code = models.CharField(
        max_length=4, blank=True, db_index=True,
        help_text=_("Code pays ISO (ex: CI) pour routage géographique. Vide = international."),
    )
    sender_name = models.CharField(
        max_length=40, blank=True,
        help_text=_("Nom d'expéditeur affiché (Sender ID Orange CI, ou numéro Twilio)."),
    )
    metadata = models.JSONField(
        default=dict, blank=True,
        help_text=_("Réglages spécifiques (timeout, quotas, etc.)."),
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Configuration fournisseur")
        verbose_name_plural = _("Configurations fournisseurs")
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "channel", "country_code"],
                name="uniq_provider_per_channel_country",
            ),
        ]
        ordering = ["channel", "priority"]

    def __str__(self) -> str:
        scope = self.country_code or "intl"
        state = "✓" if self.is_enabled else "✗"
        return f"{state} {self.provider} · {self.channel} ({scope})"


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------
class NotificationAuditAction(models.TextChoices):
    CREATE = "create", _("Création")
    SEND = "send", _("Envoi")
    RETRY = "retry", _("Réessai")
    CANCEL = "cancel", _("Annulation")
    DELIVERED = "delivered", _("Reçu confirmé")
    FAILED = "failed", _("Échec")
    VIEW = "view", _("Consultation")


class NotificationAuditLog(BaseModel):
    """Trace de chaque action sur une notification (qui, quand, depuis quelle IP)."""

    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="audit_logs",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="notification_actions",
    )
    action = models.CharField(max_length=20, choices=NotificationAuditAction.choices, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Journal de notification")
        verbose_name_plural = _("Journaux de notification")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["notification", "-created_at"])]

    def __str__(self) -> str:
        actor = self.actor.email if self.actor_id else "system"
        return f"[{self.action}] notif#{self.notification_id} by {actor}"


# ---------------------------------------------------------------------------
# Telegram — abonnement chat_id ↔ traveler
# ---------------------------------------------------------------------------
class TelegramSubscription(BaseModel):
    """Association entre un compte Telegram (chat_id) et un voyageur.

    Cycle de vie :
      1. Le voyageur ouvre `t.me/<bot>?start=<TRV-XXX>` (deep link).
      2. Le webhook Telegram reçoit `/start TRV-XXX` avec le chat_id.
      3. On crée/met à jour cet objet (unique par chat_id).
      4. À la désinscription (message `/stop`) → is_active=False.

    Note : `chat_id` est unique — un compte Telegram ne peut être lié qu'à
    un seul voyageur. Un voyageur peut par contre avoir plusieurs chats
    (téléphone + tablette) — chaque `chat_id` distinct = ligne distincte.
    """
    traveler = models.ForeignKey(
        "travelers.Traveler",
        on_delete=models.CASCADE,
        related_name="telegram_subs",
    )
    chat_id = models.CharField(
        max_length=64, unique=True, db_index=True,
        help_text=_("ID de chat Telegram (int stocké en str pour éviter la limite bigint)."),
    )
    username = models.CharField(
        max_length=64, blank=True,
        help_text=_("@username Telegram du voyageur, s'il en a un."),
    )
    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    language_code = models.CharField(max_length=8, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    linked_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Abonnement Telegram")
        verbose_name_plural = _("Abonnements Telegram")
        ordering = ["-linked_at"]
        indexes = [
            models.Index(fields=["traveler", "is_active"]),
        ]

    def __str__(self) -> str:
        tag = f"@{self.username}" if self.username else self.chat_id
        return f"Telegram {tag} → {self.traveler_id}"


# ---------------------------------------------------------------------------
# Modèles email multi-expéditeur — importés depuis email_models.py pour que
# Django les détecte automatiquement et applique les migrations.
# ---------------------------------------------------------------------------
from .email_models import (  # noqa: E402, F401
    EmailLog,
    EmailStatus,
    EmailTemplate,
    EmailType,
    INTERNAL_EMAIL_TYPES,
    PUBLIC_EMAIL_TYPES,
    PasswordResetToken,
    SenderProfile,
    SenderProfileCode,
    UsageScope,
    get_sender_profile_code_for_type,
)
