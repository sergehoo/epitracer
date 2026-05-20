"""Signaux d'audit liés à l'authentification."""
from __future__ import annotations

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .models import LoginEvent


def _client_meta(request):
    if request is None:
        return None, ""
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get("REMOTE_ADDR")
    ua = request.META.get("HTTP_USER_AGENT", "")[:400]
    return ip, ua


@receiver(user_logged_in)
def _on_login(sender, request, user, **kwargs):
    ip, ua = _client_meta(request)
    LoginEvent.objects.create(
        user=user,
        email_attempted=getattr(user, "email", ""),
        ip_address=ip,
        user_agent=ua,
        success=True,
    )


@receiver(user_logged_out)
def _on_logout(sender, request, user, **kwargs):
    ip, ua = _client_meta(request)
    if user is not None:
        LoginEvent.objects.create(
            user=user,
            email_attempted=getattr(user, "email", ""),
            ip_address=ip,
            user_agent=ua,
            success=True,
            failure_reason="logout",
        )


@receiver(user_login_failed)
def _on_login_failed(sender, credentials, request, **kwargs):
    ip, ua = _client_meta(request)
    LoginEvent.objects.create(
        user=None,
        email_attempted=credentials.get("username", "")[:254],
        ip_address=ip,
        user_agent=ua,
        success=False,
        failure_reason="bad_credentials",
    )
