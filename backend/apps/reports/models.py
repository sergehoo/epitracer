"""Modèles du sous-module rapports automatisés.

Distincts des vues d'export à la volée dans views.py :
  - AutomatedReportSchedule  : configuration de planification (Celery Beat)
  - AutomatedReportRecipient : liste d'abonnés SMS / Email
  - GeneratedReport          : rapport archivé (PDF + Excel + résumé JSON)
  - ReportDeliveryLog        : traçabilité de chaque tentative d'envoi
"""
from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


# ============================================================================
# Enums
# ============================================================================
class ReportType(models.TextChoices):
    WEEKLY = "weekly", _("Hebdomadaire")
    MONTHLY = "monthly", _("Mensuel")
    QUARTERLY = "quarterly", _("Trimestriel")
    ADHOC = "adhoc", _("Ponctuel")


class ReportStatus(models.TextChoices):
    PENDING = "pending", _("En attente")
    GENERATING = "generating", _("Génération en cours")
    READY = "ready", _("Prêt")
    FAILED = "failed", _("Échec")
    ARCHIVED = "archived", _("Archivé")


class PreferredChannel(models.TextChoices):
    SMS = "sms", _("SMS uniquement")
    EMAIL = "email", _("Email uniquement")
    BOTH = "both", _("SMS + Email")


class DeliveryChannel(models.TextChoices):
    SMS = "sms", _("SMS")
    WHATSAPP = "whatsapp", _("WhatsApp")
    EMAIL = "email", _("Email")


class DeliveryStatus(models.TextChoices):
    QUEUED = "queued", _("En file")
    SENT = "sent", _("Envoyé")
    DELIVERED = "delivered", _("Délivré")
    FAILED = "failed", _("Échec")
    PERMANENTLY_FAILED = "permanently_failed", _("Échec définitif")
    RETRYING = "retrying", _("Réessai en cours")


class Frequency(models.TextChoices):
    DAILY = "daily", _("Quotidien")
    WEEKLY = "weekly", _("Hebdomadaire")
    MONTHLY = "monthly", _("Mensuel")


class Weekday(models.IntegerChoices):
    """ISO 8601 — 1 = lundi ... 7 = dimanche."""
    MONDAY = 1, _("Lundi")
    TUESDAY = 2, _("Mardi")
    WEDNESDAY = 3, _("Mercredi")
    THURSDAY = 4, _("Jeudi")
    FRIDAY = 5, _("Vendredi")
    SATURDAY = 6, _("Samedi")
    SUNDAY = 7, _("Dimanche")


# ============================================================================
# 1. AutomatedReportSchedule — configuration cron du rapport
# ============================================================================
class AutomatedReportSchedule(BaseModel):
    """Une planification par type de rapport (généralement 1 seule active
    pour WEEKLY, mais on garde le modèle N pour permettre plusieurs cadences
    et le retour arrière).

    Le Super Admin peut modifier le jour/heure/timezone depuis l'admin ou
    l'endpoint DRF ; la tâche Celery Beat lit ce modèle au boot.
    """
    name = models.CharField(
        max_length=120,
        help_text=_("Étiquette humaine, ex. 'Rapport hebdomadaire INHP'."),
    )
    report_type = models.CharField(
        max_length=20, choices=ReportType.choices, default=ReportType.WEEKLY,
    )
    frequency = models.CharField(
        max_length=20, choices=Frequency.choices, default=Frequency.WEEKLY,
    )
    weekday = models.IntegerField(
        choices=Weekday.choices,
        default=Weekday.MONDAY,
        help_text=_("Jour de la semaine où le rapport est généré (ISO 8601)."),
    )
    time = models.TimeField(
        default="08:00",
        help_text=_("Heure locale de génération."),
    )
    timezone = models.CharField(
        max_length=64,
        default="Africa/Abidjan",
        help_text=_("Fuseau IANA. Doit correspondre à CELERY_TIMEZONE."),
    )
    is_active = models.BooleanField(default=True, db_index=True)
    include_pdf = models.BooleanField(default=True)
    include_excel = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="report_schedules_created",
    )

    class Meta:
        verbose_name = _("Planification de rapport")
        verbose_name_plural = _("Planifications de rapport")
        ordering = ["-created_at"]
        constraints = [
            # Une seule planification active par type (safety anti-doublon)
            models.UniqueConstraint(
                fields=["report_type"],
                condition=models.Q(is_active=True),
                name="unique_active_schedule_per_type",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.report_type}] {self.name}"


