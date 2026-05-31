"""Service MFA par email — génération + vérification de codes OTP 6 chiffres.

Sécurité :
    - Codes hashés (SHA-256) en DB, jamais en clair
    - Expiration 10 minutes
    - 5 tentatives max par code
    - Invalidation auto des anciens codes lors d'une nouvelle génération
    - Envoi via le canal INTERNAL (inhp@veillesanitaire.com)
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from apps.accounts.mfa_models import EmailOtpCode

logger = logging.getLogger("epidemitracker.accounts.email_otp")

OTP_TTL_MINUTES = 10
OTP_LENGTH = 6


@dataclass
class OtpResult:
    ok: bool
    error: str = ""
    code_id: Optional[int] = None
    attempts_remaining: int = 0


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _get_client_ip(request) -> Optional[str]:
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def generate_otp_for_user(user, *, request=None) -> tuple[str, EmailOtpCode]:
    """Génère un nouveau code OTP, invalide les anciens, retourne (code_clair, obj).

    Le code clair N'EST RETOURNÉ qu'à l'appelant pour l'inclure dans l'email
    — jamais stocké en DB. Seul son hash SHA-256 l'est.
    """
    # Invalidate tous les codes valides précédents (un code à la fois actif)
    EmailOtpCode.objects.filter(
        user=user, used_at__isnull=True, expires_at__gt=timezone.now(),
    ).update(used_at=timezone.now())

    # Code à 6 chiffres aléatoires (cryptographiquement sûr)
    code = "".join(str(secrets.randbelow(10)) for _ in range(OTP_LENGTH))

    obj = EmailOtpCode.objects.create(
        user=user,
        code_hash=_hash_code(code),
        expires_at=timezone.now() + timedelta(minutes=OTP_TTL_MINUTES),
        ip_address=_get_client_ip(request),
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:300] if request else ""),
    )
    return code, obj


def send_otp_email(user, *, request=None, sync: bool = True) -> OtpResult:
    """Génère un code et l'envoie par email via le profil INTERNAL.

    Args:
        user : utilisateur destinataire
        request : HttpRequest (pour tracer IP/UA dans l'OTP)
        sync : si True (défaut), envoie l'email en SYNCHRONE (skip Celery).
            Latence < 3s pour un SMTP fonctionnel. C'est le mode recommandé
            pour le login car l'utilisateur attend activement le code.
            Si False, passe par la queue Celery (peut prendre du temps si
            le worker est chargé ou si greylisting Gmail).

    Utilisé en deux endroits :
      - Après validation email/password si l'utilisateur a activé MFA
      - Sur demande explicite (renvoi du code après cooldown)
    """
    from apps.notifications.email_models import EmailLog, EmailStatus, EmailType
    from apps.notifications.services.email_router import (
        _execute_email_send, send_email_by_type,
    )

    code, obj = generate_otp_for_user(user, request=request)

    full_name = (
        f"{user.first_name} {user.last_name}".strip()
        or user.get_username() or user.email
    )

    subject = "Votre code de vérification — INHP Veille Sanitaire"
    body_html = f"""
<!doctype html>
<html lang="fr"><body style="margin:0;padding:0;background:#F1F5F9;
  font-family:Arial,sans-serif;color:#0F172A">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background:#F1F5F9;padding:24px 0">
 <tr><td align="center">
  <table role="presentation" width="500" cellpadding="0" cellspacing="0"
         style="max-width:500px;background:#ffffff;border-radius:8px;
                overflow:hidden;border:1px solid #CBD5E1">
    <tr><td style="background:#1E40AF;padding:18px 28px;color:#ffffff;
       font-weight:700;font-size:16px">
      INHP &middot; Veille Sanitaire
    </td></tr>
    <tr><td style="padding:28px 32px">
      <h1 style="margin:0;font-size:20px;font-weight:700;color:#0F172A">
        Code de vérification
      </h1>
      <p style="color:#334155;font-size:14px;line-height:1.6;margin:14px 0 0 0">
        Bonjour <strong>{full_name}</strong>,
      </p>
      <p style="color:#334155;font-size:14px;line-height:1.6">
        Voici votre code de connexion à la console INHP. Il est valable
        <strong>{OTP_TTL_MINUTES} minutes</strong> et ne peut être utilisé
        qu'une seule fois.
      </p>
      <div style="text-align:center;padding:24px 0">
        <div style="display:inline-block;background:#EFF6FF;border:2px solid #1E40AF;
                    border-radius:10px;padding:18px 36px;font-family:Consolas,monospace;
                    font-size:34px;font-weight:800;letter-spacing:8px;color:#1E40AF">
          {code}
        </div>
      </div>
      <p style="color:#334155;font-size:13px;line-height:1.6">
        Saisissez ce code dans l'écran de connexion.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0"
             style="margin-top:18px;background:#FEF3C7;border-left:4px solid #D97706;
                    border-radius:6px;padding:12px 14px">
        <tr><td style="font-size:12px;color:#92400E;line-height:1.5">
          <strong>Sécurité :</strong> si vous n'êtes pas à l'origine de cette
          connexion, ignorez cet email et signalez-le immédiatement à
          l'administrateur.
        </td></tr>
      </table>
    </td></tr>
    <tr><td style="background:#F8FAFC;border-top:1px solid #CBD5E1;
       padding:14px 28px;font-size:11px;color:#64748B;line-height:1.6">
      Email automatique — ne pas répondre. Adresse de contact :
      <a href="mailto:inhp@veillesanitaire.com" style="color:#1E40AF">
        inhp@veillesanitaire.com</a>
    </td></tr>
  </table>
 </td></tr>
</table>
</body></html>
""".strip()

    body_text = (
        f"Bonjour {full_name},\n\n"
        f"Votre code de vérification INHP : {code}\n\n"
        f"Ce code est valable {OTP_TTL_MINUTES} minutes et ne peut être\n"
        f"utilisé qu'une seule fois.\n\n"
        f"Si vous n'êtes pas à l'origine de cette connexion, ignorez ce\n"
        f"message et signalez-le à inhp@veillesanitaire.com.\n\n"
        f"— INHP Veille Sanitaire"
    )

    # send_email_by_type crée l'EmailLog en QUEUED puis enqueue Celery.
    # En mode SYNC on récupère le log et on appelle _execute_email_send
    # juste après pour court-circuiter la queue.
    result = send_email_by_type(
        email_type=EmailType.MFA_NOTIFICATION,
        recipient=user.email,
        subject=subject,
        body_html=body_html,
        body_text=body_text,
        related_user=user,
    )

    if not result.ok:
        logger.error("Envoi OTP email échoué pour user=%s : %s", user.pk, result.error)
        return OtpResult(ok=False, error=result.error)

    if sync and result.log_id:
        # Force l'envoi SMTP immédiat (skip Celery) — UX login instantanée.
        # Le worker peut quand même picker plus tard, _execute_email_send
        # marquera déjà status=SENT donc le worker la skip.
        try:
            email_log = EmailLog.objects.get(pk=result.log_id)
            if email_log.status == EmailStatus.QUEUED:
                ok = _execute_email_send(email_log)
                if not ok:
                    logger.warning(
                        "Envoi OTP sync KO pour user=%s : %s",
                        user.pk, email_log.error_message,
                    )
                    return OtpResult(ok=False, error=email_log.error_message)
        except Exception as exc:  # noqa: BLE001
            logger.exception("OTP sync send crash : %s", exc)
            # On considère que c'est OK quand même car Celery va prendre le relai
            # (la tâche reste en queue et sera consommée plus tard)

    return OtpResult(ok=True, code_id=obj.id, attempts_remaining=obj.max_attempts)


def verify_otp(user, code: str) -> OtpResult:
    """Vérifie un code OTP saisi par l'utilisateur.

    - Cherche le dernier code valide pour cet user
    - Incrémente attempts à chaque tentative
    - Marque used_at en cas de succès
    - Retourne attempts_remaining pour affichage côté UI
    """
    code = (code or "").strip()
    if not code or not code.isdigit() or len(code) != OTP_LENGTH:
        return OtpResult(ok=False, error="Code invalide (6 chiffres attendus).")

    obj = (
        EmailOtpCode.objects
        .filter(user=user, used_at__isnull=True, expires_at__gt=timezone.now())
        .order_by("-created_at")
        .first()
    )
    if not obj:
        return OtpResult(
            ok=False, error="Code expiré ou inexistant. Demander un nouveau code.",
        )

    if obj.attempts >= obj.max_attempts:
        return OtpResult(
            ok=False,
            error="Trop de tentatives. Demander un nouveau code.",
            attempts_remaining=0,
        )

    obj.attempts += 1

    if obj.code_hash != _hash_code(code):
        obj.save(update_fields=["attempts", "updated_at"])
        return OtpResult(
            ok=False,
            error="Code incorrect.",
            attempts_remaining=obj.attempts_remaining,
        )

    # Code OK
    obj.used_at = timezone.now()
    obj.save(update_fields=["attempts", "used_at", "updated_at"])
    return OtpResult(ok=True, code_id=obj.id)
