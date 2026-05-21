"""Logique de tracking de visites + détection bots + enrichissement pays."""
from __future__ import annotations

import re

# Liste pragmatique de signatures de bots — étendable.
_BOT_RE = re.compile(
    r"(bot|crawler|spider|crawling|slurp|googlebot|bingbot|duckduckbot|"
    r"yandex|baiduspider|facebookexternalhit|whatsapp|telegrambot|"
    r"semrushbot|ahrefsbot|mj12bot|petalbot|seznambot|applebot|"
    r"headlesschrome|phantomjs|selenium|puppeteer|playwright|curl|wget|python-urllib|httpie)",
    re.I,
)


def looks_like_bot(user_agent: str) -> bool:
    if not user_agent:
        return True
    return bool(_BOT_RE.search(user_agent))


def extract_ip(request) -> str | None:
    fwd = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# Mapping ISO-2 → nom français pour les pays les plus fréquents
COUNTRY_NAMES = {
    "CI": "Côte d'Ivoire", "FR": "France", "BE": "Belgique", "CH": "Suisse",
    "GH": "Ghana", "NG": "Nigeria", "ML": "Mali", "BF": "Burkina Faso",
    "SN": "Sénégal", "TG": "Togo", "BJ": "Bénin", "CM": "Cameroun",
    "GA": "Gabon", "CD": "RD Congo", "CG": "Congo", "GN": "Guinée",
    "SL": "Sierra Leone", "LR": "Libéria", "MA": "Maroc", "TN": "Tunisie",
    "DZ": "Algérie", "EG": "Égypte", "ZA": "Afrique du Sud", "KE": "Kenya",
    "ET": "Éthiopie", "DE": "Allemagne", "IT": "Italie", "ES": "Espagne",
    "PT": "Portugal", "GB": "Royaume-Uni", "US": "États-Unis", "CA": "Canada",
    "BR": "Brésil", "CN": "Chine", "IN": "Inde", "JP": "Japon",
    "AE": "Émirats arabes unis", "SA": "Arabie saoudite", "LB": "Liban",
    "TR": "Turquie",
}


def detect_country(request, fallback_code: str = "") -> tuple[str, str]:
    """Détecte (code ISO-2, nom) à partir des headers connus.

    Privilégie les headers de proxy/CDN (Cloudflare, Traefik) qui sont
    fiables et performants. Pas de lookup réseau ici (latence + rate-limit).
    """
    headers = request.META
    code = (
        headers.get("HTTP_CF_IPCOUNTRY")           # Cloudflare
        or headers.get("HTTP_X_COUNTRY_CODE")      # Traefik / load balancer custom
        or headers.get("HTTP_X_GEO_COUNTRY")
        or fallback_code
        or ""
    )
    code = code.strip().upper()[:2]
    if code in {"XX", "T1"}:                       # CF anonymisé / Tor
        code = ""
    return code, COUNTRY_NAMES.get(code, "")
