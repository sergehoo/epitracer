"""Validators réutilisables pour EpiTrace.

Conçu pour les uploads voyageurs publics (passeport, signature, justificatifs).
Couvre les 3 garde-fous obligatoires avant écriture sur disque / S3 :

  1. **Taille**             : pour éviter les denial-of-service.
  2. **MIME déclaré**       : Content-Type côté client — peu fiable mais
                              premier filtre pour bloquer les fichiers texte
                              et autres formats clairement non attendus.
  3. **Magic bytes**        : en-tête réel du fichier — non triché. C'est
                              le contrôle qui matérialise la sécurité :
                              un .exe renommé "passport.pdf" sera détecté.

Utilisation côté serializer DRF :

    from apps.core.validators import validate_uploaded_file

    class MySerializer(serializers.Serializer):
        document = serializers.FileField()

        def validate_document(self, value):
            validate_uploaded_file(
                value,
                allowed_mimes={"image/jpeg", "image/png", "application/pdf"},
                max_size_mb=5,
            )
            return value

Si `python-magic` (libmagic) est dispo, on l'utilise pour identifier le
MIME effectif ; sinon on retombe sur un sniff pur-Python des premiers
bytes (suffisant pour les 4 formats whitelistés).
"""
from __future__ import annotations

import logging
from typing import Iterable

from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

# Magic bytes officiels — RFC + spec format.
# Tuple (signature, mime, label) — signatures vérifiées au début du buffer.
MAGIC_SIGNATURES: tuple[tuple[bytes, str, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg", "JPEG"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "PNG"),
    # WebP : "RIFF" + 4 bytes longueur + "WEBP"
    # On vérifie séparément ci-dessous car il y a un offset.
    (b"%PDF-", "application/pdf", "PDF"),
)

# Quantité d'octets à lire pour le sniff (assez pour tous nos formats).
_SNIFF_SIZE = 16


def _sniff_mime_pure_python(head: bytes) -> str | None:
    """Identifie le MIME en lisant les premiers bytes sans dépendre de libmagic.

    Couvre JPEG / PNG / PDF / WebP. Retourne None si rien ne matche.
    """
    for sig, mime, _label in MAGIC_SIGNATURES:
        if head.startswith(sig):
            return mime
    # WebP a un offset : RIFF<4 bytes><WEBP>
    if len(head) >= 12 and head[0:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def _sniff_mime(head: bytes) -> str | None:
    """Utilise python-magic si dispo, sinon fallback pur-Python."""
    try:
        import magic  # type: ignore
    except Exception:  # pragma: no cover - import-time fallback
        return _sniff_mime_pure_python(head)

    try:
        mime = magic.from_buffer(head, mime=True)
        if mime:
            return mime
    except Exception as exc:
        logger.warning("python-magic detection failed, falling back: %s", exc)

    return _sniff_mime_pure_python(head)


def validate_uploaded_file(
    file,
    allowed_mimes: Iterable[str] | None = None,
    max_size_mb: int | None = None,
) -> str:
    """Valide un fichier uploadé (Django UploadedFile-like).

    Lève :code:`ValidationError` si la taille, le Content-Type déclaré ou
    les magic bytes ne correspondent pas à la whitelist.

    Retourne le MIME effectif détecté (utile pour l'audit / le nommage).
    """
    if file is None:
        raise ValidationError("Aucun fichier fourni.")

    # Defaults from settings (centralisation cf. base.py)
    if allowed_mimes is None:
        allowed_mimes = getattr(
            settings, "ALLOWED_UPLOAD_MIMES",
            ["image/jpeg", "image/png", "image/webp", "application/pdf"],
        )
    allowed_mimes = set(allowed_mimes)

    if max_size_mb is None:
        max_size_mb = getattr(settings, "MAX_UPLOAD_SIZE_MB", 5)

    max_bytes = int(max_size_mb) * 1024 * 1024

    # ── 1. Taille ────────────────────────────────────────────────────────
    size = getattr(file, "size", None)
    if size is None:
        # Certains backends (Storage custom) ne peuplent pas size ;
        # on lit en mémoire dans la limite +1 byte pour vérifier.
        # Cas limite uniquement.
        data = file.read(max_bytes + 1)
        size = len(data)
        try:
            file.seek(0)
        except Exception:
            pass
    if size > max_bytes:
        raise ValidationError(
            f"Fichier trop volumineux ({size // 1024} Ko). "
            f"Maximum autorisé : {max_size_mb} Mo."
        )
    if size == 0:
        raise ValidationError("Fichier vide.")

    # ── 2. Content-Type déclaré (premier filtre, peu fiable) ─────────────
    declared_ct = (getattr(file, "content_type", "") or "").lower().split(";")[0].strip()
    if declared_ct and declared_ct not in allowed_mimes:
        # On ne bloque pas tout de suite : si le Content-Type est absent /
        # générique (application/octet-stream), on laisse les magic bytes
        # trancher. Sinon on rejette tout de suite — c'est un signal fort.
        if declared_ct not in ("", "application/octet-stream", "binary/octet-stream"):
            raise ValidationError(
                "Format de fichier non supporté."
            )

    # ── 3. Magic bytes (la garde sérieuse) ──────────────────────────────
    pos = 0
    try:
        pos = file.tell()
    except Exception:
        pass
    try:
        head = file.read(_SNIFF_SIZE)
    finally:
        try:
            file.seek(pos)
        except Exception:
            pass

    if not head:
        raise ValidationError("Impossible de lire l'en-tête du fichier.")

    real_mime = _sniff_mime(head)
    if real_mime is None or real_mime not in allowed_mimes:
        # /!\ on ne logge JAMAIS le contenu ni le nom du fichier (peut être PII).
        logger.info(
            "upload rejected: declared_ct=%s detected_mime=%s size=%s",
            declared_ct or "-", real_mime or "-", size,
        )
        raise ValidationError(
            "Format de fichier non supporté."
        )

    return real_mime
