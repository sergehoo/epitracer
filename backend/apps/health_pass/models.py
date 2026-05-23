"""Pass sanitaire numérique avec QR signé cryptographiquement (Ed25519)."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from apps.core.utils import short_id


class HealthPassStatus(models.TextChoices):
    ACTIVE = "active", _("Actif")
    EXPIRED = "expired", _("Expiré")
    REVOKED = "revoked", _("Révoqué")
    BLACKLISTED = "blacklisted", _("Liste noire")


class HealthPass(BaseModel):
    pass_number = models.CharField(max_length=24, unique=True, editable=False, db_index=True)
    traveler = models.ForeignKey(
        "travelers.Traveler", on_delete=models.CASCADE, related_name="health_passes"
    )
    disease = models.ForeignKey(
        "diseases.Disease", null=True, blank=True, on_delete=models.SET_NULL, related_name="passes"
    )
    investigation_ref = models.CharField(max_length=24, blank=True, db_index=True)

    status = models.CharField(
        max_length=20, choices=HealthPassStatus.choices, default=HealthPassStatus.ACTIVE, db_index=True
    )
    risk_level = models.CharField(max_length=20, blank=True)
    risk_score = models.PositiveSmallIntegerField(default=0)

    issued_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)

    # Données signées
    payload = models.JSONField(default=dict)
    signature_b64 = models.TextField(blank=True)
    signing_kid = models.CharField(max_length=32, blank=True, help_text=_("Identifiant de la clé utilisée."))

    # Révocation
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="revoked_passes",
    )
    revocation_reason = models.CharField(max_length=200, blank=True)

    qr_image = models.ImageField(upload_to="passes/qr/", null=True, blank=True)
    pdf_file = models.FileField(upload_to="passes/pdf/", null=True, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Pass sanitaire")
        verbose_name_plural = _("Pass sanitaires")
        indexes = [
            models.Index(fields=["status", "expires_at"]),
        ]

    def save(self, *args, **kwargs):
        if not self.pass_number:
            self.pass_number = short_id("PASS", length=10)
        super().save(*args, **kwargs)

    @property
    def is_valid(self) -> bool:
        if self.status != HealthPassStatus.ACTIVE:
            return False
        return self.expires_at > timezone.now()

    def __str__(self) -> str:
        traveler_str = (
            f"{self.traveler.last_name} {self.traveler.first_name}"
            if self.traveler_id else "?"
        )
        return f"{self.pass_number} — {traveler_str}"


class PassVerificationLog(BaseModel):
    """Trace de chaque vérification de QR (utile pour analyse de flux + audit)."""

    pass_obj = models.ForeignKey(
        HealthPass, null=True, blank=True, on_delete=models.SET_NULL, related_name="verifications"
    )
    pass_number = models.CharField(max_length=24, db_index=True)
    verified_at = models.DateTimeField(auto_now_add=True, db_index=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="pass_verifications",
    )
    entry_point = models.ForeignKey(
        "geo.EntryPoint", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="pass_verifications",
    )
    is_valid = models.BooleanField()
    reason = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = _("Vérification de pass")
        verbose_name_plural = _("Vérifications de pass")
        ordering = ["-verified_at"]


class PassBlacklistEntry(BaseModel):
    """Numéro de pass blacklisté (volé, fraude, etc.)."""

    pass_number = models.CharField(max_length=24, unique=True, db_index=True)
    reason = models.CharField(max_length=200)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="blacklisted_passes",
    )

    class Meta(BaseModel.Meta):
        verbose_name = _("Pass en liste noire")
        verbose_name_plural = _("Liste noire")
