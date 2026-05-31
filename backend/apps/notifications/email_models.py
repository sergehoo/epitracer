"""Modèles dédiés au système email multi-expéditeur EpiTrace.

Séparation stricte :
    - SenderProfile.PUBLIC   → infos@destinationci.com   (voyageurs / grand public)
    - SenderProfile.INTERNAL → inhp@veillesanitaire.com  (admin / agents / système)

Le routage est imposé côté backend : pour un EmailType donné, on récupère
le SenderProfile via EMAIL_TYPE_TO_SENDER. Le frontend N'A JAMAIS le
droit de choisir l'adresse d'expédition.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


# ===========================================================================
# ENUMS
# ===========================================================================

class EmailType(models.TextChoices):
    """Types d'emails métier — déterminent quel expéditeur est utilisé.

    PUBLIC (voyageurs) :  infos@destinationci.com
    INTERNAL (admin/agents) : inhp@veillesanitaire.com
    """
    # ── Public / voyageurs ──────────────────────────────────────────────
    TRAVELER_INFO = "traveler_info", _("Information voyageur")
    TRAVELER_CAMPAIGN = "traveler_campaign", _("Campagne de sensibilisation")
    HEALTH_NOTIFICATION = "health_notification", _("Notification sanitaire")
    FOLLOWUP_REMINDER = "followup_reminder", _("Rappel de suivi")
    PASS_CONFIRMATION = "pass_confirmation", _("Confirmation de pass sanitaire")
    PUBLIC_ASSISTANCE = "public_assistance", _("Assistance publique")
    TRAVELER_ALERT = "traveler_alert", _("Alerte voyageur")
    FOLLOWUP_COMPLETED = "followup_completed", _("Fin de suivi 21 jours")

    # ── Interne / administration ────────────────────────────────────────
    ADMIN_ACCOUNT_CREATED = "admin_account_created", _("Création compte admin/agent")
    ADMIN_PASSWORD_RESET = "admin_password_reset", _("Réinitialisation mot de passe")
    ADMIN_SECURITY_ALERT = "admin_security_alert", _("Alerte sécurité admin")
    STAFF_NOTIFICATION = "staff_notification", _("Notification agent")
    INTERNAL_REPORT = "internal_report", _("Rapport interne")
    MFA_NOTIFICATION = "mfa_notification", _("Notification MFA")
    USER_INVITATION = "user_invitation", _("Invitation utilisateur")
    SYSTEM_ALERT = "system_alert", _("Alerte système")


class SenderProfileCode(models.TextChoices):
    """Codes des profils d'expédition disponibles."""
    PUBLIC = "public", _("Public — voyageurs (destinationci.com)")
    INTERNAL = "internal", _("Interne — administration (veillesanitaire.com)")


class UsageScope(models.TextChoices):
    PUBLIC_TRAVELER = "public_traveler", _("Voyageurs / grand public")
    INTERNAL_ADMIN = "internal_admin", _("Administration interne")


class EmailStatus(models.TextChoices):
    PENDING = "pending", _("En attente")
    QUEUED = "queued", _("En file")
    SENT = "sent", _("Envoyé")
    DELIVERED = "delivered", _("Délivré")
    BOUNCED = "bounced", _("Rejeté (bounce)")
    FAILED = "failed", _("Échec")
    CANCELLED = "cancelled", _("Annulé")
    OPENED = "opened", _("Ouvert")
    CLICKED = "clicked", _("Cliqué")


# ===========================================================================
# MAPPING : EmailType → SenderProfile (règle métier figée)
# ===========================================================================

# Liste des types autorisés à utiliser le profil PUBLIC (voyageurs).
PUBLIC_EMAIL_TYPES = {
    EmailType.TRAVELER_INFO,
    EmailType.TRAVELER_CAMPAIGN,
    EmailType.HEALTH_NOTIFICATION,
    EmailType.FOLLOWUP_REMINDER,
    EmailType.PASS_CONFIRMATION,
    EmailType.PUBLIC_ASSISTANCE,
    EmailType.TRAVELER_ALERT,
    EmailType.FOLLOWUP_COMPLETED,
}

# Liste des types autorisés à utiliser le profil INTERNAL (administration).
INTERNAL_EMAIL_TYPES = {
    EmailType.ADMIN_ACCOUNT_CREATED,
    EmailType.ADMIN_PASSWORD_RESET,
    EmailType.ADMIN_SECURITY_ALERT,
    EmailType.STAFF_NOTIFICATION,
    EmailType.INTERNAL_REPORT,
    EmailType.MFA_NOTIFICATION,
    EmailType.USER_INVITATION,
    EmailType.SYSTEM_ALERT,
}


def get_sender_profile_code_for_type(email_type: str) -> str:
    """Retourne le code du SenderProfile à utiliser pour ce type d'email.

    Lève ValueError si le type est inconnu — sécurité défensive pour
    s'assurer que toute nouvelle valeur passe explicitement par la review.
    """
    if email_type in PUBLIC_EMAIL_TYPES:
        return SenderProfileCode.PUBLIC
    if email_type in INTERNAL_EMAIL_TYPES:
        return SenderProfileCode.INTERNAL
    raise ValueError(
        f"EmailType `{email_type}` n'est rattaché à aucun SenderProfile. "
        f"Ajouter sa catégorisation dans PUBLIC_EMAIL_TYPES ou INTERNAL_EMAIL_TYPES."
    )


