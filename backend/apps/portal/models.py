"""Contenus du portail public : alertes sanitaires et recommandations aux voyageurs.

Les fiches maladies ne sont pas dupliquées ici : leur contenu public est porté
par apps.diseases.Disease. Ce module ne gère que les annonces datées.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords

from apps.core.models import BaseModel
from apps.diseases.models import PublicAlertLevel

PUBLISHER_ROLES = ("NATIONAL_ADMIN", "MINISTRY", "INHP")


class NoticeKind(models.TextChoices):
    ALERT = "alert", _("Alerte sanitaire")
    RECOMMENDATION = "recommendation", _("Recommandation aux voyageurs")


class NoticeStatus(models.TextChoices):
    DRAFT = "draft", _("Brouillon")
    PUBLISHED = "published", _("Publiée")
    ARCHIVED = "archived", _("Archivée")


class PublicNoticeQuerySet(models.QuerySet):
    def visible(self, at=None):
        """Annonces publiées et dans leur période de validité."""
        at = at or timezone.now()
        return self.filter(status=NoticeStatus.PUBLISHED, valid_from__lte=at).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gte=at)
        )


class PublicNoticeManager(models.Manager.from_queryset(PublicNoticeQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class PublicNotice(BaseModel):
    """Alerte ou recommandation publiée sur le portail par un administrateur habilité."""

    kind = models.CharField(_("type"), max_length=20, choices=NoticeKind.choices, db_index=True)
    title = models.CharField(_("titre"), max_length=200)
    summary = models.CharField(_("résumé"), max_length=300, blank=True)
    body = models.TextField(_("contenu"), blank=True)
    alert_level = models.CharField(
        _("niveau d'alerte"),
        max_length=20,
        choices=PublicAlertLevel.choices,
        default=PublicAlertLevel.NORMAL,
    )
    disease = models.ForeignKey(
        "diseases.Disease",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="public_notices",
    )
    countries = models.ManyToManyField("geo.Country", blank=True, related_name="public_notices")
    source_alert = models.ForeignKey(
        "surveillance.HealthAlert",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="public_notices",
        help_text=_("Alerte interne validée à l'origine de l'annonce (non affichée)."),
    )
    translations = models.JSONField(
        _("traductions"),
        default=dict,
        blank=True,
        help_text=_('Ex : {"en": {"title": "…", "summary": "…", "body": "…"}}'),
    )
    status = models.CharField(
        _("statut"),
        max_length=20,
        choices=NoticeStatus.choices,
        default=NoticeStatus.DRAFT,
        db_index=True,
    )
    valid_from = models.DateTimeField(_("visible à partir du"), default=timezone.now)
    valid_until = models.DateTimeField(_("visible jusqu'au"), null=True, blank=True)
    published_at = models.DateTimeField(_("publiée le"), null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    objects = PublicNoticeManager()
    history = HistoricalRecords()

    class Meta(BaseModel.Meta):
        verbose_name = _("Annonce publique")
        verbose_name_plural = _("Annonces publiques")
        ordering = ["-valid_from"]
        indexes = [models.Index(fields=["status", "kind", "valid_from"])]

    def __str__(self) -> str:
        return f"[{self.get_kind_display()}] {self.title}"
