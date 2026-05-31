"""EmailRouter — orchestration centrale du système email multi-expéditeur.

Règle d'or :
    Le frontend NE CHOISIT JAMAIS l'expéditeur. Pour chaque envoi, on
    fournit un `email_type` (un membre de EmailType) et le router se
    charge tout seul de sélectionner le profil PUBLIC ou INTERNAL.

Architecture :
    send_email_by_type(email_type, recipient, context)
        → résolution du SenderProfile (mapping + DB)
        → rendu du template (HTML + texte)
        → création de l'EmailLog (status=QUEUED)
        → enqueue Celery (send_email_task)
        → retourne EmailLog.id

    Le worker Celery prend ensuite la main et appelle _execute_email_send()
    qui crée la connexion SMTP correcte (PUBLIC=SES, INTERNAL=SMTP local).
"""
from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.utils import timezone

from ..email_models import (
    EmailLog, EmailStatus, EmailTemplate, EmailType,
    PasswordResetToken, SenderProfile,
    get_sender_profile_code_for_type,
)

logger = logging.getLogger("epidemitracker.email_router")


# ===========================================================================
# RÉSULTATS
# ===========================================================================

@dataclass
class EmailResult:
    ok: bool
    log_id: Optional[int] = None
    error: str = ""


@dataclass
class _SafeFormatDict(dict):
    """dict qui retourne `{key}` au lieu de raise KeyError."""
    def __missing__(self, key):  # type: ignore[override]
        return "{" + key + "}"


# ===========================================================================
# RÉSOLUTION PROFIL EXPÉDITEUR
# ===========================================================================

def get_sender_profile(email_type: str) -> SenderProfile:
    """Retourne le SenderProfile DB correspondant au type d'email.

    Lève RuntimeError si le profil n'existe pas en DB (migration manquante).
    """
    code = get_sender_profile_code_for_type(email_type)
    profile = SenderProfile.objects.filter(code=code, is_active=True).first()
    if not profile:
        raise RuntimeError(
            f"SenderProfile actif `{code}` introuvable. "
            f"Exécuter `python manage.py migrate notifications` pour seed."
        )
    return profile


def _get_smtp_settings(profile_code: str) -> dict:
    """Renvoie le dict {host, port, tls, user, password} pour un profil donné."""
    profiles = getattr(settings, "EMAIL_PROFILES", {})
    cfg = profiles.get(profile_code)
    if not cfg:
        raise RuntimeError(
            f"EMAIL_PROFILES['{profile_code}'] non configuré dans settings."
        )
    return cfg


def _build_connection(profile_code: str):
    """Crée une connexion SMTP Django à la volée pour le profil donné.

    Chaque envoi ouvre/ferme sa propre connexion (acceptable pour le volume
    EpiTrace ; pour gros volumes campagne, on pourrait pooler).
    """
    cfg = _get_smtp_settings(profile_code)
    return get_connection(
        backend="django.core.mail.backends.smtp.EmailBackend",
        host=cfg["host"],
        port=cfg["port"],
        username=cfg.get("username") or None,
        password=cfg.get("password") or None,
        use_tls=cfg.get("use_tls", True),
        use_ssl=cfg.get("use_ssl", False),
        timeout=cfg.get("timeout", 20),
        fail_silently=False,
    )


# ===========================================================================
# RENDU TEMPLATE
# ===========================================================================

def _render(text: str, context: dict) -> str:
    """Substitue `{nom_variable}` par sa valeur dans `context`.

    Utilise une regex stricte sur `\\{(\\w+)\\}` pour ne pas interférer
    avec les `{` présents dans le CSS HTML (ex: `style="color:#fff"`).
    Si la variable n'est pas dans le context, on laisse `{nom}` brut
    (jamais d'exception).
    """
    if not text or "{" not in text:
        return text or ""
    ctx = context or {}
    import re
    return re.sub(
        r"\{(\w+)\}",
        lambda m: str(ctx.get(m.group(1), m.group(0))),
        text,
    )


