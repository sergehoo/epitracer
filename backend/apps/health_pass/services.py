"""Services : émission, génération QR/PDF, vérification, révocation."""
from __future__ import annotations

from datetime import timedelta
from io import BytesIO

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from apps.diseases.models import Disease
from apps.ebola.models import EbolaInvestigation
from apps.travelers.models import Traveler

from .crypto import is_expired, public_kid, sign_payload, verify_token
from .models import HealthPass, HealthPassStatus, PassBlacklistEntry, PassVerificationLog


def issue_pass(
    *,
    traveler: Traveler,
    disease: Disease,
    risk_level: str = "low",
    risk_score: int = 0,
    investigation_ref: str = "",
    ttl_days: int | None = None,
) -> HealthPass:
    ttl = ttl_days or settings.HEALTHPASS["DEFAULT_TTL_DAYS"]
    expires_at = timezone.now() + timedelta(days=ttl)

    hp = HealthPass.objects.create(
        traveler=traveler,
        disease=disease,
        investigation_ref=investigation_ref,
        risk_level=risk_level,
        risk_score=risk_score,
        expires_at=expires_at,
        signing_kid=public_kid(),
    )

    payload = {
        "iss": settings.HEALTHPASS["ISSUER"],
        "kid": hp.signing_kid,
        "pid": hp.pass_number,
        "tid": traveler.public_id,
        "name": f"{traveler.last_name} {traveler.first_name}",
        "dis": disease.code if disease else None,
        "rsk": risk_level,
        "scr": risk_score,
        "iat": hp.issued_at.isoformat(),
        "exp": expires_at.isoformat(),
    }
    token, signature = sign_payload(payload)
    hp.payload = payload
    hp.signature_b64 = signature

    # QR PNG
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=2)
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    hp.qr_image.save(f"{hp.pass_number}.png", ContentFile(buf.getvalue()), save=False)

    # PDF
    pdf_bytes = _render_pdf(hp, token)
    hp.pdf_file.save(f"{hp.pass_number}.pdf", ContentFile(pdf_bytes), save=False)

    hp.save()
    return hp


def _render_pdf(hp: HealthPass, token: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A5)
    width, height = A5

    # Bandeau
    c.setFillColor(colors.HexColor("#0f172a"))
    c.rect(0, height - 28 * mm, width, 28 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(15 * mm, height - 14 * mm, "PASS SANITAIRE NATIONAL")
    c.setFont("Helvetica", 9)
    c.drawString(15 * mm, height - 20 * mm, settings.APP_METADATA["NATIONAL_ORG_NAME"])
    c.drawString(15 * mm, height - 25 * mm, f"Émetteur : {settings.HEALTHPASS['ISSUER']}")

    # Identité
    y = height - 40 * mm
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(15 * mm, y, f"N° Pass : {hp.pass_number}")
    y -= 7 * mm
    c.setFont("Helvetica", 10)
    c.drawString(15 * mm, y, f"Voyageur : {hp.traveler.last_name.upper()} {hp.traveler.first_name}")
    y -= 5 * mm
    c.drawString(15 * mm, y, f"ID voyageur : {hp.traveler.public_id}")
    y -= 5 * mm
    c.drawString(15 * mm, y, f"Maladie suivie : {hp.disease.name if hp.disease else '-'}")
    y -= 5 * mm
    c.drawString(15 * mm, y, f"Niveau de risque : {hp.risk_level.upper()} ({hp.risk_score}/100)")
    y -= 5 * mm
    c.drawString(15 * mm, y, f"Émis le : {hp.issued_at.strftime('%Y-%m-%d %H:%M')}")
    y -= 5 * mm
    c.drawString(15 * mm, y, f"Expire le : {hp.expires_at.strftime('%Y-%m-%d %H:%M')}")

    # QR
    if hp.qr_image:
        from reportlab.lib.utils import ImageReader

        c.drawImage(
            ImageReader(hp.qr_image.path),
            width - 65 * mm, height - 100 * mm,
            55 * mm, 55 * mm,
            preserveAspectRatio=True, mask="auto",
        )

    # Footer
    c.setFont("Helvetica-Oblique", 7)
    c.setFillColor(colors.grey)
    c.drawString(15 * mm, 12 * mm, "Document signé numériquement (Ed25519). Vérifiable offline avec la clé publique officielle.")
    c.drawString(15 * mm, 8 * mm, f"kid={hp.signing_kid}")

    c.showPage()
    c.save()
    return buf.getvalue()


def issue_pass_for_ebola_investigation(investigation: EbolaInvestigation) -> HealthPass:
    disease = Disease.objects.filter(code="EBOLA").first()
    return issue_pass(
        traveler=investigation.traveler,
        disease=disease,
        risk_level=investigation.risk_level,
        risk_score=investigation.risk_score,
        investigation_ref=investigation.case_number,
    )


def revoke_pass(hp: HealthPass, *, user=None, reason: str = "") -> HealthPass:
    hp.status = HealthPassStatus.REVOKED
    hp.revoked_at = timezone.now()
    hp.revoked_by = user
    hp.revocation_reason = reason[:200]
    hp.save(update_fields=["status", "revoked_at", "revoked_by", "revocation_reason"])
    return hp


def verify_pass(
    token: str,
    *,
    entry_point=None,
    user=None,
    online: bool = True,
) -> dict:
    """Vérifie un QR (offline crypto + online statut)."""
    result: dict = {"is_valid": False, "reason": "", "payload": None, "online_checked": online}
    try:
        payload = verify_token(token)
    except Exception as exc:
        _log_verification(None, "", False, "bad_signature", entry_point, user)
        return {**result, "reason": f"Signature invalide : {exc}"}

    result["payload"] = payload

    if is_expired(payload):
        _log_verification(None, payload.get("pid", ""), False, "expired", entry_point, user)
        return {**result, "reason": "Pass expiré (crypto)."}

    if not online:
        result["is_valid"] = True
        _log_verification(None, payload.get("pid", ""), True, "offline_only", entry_point, user)
        return result

    pass_number = payload.get("pid", "")
    hp = HealthPass.objects.filter(pass_number=pass_number).first()
    if PassBlacklistEntry.objects.filter(pass_number=pass_number).exists():
        _log_verification(hp, pass_number, False, "blacklisted", entry_point, user)
        return {**result, "reason": "Pass en liste noire."}
    if hp is None:
        _log_verification(None, pass_number, False, "unknown", entry_point, user)
        return {**result, "reason": "Pass inconnu côté serveur."}
    if hp.status != HealthPassStatus.ACTIVE:
        _log_verification(hp, pass_number, False, f"status_{hp.status}", entry_point, user)
        return {**result, "reason": f"Pass non actif ({hp.status})."}
    if not hp.is_valid:
        _log_verification(hp, pass_number, False, "expired_or_inactive", entry_point, user)
        return {**result, "reason": "Pass expiré côté serveur."}

    _log_verification(hp, pass_number, True, "ok", entry_point, user)
    return {**result, "is_valid": True}


def _log_verification(hp, pass_number, ok, reason, entry_point, user):
    PassVerificationLog.objects.create(
        pass_obj=hp,
        pass_number=pass_number,
        is_valid=ok,
        reason=reason,
        entry_point=entry_point,
        verified_by=user if user and getattr(user, "is_authenticated", False) else None,
    )
