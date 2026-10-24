"""Limitation de débit applicative (fenêtres fixes atomiques, Redis).

Complète les throttles DRF (par IP, historique non atomique) pour les
parcours coûteux : clés arbitraires (IP, numéro E.164, compte, endpoint),
compteurs `INCR` atomiques — deux requêtes concurrentes ne peuvent pas
dépasser la limite ensemble.

Redis indisponible (django_redis en IGNORE_EXCEPTIONS) : `hit()` renvoie
None et l'appelant choisit sa politique (la garde SMS se replie sur la base).
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

_PREFIX = "rl"


def fingerprint(value: str) -> str:
    """Empreinte courte et non réversible (pas de numéro en clair dans Redis)."""
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest()[:20]


def client_ip(request) -> str:
    """IP client (premier saut de X-Forwarded-For posé par le reverse proxy)."""
    if request is None:
        return ""
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or ""


def incr_window(key: str, window: int, amount: int = 1) -> int | None:
    """Incrémente atomiquement le compteur de la fenêtre courante.

    Retourne la nouvelle valeur, ou None si le cache est indisponible.
    """
    bucket = int(time.time() // window)
    full_key = f"{_PREFIX}:{key}:{bucket}"
    for _ in range(2):
        added = cache.add(full_key, 0, timeout=window + 5)
        if added is None:  # backend en erreur (exceptions ignorées)
            return None
        try:
            value = cache.incr(full_key, amount)
        except ValueError:  # clé expirée entre add et incr : on recommence
            continue
        return None if value is None else int(value)
    return None


def decr_window(key: str, window: int, amount: int = 1) -> None:
    """Annule une réservation (rollback quand une autre limite refuse)."""
    bucket = int(time.time() // window)
    try:
        cache.decr(f"{_PREFIX}:{key}:{bucket}", amount)
    except ValueError:
        pass


@dataclass
class LimitResult:
    allowed: bool
    rule: str = ""
    count: int | None = None
    limit: int = 0
    window: int = 0

    @property
    def retry_after(self) -> int:
        if not self.window:
            return 0
        return max(1, self.window - int(time.time() % self.window))


def hit(
    rule: str, identity: str, *, limit: int | None = None, window: int | None = None
) -> LimitResult:
    """Compte un passage pour `rule` + `identity` et dit s'il est autorisé.

    `limit`/`window` par défaut lus dans settings.PUBLIC_RATE_LIMITS[rule].
    Cache indisponible → autorisé (count=None) : la garde SMS en aval reste
    la dernière ligne de défense (repli base de données).
    """
    if limit is None or window is None:
        limit, window = settings.PUBLIC_RATE_LIMITS[rule]
    count = incr_window(f"{rule}:{fingerprint(identity)}", window)
    if count is None:
        return LimitResult(allowed=True, rule=rule, count=None, limit=limit, window=window)
    return LimitResult(allowed=count <= limit, rule=rule, count=count, limit=limit, window=window)