# ============================================================================
# 2. AutomatedReportRecipient — abonné SMS/Email
# ============================================================================
class AutomatedReportRecipient(BaseModel):
    """Destinataire habilité à recevoir les rapports périodiques.

    Le consentement (`consent_date`) est OBLIGATOIRE (AC-08) : l'envoi sera
    refusé si null. Historique conservé même après désactivation pour audit.
    """
    full_name = models.CharField(max_length=180)
    job_title = models.CharField(max_length=120, blank=True)
    organization = models.CharField(max_length=180, blank=True)
    phone_number = models.CharField(
        max_length=32, blank=True, db_index=True,
        help_text=_("Format international E.164 (+225XXXXXXXXXX)."),
    )
    email = models.EmailField(blank=True, db_index=True)
    preferred_channel = models.CharField(
        max_length=10,
        choices=PreferredChannel.choices,
        default=PreferredChannel.EMAIL,
    )
    language = models.CharField(
        max_length=8, default="fr",
        help_text=_("Code ISO 639-1 (fr, en, ...)."),
    )
    district = models.ForeignKey(
        "geo.HealthZone", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="report_recipients",
        help_text=_("District sanitaire ou périmètre géographique optionnel."),
    )
    allowed_report_types = models.JSONField(
        default=list, blank=True,
        help_text=_("Liste des report_type autorisés — vide = tous."),
    )
    is_active = models.BooleanField(default=True, db_index=True)

    # ── Consentement (obligatoire — AC-08) ───────────────────────────────
    consent_date = models.DateField(
        null=True, blank=True,
        help_text=_("Date de recueil du consentement écrit du destinataire."),
    )
    consent_evidence = models.CharField(
        max_length=500, blank=True,
        help_text=_("Référence du document ou URL de preuve du consentement."),
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="report_recipients_created",
    )

    class Meta:
        verbose_name = _("Destinataire de rapport")
        verbose_name_plural = _("Destinataires de rapport")
        ordering = ["full_name"]
        indexes = [
            models.Index(fields=["is_active", "preferred_channel"]),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.preferred_channel})"

    def clean(self):
        """Validations métier appliquées AVANT save (via admin/DRF)."""
        super().clean()
        needs_phone = self.preferred_channel in (
            PreferredChannel.SMS, PreferredChannel.BOTH,
        )
        needs_email = self.preferred_channel in (
            PreferredChannel.EMAIL, PreferredChannel.BOTH,
        )
        if needs_phone and not self.phone_number:
            raise ValidationError(
                {"phone_number": _("Requis pour le canal SMS.")}
            )
        if needs_email and not self.email:
            raise ValidationError(
                {"email": _("Requis pour le canal Email.")}
            )
        if self.is_active and not self.consent_date:
            raise ValidationError(
                {"consent_date": _(
                    "Le consentement est obligatoire pour activer un destinataire "
                    "(conformité RGPD nationale INHP)."
                )}
            )

    @property
    def masked_phone(self) -> str:
        """Version masquée pour affichage : +22507****0000."""
        if not self.phone_number or len(self.phone_number) < 8:
            return "***"
        return f"{self.phone_number[:6]}****{self.phone_number[-4:]}"


