"""Modèles spécifiques à l'API mobile EpiTrace / Mon Pass Sanitaire.

Couvre ce qui n'existe pas déjà côté backend :
  - MobileDevice : tokens push FCM par appareil utilisateur
  - Vaccination : carnet vaccinal numérique
  - AssistanceRequest : demande d'appel agent INHP
  - LocationShare : partage volontaire one-shot de position

Les pass sanitaires et le suivi 21j réutilisent les modèles existants
(apps.health_pass, apps.companion).
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


# ---------------------------------------------------------------------------
# Push / FCM
# ---------------------------------------------------------------------------
class DevicePlatform(models.TextChoices):
    ANDROID = "android", _("Android")
    IOS = "ios", _("iOS")
    WEB = "web", _("Web (PWA)")


class MobileDevice(BaseModel):
    """Représente un appareil mobile enregistré pour les notifications push."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mobile_devices",
    )
    fcm_token = models.CharField(_("token FCM"), max_length=512, unique=True)
    platform = models.CharField(
        max_length=20, choices=DevicePlatform.choices, default=DevicePlatform.ANDROID,
    )
    device_id = models.CharField(
        _("identifiant appareil"), max_length=200, blank=True,
        help_text=_("ANDROID_ID ou identifierForVendor — non identifiant utilisateur"),
    )
    app_version = models.CharField(max_length=40, blank=True)
    os_version = models.CharField(max_length=40, blank=True)
    locale = models.CharField(max_length=20, default="fr-CI")
    last_seen_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Appareil mobile")
        verbose_name_plural = _("Appareils mobiles")
        ordering = ["-last_seen_at"]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["fcm_token"]),
        ]

    def __str__(self) -> str:
        return f"{self.platform} · {self.user.email} ({self.fcm_token[:12]}…)"


# ---------------------------------------------------------------------------
# Carnet vaccinal numérique
# ---------------------------------------------------------------------------
class Vaccination(BaseModel):
    """Entrée du carnet de vaccination personnel."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vaccinations",
    )
    disease_code = models.CharField(
        _("code maladie"), max_length=40, db_index=True,
        help_text=_("ex: YELLOW_FEVER, COVID19, EBOLA, MPOX, HEPATITIS_B"),
    )
    disease_name = models.CharField(_("nom maladie"), max_length=120)
    vaccine_name = models.CharField(_("nom du vaccin"), max_length=160)
    manufacturer = models.CharField(_("fabricant / labo"), max_length=160, blank=True)
    lot_number = models.CharField(_("n° de lot"), max_length=80, blank=True)
    administered_at = models.DateField(_("date d'administration"), db_index=True)
    next_dose_at = models.DateField(_("prochaine dose"), null=True, blank=True)
    dose_number = models.PositiveSmallIntegerField(_("n° de dose"), default=1)
    total_doses = models.PositiveSmallIntegerField(_("doses totales"), default=1)
    center_name = models.CharField(_("centre de vaccination"), max_length=200, blank=True)
    country_code = models.CharField(_("pays"), max_length=2, default="CI")
    certificate_pdf = models.FileField(
        upload_to="vaccinations/certificates/%Y/%m/",
        null=True, blank=True,
    )
    qr_payload = models.TextField(blank=True, help_text=_("Payload QR officiel si fourni"))
    verified = models.BooleanField(
        default=False,
        help_text=_("Validé par un agent INHP / centre agréé"),
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Vaccination")
        verbose_name_plural = _("Carnet vaccinal")
        ordering = ["-administered_at", "-created_at"]
        indexes = [
            models.Index(fields=["user", "-administered_at"]),
            models.Index(fields=["disease_code"]),
        ]

    def __str__(self) -> str:
        return f"{self.disease_name} · {self.vaccine_name} ({self.administered_at})"


# ---------------------------------------------------------------------------
# Demandes d'assistance (appel rappel agent INHP)
# ---------------------------------------------------------------------------
class AssistanceRequestStatus(models.TextChoices):
    PENDING = "pending", _("En attente")
    ASSIGNED = "assigned", _("Assignée")
    CONTACTED = "contacted", _("Voyageur contacté")
    CLOSED = "closed", _("Clôturée")


class AssistanceRequest(BaseModel):
    """Le voyageur demande qu'un agent INHP le rappelle."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assistance_requests",
    )
    reason = models.CharField(_("motif"), max_length=200, blank=True)
    message = models.TextField(_("message"), blank=True)
    callback_phone = models.CharField(_("téléphone de rappel"), max_length=32)
    preferred_time = models.CharField(_("plage horaire préférée"), max_length=80, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=AssistanceRequestStatus.choices,
        default=AssistanceRequestStatus.PENDING, db_index=True,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assistance_assignments",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_note = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Demande d'assistance")
        verbose_name_plural = _("Demandes d'assistance")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self) -> str:
        return f"#{self.pk} · {self.user.email} · {self.status}"


# ---------------------------------------------------------------------------
# Partage volontaire de position (one-shot)
# ---------------------------------------------------------------------------
class LocationShare(BaseModel):
    """Partage explicite et ponctuel de position par un utilisateur.

    Distinct de TravelerLocationPing (apps.companion) qui est dans le cadre
    du suivi PWA voyageur. Ici, c'est un partage manuel depuis l'app mobile.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="location_shares",
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    accuracy_m = models.FloatField(null=True, blank=True)
    context = models.CharField(
        _("contexte"), max_length=60, blank=True,
        help_text=_("ex: 'assistance_request', 'checkin', 'manual'"),
    )
    shared_with_agent = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="shared_locations_received",
    )

    class Meta:
        verbose_name = _("Partage de position")
        verbose_name_plural = _("Partages de position")
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        return f"{self.user.email} · {self.latitude:.4f}, {self.longitude:.4f}"
