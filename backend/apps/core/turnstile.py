"""Cloudflare Turnstile — vérification côté serveur.

Le jeton est lu dans l'en-tête `X-Turnstile-Token` (clients web et mobile)
ou, à défaut, dans le champ `turnstile_token` du corps. La vérification est
faite auprès de Cloudflare (siteverify) avec l'IP du client ; l'action
attendue et, si configurés, les noms d'hôte sont contrôlés.

Rejeu : un jeton déjà validé n'est accepté à nouveau que depuis la même IP et
dans la limite `MAX_REUSE_SAME_IP` (retry réseau du formulaire). Toute autre
re-présentation est rejetée sans appel à Cloudflare.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx
from django.conf import settings
from django.core.cache import cache

from .ratelimit import client_ip, fingerprint

logger = logging.getLogger("epidemitracker.security.turnstile")

_REPLAY_TTL = 300  # durée de vie d'un jeton Turnstile côté Cloudflare


@dataclass
class TurnstileResult:
    ok: bool
    reason: str = ""
    error_codes: list[str] = field(default_factory=list)


def _cfg() -> dict:
    return getattr(settings, "TURNSTILE", {}) or {}


def is_required(action: str) -> bool:
    cfg = _cfg()
    return bool(cfg.get("SECRET_KEY")) and action in (cfg.get("PROTECTED_ACTIONS") or [])


def token_from_request(request) -> str:
    token = request.META.get("HTTP_X_TURNSTILE_TOKEN", "")
    if not token:
        try:
            token = request.data.get("turnstile_token", "") or ""
        except AttributeError:
            token = ""
    return str(token).strip()[:2048]


def verify(token: str, *, ip: str, action: str) -> TurnstileResult:
    cfg = _cfg()
    if not token:
        return TurnstileResult(ok=False, reason="missing")

    replay_key = f"turnstile:used:{fingerprint(token)}"
    seen = cache.get(replay_key)
    if seen:
        if seen.get("ip") == ip and seen.get("uses", 0) < cfg.get("MAX_REUSE_SAME_IP", 3):
            seen["uses"] = seen.get("uses", 0) + 1
            cache.set(replay_key, seen, timeout=_REPLAY_TTL)
            return TurnstileResult(ok=True, reason="reused_same_ip")
        return TurnstileResult(ok=False, reason="replay")

    try:
        resp = httpx.post(
            cfg.get("VERIFY_URL"),
            data={"secret": cfg.get("SECRET_KEY"), "response": token, "remoteip": ip},
            timeout=cfg.get("TIMEOUT", 5),
        )
        data = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Turnstile injoignable (%s) — fail_open=%s", exc, cfg.get("FAIL_OPEN"))
        if cfg.get("FAIL_OPEN"):
            return TurnstileResult(ok=True, reason="unavailable_fail_open")
        return TurnstileResult(ok=False, reason="unavailable")

    if not data.get("success"):
        codes = [str(c) for c in data.get("error-codes", [])]
        reason = "replay" if "timeout-or-duplicate" in codes else "invalid"
        return TurnstileResult(ok=False, reason=reason, error_codes=codes)
    if data.get("action") and data["action"] != action:
        return TurnstileResult(ok=False, reason="action_mismatch")
    hostnames = cfg.get("ALLOWED_HOSTNAMES") or []
    if hostnames and data.get("hostname") not in hostnames:
        return TurnstileResult(ok=False, reason="hostname_mismatch")

    cache.set(replay_key, {"ip": ip, "uses": 1}, timeout=_REPLAY_TTL)
    return TurnstileResult(ok=True)


TURNSTILE_MESSAGES = {
    "missing": "Vérification anti-robot requise. Rechargez la page et validez le contrôle.",
    "unavailable": "Vérification anti-robot momentanément indisponible. Réessayez dans un instant.",
}
DEFAULT_MESSAGE = "Vérification anti-robot échouée. Rechargez la page et réessayez."


def check_request(request, action: str) -> TurnstileResult:
    """Vérifie la requête si l'action est protégée ; journalise les échecs."""
    if not is_required(action):
        return TurnstileResult(ok=True, reason="not_required")
    ip = client_ip(request)
    result = verify(token_from_request(request), ip=ip, action=action)
    if not result.ok:
        from apps.notifications.services.security import SecurityEventKind, log_security_event

        log_security_event(
            SecurityEventKind.TURNSTILE_FAILED,
            source=action,
            ip=ip,
            details={"reason": result.reason, "error_codes": result.error_codes},
            dedupe=f"{action}:{ip}:{result.reason}",
        )
    return result


def failure_message(result: TurnstileResult) -> str:
    return TURNSTILE_MESSAGES.get(result.reason, DEFAULT_MESSAGE)
