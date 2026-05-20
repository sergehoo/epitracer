"""
Modèles abstraits partagés.

Tous les modèles métier héritent d'au moins :
- UUIDModel       : identifiant UUID externe stable (en plus du PK interne)
- TimestampedModel : created_at / updated_at automatiques
- SoftDeleteModel  : suppression logique (jamais de DELETE physique sur des données sanitaires)
"""
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(_("créé le"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("mis à jour le"), auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Ajoute un identifiant public uuid (en plus du pk interne BigAuto).

    On utilise un uuid pour les URLs publiques, les QR codes, etc.,
    afin de ne jamais exposer les ids séquentiels.
    """

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)

    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    """Manager qui filtre automatiquement les objets supprimés."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllObjectsManager(models.Manager):
    """Manager qui inclut les objets supprimés."""

    def get_queryset(self):
        return super().get_queryset()


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, hard: bool = False):
        if hard:
            return super().delete(using=using, keep_parents=keep_parents)
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])
        return (1, {self._meta.label: 1})

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])


class BaseModel(UUIDModel, TimestampedModel, SoftDeleteModel):
    """Combinaison standard. À privilégier pour toutes les entités métier."""

    class Meta:
        abstract = True
        ordering = ["-created_at"]