def render_template(template_code: str, context: Optional[dict] = None):
    """Charge un EmailTemplate par code et rend ses champs.

    Retourne (subject, body_html, body_text, template_obj).
    Lève ValueError si le template n'existe pas ou est inactif.
    """
    tpl = EmailTemplate.objects.filter(code=template_code, is_active=True).first()
    if not tpl:
        raise ValueError(f"EmailTemplate `{template_code}` introuvable ou inactif.")
    ctx = context or {}
    return (
        _render(tpl.subject, ctx),
        _render(tpl.body_html, ctx),
        _render(tpl.body_text or _html_to_text(tpl.body_html), ctx),
        tpl,
    )


def _html_to_text(html: str) -> str:
    """Fallback texte naïf à partir du HTML — strip des balises."""
    import re
    if not html:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


# ===========================================================================
# CRÉATION + LOG
# ===========================================================================

def send_email_by_type(
    email_type: str,
    recipient: str,
    *,
    context: Optional[dict] = None,
    template_code: Optional[str] = None,
    subject: Optional[str] = None,
    body_html: Optional[str] = None,
    body_text: Optional[str] = None,
    related_user=None,
    related_traveler=None,
    sent_by=None,
    metadata: Optional[dict] = None,
) -> EmailResult:
    """Point d'entrée unique pour tout envoi email.

    Modes d'usage :
        (a) Avec template_code  → rendu auto depuis DB.
        (b) Sans template_code  → subject/body_html fournis directement.

    Dans les deux cas, l'expéditeur est FORCÉ par le mapping email_type
    → SenderProfile. Le caller ne peut JAMAIS overrider.
    """
    # 1) Valider le type
    if email_type not in dict(EmailType.choices):
        return EmailResult(ok=False, error=f"EmailType inconnu : {email_type}")

    # 2) Validation destinataire (basique)
    if not recipient or "@" not in recipient:
        return EmailResult(ok=False, error="Destinataire email invalide.")

    # 3) Résolution du profil expéditeur
    try:
        profile = get_sender_profile(email_type)
    except (ValueError, RuntimeError) as exc:
        return EmailResult(ok=False, error=str(exc))

    # 4) Rendu (template OU contenu fourni)
    tpl = None
    ctx = dict(context or {})
    if template_code:
        try:
            rendered_subject, rendered_html, rendered_text, tpl = render_template(
                template_code, ctx,
            )
        except ValueError as exc:
            return EmailResult(ok=False, error=str(exc))
    else:
        if not subject or not (body_html or body_text):
            return EmailResult(
                ok=False,
                error="Sans template_code, subject + body_html/body_text sont requis.",
            )
        rendered_subject = _render(subject, ctx)
        rendered_html = _render(body_html or "", ctx)
        rendered_text = _render(body_text or _html_to_text(body_html or ""), ctx)

    # 5) Création de l'EmailLog en QUEUED (sera traité par Celery)
    log = EmailLog.objects.create(
        recipient=recipient.strip().lower(),
        email_type=email_type,
        sender_address=profile.from_address,
        subject=rendered_subject[:300],
        body_html=rendered_html,
        body_text=rendered_text,
        status=EmailStatus.QUEUED,
        template=tpl,
        context=ctx,
        related_user=related_user,
        related_traveler=related_traveler,
        sent_by=sent_by if sent_by and getattr(sent_by, "is_authenticated", False) else None,
    )

    # 6) Enqueue Celery — fallback sync si Celery KO
    try:
        from ..tasks_email import send_email_task
        send_email_task.delay(log.id)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Celery enqueue email failed, fallback sync: %s", exc)
        ok = _execute_email_send(log)
        return EmailResult(ok=ok, log_id=log.id, error=log.error_message)

    return EmailResult(ok=True, log_id=log.id)


# ===========================================================================
# EXÉCUTION (appelée par Celery — séparé pour pouvoir être testée en sync)
# ===========================================================================