# ============================================================================
# 3. GeneratedReport — archive du rapport produit
# ============================================================================
class GeneratedReport(BaseModel):
    """Rapport généré (agrégats + fichiers). Idempotent par (type, période).

    Un `report_code` humainement lisible est calculé au save :
      - WEEKLY : RAP-HEBDO-2026-S24
      - MONTHLY : RAP-MENS-2026-06
    """
    report_code = models.CharField(
        max_length=32, unique=True, db_index=True,
        help_text=_("Ex. RAP-HEBDO-2026-S24 — généré au save si vide."),
    )
    report_type = models.CharField(
        max_length=20, choices=ReportType.choices,
    )
    period_start = models.DateTimeField(db_index=True)
    period_end = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=20, choices=ReportStatus.choices, default=ReportStatus.PENDING,
    )
    # summary_data contient TOUTES les KPI agrégées (compteurs, breakdowns).
    # Aucun PII individuel — que des agrégats (AC-01).
    summary_data = models.JSONField(default=dict, blank=True)
    pdf_file = models.FileField(
        upload_to="reports/weekly/%Y/%m/", null=True, blank=True,
    )
    excel_file = models.FileField(
        upload_to="reports/weekly/%Y/%m/", null=True, blank=True,
    )
    generated_at = models.DateTimeField(null=True, blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reports_generated",
        help_text=_("Null si généré par la tâche Celery Beat."),
    )
    error_message = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_("Durée de génération en millisecondes (monitoring)."),
    )

    class Meta:
        verbose_name = _("Rapport généré")
        verbose_name_plural = _("Rapports générés")
        ordering = ["-period_start"]
        # Idempotence forte : 1 seul rapport par (type, période)
        constraints = [
            models.UniqueConstraint(
                fields=["report_type", "period_start", "period_end"],
                name="unique_report_per_type_period",
            ),
        ]
        indexes = [
            models.Index(fields=["report_type", "-period_start"]),
            models.Index(fields=["status", "-generated_at"]),
        ]

    def __str__(self) -> str:
        return self.report_code or f"[{self.report_type}] {self.period_start.date()}"

    def save(self, *args, **kwargs):
        if not self.report_code:
            self.report_code = self._compute_code()
        super().save(*args, **kwargs)

    def _compute_code(self) -> str:
        """Calcule un code humainement lisible depuis type + période."""
        if self.report_type == ReportType.WEEKLY:
            iso_year, iso_week, _dow = self.period_start.astimezone(
                timezone.get_current_timezone()
            ).isocalendar()
            return f"RAP-HEBDO-{iso_year}-S{iso_week:02d}"
        if self.report_type == ReportType.MONTHLY:
            d = self.period_start.astimezone(timezone.get_current_timezone())
            return f"RAP-MENS-{d.year}-{d.month:02d}"
        if self.report_type == ReportType.QUARTERLY:
            d = self.period_start.astimezone(timezone.get_current_timezone())
            q = (d.month - 1) // 3 + 1
            return f"RAP-TRIM-{d.year}-Q{q}"
        return f"RAP-{self.report_type.upper()}-{self.period_start:%Y%m%d}"


# ============================================================================
# 4. ReportDeliveryLog — traçabilité des envois
# ============================================================================
class ReportDeliveryLog(BaseModel):
    """Une ligne par tentative d'envoi à un destinataire.

    Retry safe : `retry_count` borné à 3 (voir tasks.retry_failed_weekly_reports).
    Adresse toujours masquée dans les logs (voir masked_destination).
    """
    report = models.ForeignKey(
        GeneratedReport, on_delete=models.CASCADE, related_name="deliveries",
    )
    recipient = models.ForeignKey(
        AutomatedReportRecipient,
        on_delete=models.PROTECT,  # PROTECT car on veut garder l'historique
        related_name="deliveries",
    )
    channel = models.CharField(max_length=20, choices=DeliveryChannel.choices)
    provider = models.CharField(
        max_length=40, blank=True,
        help_text=_("Ex. orange_ci, twilio, smtp, ses."),
    )
    destination_masked = models.CharField(
        max_length=80,
        help_text=_("Version masquée du numéro ou email (jamais en clair)."),
    )
    status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.QUEUED,
        db_index=True,
    )
    notification_id = models.PositiveBigIntegerField(
        null=True, blank=True,
        help_text=_("FK logique vers apps.notifications.Notification."),
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    next_retry_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Log d'envoi de rapport")
        verbose_name_plural = _("Logs d'envoi de rapport")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["report", "status"]),
            models.Index(fields=["recipient", "-created_at"]),
            models.Index(fields=["status", "next_retry_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.report.report_code} → {self.recipient} ({self.status})"

    @property
    def is_terminal(self) -> bool:
        """Statut final (plus de retry possible)."""
        return self.status in (
            DeliveryStatus.DELIVERED,
            DeliveryStatus.PERMANENTLY_FAILED,
        )

    @property
    def can_retry(self) -> bool:
        return self.status == DeliveryStatus.FAILED and self.retry_count < 3
