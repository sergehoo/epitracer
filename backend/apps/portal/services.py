"""Portail public : publication des contenus (fiches maladies, annonces).

La qualification des voyageurs vit dans apps.medical.screening.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.diseases.models import Disease

from .models import PUBLISHER_ROLES, NoticeStatus, PublicNotice

# --------------------------------------------------------------------------- publication


def can_publish(user) -> bool:
    if not user or not user.is_authenticated or not user.is_active:
        return False
    return bool(user.is_superuser or user.has_role(*PUBLISHER_ROLES))


def _require_publisher(user) -> None:
    if not can_publish(user):
        raise PermissionDenied("Publication réservée aux administrateurs habilités.")


def publish_disease(disease: Disease, user) -> Disease:
    _require_publisher(user)
    missing = [f for f in ("slug", "description") if not getattr(disease, f)]
    if missing:
        raise ValidationError({f: "Champ requis avant publication." for f in missing})
    disease.is_published = True
    disease.published_at = timezone.now()
    disease.published_by = user
    disease._change_reason = "Publication sur le portail"
    disease.save(update_fields=["is_published", "published_at", "published_by", "updated_at"])
    return disease


def unpublish_disease(disease: Disease, user) -> Disease:
    _require_publisher(user)
    disease.is_published = False
    disease._change_reason = "Retrait du portail"
    disease.save(update_fields=["is_published", "updated_at"])
    return disease


def publish_notice(notice: PublicNotice, user) -> PublicNotice:
    _require_publisher(user)
    if not notice.title.strip() or not (notice.summary.strip() or notice.body.strip()):
        raise ValidationError({"body": "Titre et contenu requis avant publication."})
    notice.status = NoticeStatus.PUBLISHED
    notice.published_at = timezone.now()
    notice.published_by = user
    notice.save(update_fields=["status", "published_at", "published_by", "updated_at"])
    return notice


def archive_notice(notice: PublicNotice, user) -> PublicNotice:
    _require_publisher(user)
    notice.status = NoticeStatus.ARCHIVED
    notice.save(update_fields=["status", "updated_at"])
    return notice


# ---------------------------------------------------------------------- traductions


def localized(obj, field: str, lang: str | None, translations_attr: str):
    """Valeur traduite si disponible pour `lang`, sinon la valeur française."""
    if lang and not lang.startswith("fr"):
        tr = (getattr(obj, translations_attr, None) or {}).get(lang[:2], {})
        if isinstance(tr, dict) and tr.get(field):
            return tr[field]
    return getattr(obj, field)


def split_lines(text: str) -> list[str]:
    return [line.strip(" •-\t") for line in (text or "").splitlines() if line.strip(" •-\t")]
