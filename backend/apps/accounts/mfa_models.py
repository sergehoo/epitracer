"""MFA par email — modèle OTP à 6 chiffres avec expiration courte.

Sécurité :
    - Code stocké HASHÉ (SHA-256), jamais en clair
    - Expiration 10 minutes
    - Maximum 5 tentatives de validation par code
    - Invalidation automatique des anciens codes lors d'une nouvelle génération
    - IP + User-Agent tracés pour audit
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class EmailOtpCode(BaseModel):
    """Code OTP à 6 chiffres envoyé par email pour la MFA."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="email_otp_codes",
    )
    code_hash = models.CharField(_("hash du code"), max_length=128, db_index=True)
    expires_at = models.DateTimeField(_("expire à"), db_index=True)
    attempts = models.PositiveSmallIntegerField(_("tentatives"), default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    used_at = models.DateTimeField(_("utilisé le"), null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = _("Code OTP email")
        verbose_name_plural = _("Codes OTP email")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self) -> str:
        return f"OTP #{self.pk} → {self.user.email}"

    @property
    def is_valid(self) -> bool:
        return (
            self.used_at is None
            and self.expires_at > timezone.now()
            and self.attempts < self.max_attempts
        )

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()

    @property
    def attempts_remaining(self) -> int:
        return max(0, self.max_attempts - self.attempts)