# ===========================================================================
# MODÈLES
# ===========================================================================

class SenderProfile(BaseModel):
    """Profil d'expédition email — paramètres SMTP + identité visible.

    Chargés en DB pour permettre l'édition par le Super Admin, MAIS les
    secrets (mots de passe SMTP, clés AWS) restent dans l'env. Ce modèle
    ne stocke QUE l'identité publique (from, reply-to, nom affiché).
    """
    code = models.CharField(
        _("code"), max_length=40, unique=True, choices=SenderProfileCode.choices,
    )
    name = models.CharField(_("nom interne"), max_length=120)
    from_address = models.EmailField(_("adresse d'expédition"))
    from_name = models.CharField(_("nom affiché"), max_length=120)
    reply_to = models.EmailField(_("adresse de réponse (Reply-To)"), blank=True)
    usage_scope = models.CharField(
        _("portée d'usage"), max_length=20, choices=UsageScope.choices,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Profil d'expéditeur email")
        verbose_name_plural = _("Profils d'expéditeur email")
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.from_name} <{self.from_address}>"

    @property
    def formatted_from(self) -> str:
        """Adresse complète au format `Nom <email>`."""
        if self.from_name:
            return f"{self.from_name} <{self.from_address}>"
        return self.from_address


class EmailTemplate(BaseModel):
    """Template d'email rendu côté serveur (HTML + texte fallback)."""
    code = models.CharField(_("code unique"), max_length=80, unique=True, db_index=True)
    name = models.CharField(_("nom"), max_length=160)
    email_type = models.CharField(
        _("type d'email"), max_length=40, choices=EmailType.choices, db_index=True,
    )
    subject = models.CharField(_("sujet"), max_length=300)
    body_html = models.TextField(_("corps HTML"))
    body_text = models.TextField(_("corps texte (fallback)"), blank=True)
    sender_profile = models.ForeignKey(
        SenderProfile, on_delete=models.PROTECT, related_name="templates",
        null=True, blank=True,
        help_text=_("Si vide, déterminé automatiquement par email_type."),
    )
    variables_schema = models.JSONField(
        _("variables attendues (JSON Schema light)"),
        default=dict, blank=True,
        help_text=_('Ex: {"full_name": "string", "pass_number": "string"}'),
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Template email")
        verbose_name_plural = _("Templates email")
        ordering = ["email_type", "code"]

    def __str__(self) -> str:
        return f"{self.code} ({self.email_type})"

    def resolved_sender(self):
        """Retourne le SenderProfile à utiliser : champ explicite OU mapping."""
        if self.sender_profile_id and self.sender_profile.is_active:
            return self.sender_profile
        code = get_sender_profile_code_for_type(self.email_type)
        return SenderProfile.objects.filter(code=code, is_active=True).first()


class EmailLog(BaseModel):
    """Journal d'envoi email — un enregistrement par destinataire."""
    recipient = models.EmailField(_("destinataire"), db_index=True)
    email_type = models.CharField(
        _("type"), max_length=40, choices=EmailType.choices, db_index=True,
    )
    sender_address = models.EmailField(_("adresse expéditeur"))
    subject = models.CharField(_("sujet"), max_length=300)
    body_html = models.TextField(_("corps HTML envoyé"), blank=True)
    body_text = models.TextField(_("corps texte envoyé"), blank=True)
    status = models.CharField(
        _("statut"), max_length=20, choices=EmailStatus.choices,
        default=EmailStatus.PENDING, db_index=True,
    )
    provider_message_id = models.CharField(_("ID provider"), max_length=200, blank=True)
    error_message = models.TextField(_("erreur"), blank=True)
    retry_count = models.PositiveSmallIntegerField(_("retries"), default=0)
    max_retries = models.PositiveSmallIntegerField(default=3)
    template = models.ForeignKey(
        EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="email_logs",
    )
    context = models.JSONField(_("variables contexte"), default=dict, blank=True)

    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="emails_received_logs",
    )
    related_traveler = models.ForeignKey(
        "travelers.Traveler", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="emails_received_logs",
    )
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="emails_sent_logs",
    )

    sent_at = models.DateTimeField(null=True, blank=True, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Journal email")
        verbose_name_plural = _("Journal des emails")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["email_type", "-created_at"]),
            models.Index(fields=["recipient"]),
        ]

    def __str__(self) -> str:
        return f"[{self.email_type}] → {self.recipient} ({self.status})"

    @property
    def masked_recipient(self) -> str:
        """Email masqué pour les logs : `j***n@example.com`."""
        if "@" not in self.recipient:
            return self.recipient
        local, domain = self.recipient.split("@", 1)
        if len(local) <= 2:
            masked = local[0] + "*"
        else:
            masked = local[0] + "*" * (len(local) - 2) + local[-1]
        return f"{masked}@{domain}"


class PasswordResetToken(BaseModel):
    """Token à usage unique pour réinitialisation de mot de passe.

    Lié à l'envoi d'email ADMIN_PASSWORD_RESET — fournit une URL signée
    avec expiration courte (24h par défaut), invalidée après usage.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token_hash = models.CharField(max_length=128, db_index=True, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = _("Token reset password")
        verbose_name_plural = _("Tokens reset password")
        ordering = ["-created_at"]

    @property
    def is_valid(self) -> bool:
        from django.utils import timezone
        return self.used_at is None and self.expires_at > timezone.now()
