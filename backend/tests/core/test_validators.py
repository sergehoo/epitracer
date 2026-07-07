"""Tests du validator d'uploads — chantier #213-2.

Couvre les 3 axes :
  - taille (rejet > MAX_UPLOAD_SIZE_MB)
  - MIME (rejet d'un type non whitelisté)
  - magic bytes (rejet d'un .exe renommé en .pdf — c'est LE test critique)

Plus un test "happy path" : un PDF minimal valide passe.
"""
from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.validators import validate_uploaded_file


# Magic bytes minimaux pour chaque format whitelisté
JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 50
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
PDF_BYTES = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n" + b"\x00" * 50
WEBP_BYTES = b"RIFF" + b"\x24\x00\x00\x00" + b"WEBP" + b"\x00" * 50
# "MZ" = magic bytes d'un exécutable Windows (PE) — bouchon classique
EXE_BYTES = b"MZ\x90\x00\x03" + b"\x00" * 60


def _file(content: bytes, name: str, content_type: str | None = None) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, content, content_type=content_type)


def test_validate_accepts_valid_pdf():
    detected = validate_uploaded_file(
        _file(PDF_BYTES, "passport.pdf", "application/pdf"),
        allowed_mimes={"application/pdf"},
        max_size_mb=5,
    )
    assert detected == "application/pdf"


def test_validate_accepts_valid_png():
    detected = validate_uploaded_file(
        _file(PNG_BYTES, "scan.png", "image/png"),
        allowed_mimes={"image/png", "image/jpeg"},
        max_size_mb=5,
    )
    assert detected == "image/png"


def test_validate_accepts_valid_jpeg():
    detected = validate_uploaded_file(
        _file(JPEG_BYTES, "scan.jpg", "image/jpeg"),
        allowed_mimes={"image/jpeg"},
        max_size_mb=5,
    )
    assert detected == "image/jpeg"


def test_validate_accepts_valid_webp():
    detected = validate_uploaded_file(
        _file(WEBP_BYTES, "scan.webp", "image/webp"),
        allowed_mimes={"image/webp"},
        max_size_mb=5,
    )
    assert detected == "image/webp"


def test_validate_rejects_exe_renamed_as_pdf():
    """LE test critique : un binaire Windows déguisé en PDF doit être rejeté.

    Le client peut tricher sur le Content-Type, mais pas sur les magic bytes
    en début de fichier — c'est ce que protège le validator.
    """
    with pytest.raises(ValidationError):
        validate_uploaded_file(
            _file(EXE_BYTES, "passport.pdf", "application/pdf"),
            allowed_mimes={"application/pdf", "image/jpeg", "image/png"},
            max_size_mb=5,
        )


def test_validate_rejects_oversized():
    big_pdf = PDF_BYTES + (b"\x00" * (2 * 1024 * 1024))  # ~2 Mo
    with pytest.raises(ValidationError):
        validate_uploaded_file(
            _file(big_pdf, "huge.pdf", "application/pdf"),
            allowed_mimes={"application/pdf"},
            max_size_mb=1,  # plafond 1 Mo → rejet
        )


def test_validate_rejects_disallowed_mime():
    """Un PDF VRAI mais MIME non whitelisté → rejet."""
    with pytest.raises(ValidationError):
        validate_uploaded_file(
            _file(PDF_BYTES, "doc.pdf", "application/pdf"),
            allowed_mimes={"image/png"},  # PDF pas autorisé
            max_size_mb=5,
        )


def test_validate_rejects_empty_file():
    with pytest.raises(ValidationError):
        validate_uploaded_file(
            _file(b"", "empty.pdf", "application/pdf"),
            allowed_mimes={"application/pdf"},
            max_size_mb=5,
        )


def test_validate_rejects_declared_text_mime():
    """Content-Type text/plain doit faire échouer immédiatement, même
    si on essaie de fournir des magic bytes corrects derrière."""
    with pytest.raises(ValidationError):
        validate_uploaded_file(
            _file(PDF_BYTES, "passport.pdf", "text/plain"),
            allowed_mimes={"application/pdf"},
            max_size_mb=5,
        )


def test_validate_accepts_generic_octet_stream_with_valid_bytes():
    """Quand le client n'envoie pas de Content-Type fiable
    (application/octet-stream), on tranche sur les magic bytes."""
    detected = validate_uploaded_file(
        _file(PDF_BYTES, "scan", "application/octet-stream"),
        allowed_mimes={"application/pdf"},
        max_size_mb=5,
    )
    assert detected == "application/pdf"


def test_validate_uses_settings_defaults(settings):
    """Sans paramètres, le validator lit settings.MAX_UPLOAD_SIZE_MB
    et settings.ALLOWED_UPLOAD_MIMES."""
    settings.MAX_UPLOAD_SIZE_MB = 5
    settings.ALLOWED_UPLOAD_MIMES = ["application/pdf"]
    detected = validate_uploaded_file(_file(PDF_BYTES, "doc.pdf", "application/pdf"))
    assert detected == "application/pdf"
