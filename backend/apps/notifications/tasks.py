"""Tâches Celery d'envoi de notifications."""
from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from .models import Channel, Notification, NotificationStatus, NotificationTemplate
from .providers import send_email, send_push, send_sms, send_whatsapp


def _render(template: NotificationTemplate | None, context: dict) -> tuple[str, str]:
    if template is None:
        return "", ""
    try:
        subject = (template.subject or "").format(**context)
        body = (template.body or "").format(**context)
    except KeyError:
        subject = template.subject or ""
        body = template.body or ""
    return subject, body


@shared_task(name="notifications.send", bind=True, max_retries=3, default_retry_delay=30)
def send_notification(
    self,
    *,
    channel: str,
    recipient: str,
    template_code: str | None = None,
    subject: str = "",
    body: str = "",
    context: dict | None = None,
):
    template = NotificationTemplate.objects.filter(code=template_code).first() if template_code else None
    rendered_subject, rendered_body = _render(template, context or {})
    subject = subject or rendered_subject
    body = body or rendered_body or ""

    notif = Notification.objects.create(
        channel=channel, template=template, recipient=recipient,
        subject=subject, body=body, context=context or {},
        status=NotificationStatus.PENDING,
    )
    try:
        if channel == Channel.SMS:
            result = send_sms(recipient, body)
        elif channel == Channel.EMAIL:
            result = send_email(recipient, subject, body)
        elif channel == Channel.WHATSAPP:
            result = send_whatsapp(recipient, body)
        elif channel == Channel.PUSH:
            result = send_push(recipient, subject, body)
        else:
            notif.status = NotificationStatus.SENT
            notif.sent_at = timezone.now()
            notif.save(update_fields=["status", "sent_at"])
            return {"ok": True}
    except Exception as exc:
        notif.status = NotificationStatus.FAILED
        notif.error = str(exc)
        notif.attempts += 1
        notif.save(update_fields=["status", "error", "attempts"])
        raise self.retry(exc=exc)

    notif.provider = result.provider
    notif.provider_id = result.provider_id
    if result.ok:
        notif.status = NotificationStatus.SENT
        notif.sent_at = timezone.now()
    else:
        notif.status = NotificationStatus.FAILED
        notif.error = result.error
    notif.attempts += 1
    notif.save(update_fields=["status", "provider", "provider_id", "error", "sent_at", "attempts"])
    return {"ok": result.ok}