def _execute_email_send(log: EmailLog) -> bool:
    """Construit le message + ouvre la connexion SMTP du bon profil + envoie.

    Met à jour l'EmailLog (status/sent_at/error_message/retry_count).
    Retourne True si l'envoi a abouti (status=SENT), False sinon.
    """
    log.retry_count += 1

    try:
        profile_code = get_sender_profile_code_for_type(log.email_type)
        profile = SenderProfile.objects.filter(code=profile_code, is_active=True).first()
        if not profile:
            raise RuntimeError(f"SenderProfile `{profile_code}` indisponible.")

        connection = _build_connection(profile_code)
        from_header = (
            f"{profile.from_name} <{profile.from_address}>"
            if profile.from_name else profile.from_address
        )
        reply_to = [profile.reply_to] if profile.reply_to else None

        msg = EmailMultiAlternatives(
            subject=log.subject,
            body=log.body_text or _html_to_text(log.body_html),
            from_email=from_header,
            to=[log.recipient],
            reply_to=reply_to,
            connection=connection,
        )
        if log.body_html:
            msg.attach_alternative(log.body_html, "text/html")

        sent = msg.send(fail_silently=False)
        if sent:
            log.status = EmailStatus.SENT
            log.sent_at = timezone.now()
            log.error_message = ""
            log.save(update_fields=[
                "status", "sent_at", "error_message", "retry_count", "updated_at",
            ])
            logger.info("Email %s sent to %s via %s", log.email_type,
                        log.masked_recipient, profile_code)
            return True

        log.status = EmailStatus.FAILED
        log.error_message = "SMTP a renvoyé 0 message envoyé"
        log.failed_at = timezone.now()
        log.save(update_fields=[
            "status", "failed_at", "error_message", "retry_count", "updated_at",
        ])
        return False

    except Exception as exc:  # noqa: BLE001
        log.status = EmailStatus.FAILED
        log.error_message = str(exc)[:1000]
        log.failed_at = timezone.now()
        log.save(update_fields=[
            "status", "failed_at", "error_message", "retry_count", "updated_at",
        ])
        logger.error("Email %s FAILED to %s : %s", log.email_type,
                     log.masked_recipient, exc)
        return False


def log_email_status(log_id: int, new_status: str, error: str = "") -> bool:
    """Helper externe pour mettre à jour le statut depuis un webhook
    (delivered/bounced/opened) provider SES par exemple."""
    log = EmailLog.objects.filter(pk=log_id).first()
    if not log:
        return False
    log.status = new_status
    if new_status == EmailStatus.DELIVERED:
        log.delivered_at = timezone.now()
    elif new_status in (EmailStatus.FAILED, EmailStatus.BOUNCED):
        log.failed_at = timezone.now()
        log.error_message = error[:1000]
    log.save()
    return True


# ===========================================================================
# UTILITAIRES SPÉCIFIQUES (utilisés par les services métier)
# ===========================================================================

def generate_password_reset_token(user, *, request=None) -> tuple[str, PasswordResetToken]:
    """Génère un token de reset password à usage unique avec hash sécurisé.

    Retourne (token_clair, PasswordResetToken). Le token clair doit être
    inclus dans l'URL envoyée par email, et N'EST JAMAIS stocké en DB —
    seul son SHA-256 l'est.
    """
    import hashlib
    ttl_hours = getattr(settings, "PASSWORD_RESET_TOKEN_TTL_HOURS", 24)
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    expires_at = timezone.now() + timedelta(hours=ttl_hours)

    obj = PasswordResetToken.objects.create(
        user=user,
        token_hash=token_hash,
        expires_at=expires_at,
        ip_address=_get_client_ip(request) if request else None,
        user_agent=(request.META.get("HTTP_USER_AGENT", "")[:300] if request else ""),
    )
    return raw, obj


def consume_password_reset_token(raw_token: str):
    """Vérifie + consomme un token reset. Retourne le User ou None si invalide."""
    import hashlib
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    obj = PasswordResetToken.objects.filter(token_hash=token_hash).select_related("user").first()
    if not obj or not obj.is_valid:
        return None
    obj.used_at = timezone.now()
    obj.save(update_fields=["used_at", "updated_at"])
    return obj.user


def _get_client_ip(request) -> Optional[str]:
    if not request:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
