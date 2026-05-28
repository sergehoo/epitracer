"""Routeur de fournisseur SMS / WhatsApp.

Règle métier stricte (cf. demande MSHPCMU) :

    Numéro ivoirien (+225...)      → Orange Côte d'Ivoire
    Numéro international (autres)  → Twilio

La règle est appliquée côté backend et ne peut pas être contournée par
l'agent depuis le frontend (toute tentative de forcer un provider pour
un numéro CI est rejetée par le dispatcher).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("epidemitracker.notifications.router")


class PhoneValidationError(Exception):
    """Levée quand un numéro est invalide ou non supporté."""


@dataclass
class RoutingDecision:
    """Résultat du routage."""
    normalized: str          # numéro E.164 (+225XXXXXXXXXX)
    country_code: str        # "CI" pour CI, "INTL" sinon
    provider: str            # "orange_ci" | "twilio"
    is_ivoirian: bool


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------
_NON_DIGITS = re.compile(r"[^\d+]")


def normalize_phone_number(phone: str) -> str:
    """Normalise un numéro vers le format E.164 (+XXXXXXXXX...).

    Règles :
      - Supprime espaces, tirets, parenthèses
      - "00xxx..." → "+xxx..."  (préfixe international classique)
      - "0xxxxxxxxx" (10 chiffres) → "+225xxxxxxxxxx" (présomption CI)
      - "+xxx..."   → conservé tel quel
      - "xxxxxxxxxx" (10 chiffres) → "+225xxxxxxxxxx"

    Lève PhoneValidationError si la longueur résultante est < 8 ou > 16.
    """
    if not phone:
        raise PhoneValidationError("Numéro vide.")

    # Nettoyage : ne garder que chiffres et +
    cleaned = _NON_DIGITS.sub("", phone.strip())

    if not cleaned:
        raise PhoneValidationError(f"Numéro vide après nettoyage : {phone!r}")

    # "00xxx..." → "+xxx..."
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]

    # Si déjà au format +xxx
    if cleaned.startswith("+"):
        out = cleaned
    elif cleaned.startswith("225"):
        # cas "225XXXXXXXXXX" sans le +
        out = "+" + cleaned
    elif len(cleaned) == 10 and cleaned.startswith("0"):
        # Convention CI : 0XXXXXXXXX (10 chiffres) → présomption +225
        out = "+225" + cleaned[1:]
    elif len(cleaned) == 10:
        # 10 chiffres sans 0 initial : présomption CI quand même
        out = "+225" + cleaned
    else:
        # Aucune forme reconnue : on refuse plutôt que de deviner
        raise PhoneValidationError(
            f"Format de numéro non reconnu : {phone!r}. "
            "Utilisez le format international +225XXXXXXXXXX ou 0XXXXXXXXX."
        )

    # Validation finale
    if not 9 <= len(out) <= 16:
        raise PhoneValidationError(
            f"Longueur de numéro invalide ({len(out)}) : {out!r}"
        )

    return out


def is_ivoirian_number(phone: str) -> bool:
    """Vrai si le numéro normalisé est ivoirien (+225...)."""
    try:
        normalized = normalize_phone_number(phone)
        return normalized.startswith("+225")
    except PhoneValidationError:
        return False


def validate_phone_number(phone: str) -> str:
    """Valide un numéro et retourne sa forme E.164.

    Spécifique CI : après le préfixe +225, on attend exactement 10 chiffres
    (réforme 2021 — tous les numéros mobiles CI sont passés à 10 chiffres).

    Lève PhoneValidationError sinon.
    """
    normalized = normalize_phone_number(phone)

    if normalized.startswith("+225"):
        ci_suffix = normalized[4:]
        if not ci_suffix.isdigit():
            raise PhoneValidationError(
                f"Numéro CI invalide (caractères non-numériques) : {normalized!r}"
            )
        if len(ci_suffix) != 10:
            raise PhoneValidationError(
                f"Numéro CI invalide : attendu 10 chiffres après +225, "
                f"reçu {len(ci_suffix)} ({normalized!r}). "
                "Format attendu : +225XXXXXXXXXX (réforme 2021)."
            )
    else:
        # International : longueur minimale 8 chiffres après +
        intl_suffix = normalized[1:]
        if len(intl_suffix) < 8:
            raise PhoneValidationError(
                f"Numéro international trop court : {normalized!r}"
            )

    return normalized


# ---------------------------------------------------------------------------
# Détection de provider
# ---------------------------------------------------------------------------
def detect_provider(phone: str, channel: str = "sms") -> RoutingDecision:
    """Décide quel provider utiliser pour ce numéro et ce canal.

    Args:
        phone: numéro brut (sera normalisé)
        channel: "sms" ou "whatsapp"

    Returns:
        RoutingDecision avec le provider canonique.

    Raises:
        PhoneValidationError: si le numéro est invalide.
        ValueError: si le canal n'est pas supporté.
    """
    channel = (channel or "sms").lower()
    if channel not in {"sms", "whatsapp"}:
        raise ValueError(f"Canal non supporté pour le routage : {channel!r}")

    normalized = validate_phone_number(phone)
    is_ci = normalized.startswith("+225")

    if channel == "whatsapp":
        # WhatsApp : Twilio par défaut (ou Meta selon settings, géré ailleurs)
        # Le routage géographique n'est pas pertinent pour WhatsApp.
        from django.conf import settings
        provider = getattr(settings, "NOTIFICATIONS", {}).get("WHATSAPP_PROVIDER", "twilio")
        provider = "meta_whatsapp" if provider == "meta" else "twilio"
        decision = RoutingDecision(
            normalized=normalized,
            country_code="CI" if is_ci else "INTL",
            provider=provider,
            is_ivoirian=is_ci,
        )
    else:
        # SMS : règle stricte CI vs international
        if is_ci:
            provider = "orange_ci"
        else:
            provider = "twilio"
        decision = RoutingDecision(
            normalized=normalized,
            country_code="CI" if is_ci else "INTL",
            provider=provider,
            is_ivoirian=is_ci,
        )

    masked = _mask(normalized)
    logger.info(
        "Routing decision: %s [%s/%s] → provider=%s",
        masked, channel, decision.country_code, decision.provider,
    )
    return decision


# ---------------------------------------------------------------------------
# Helper masquage (utilisé pour les logs — jamais le numéro brut)
# ---------------------------------------------------------------------------
def _mask(normalized: str) -> str:
    if not normalized:
        return ""
    if len(normalized) <= 8:
        return normalized
    return normalized[:6] + "****" + normalized[-4:]


# ---------------------------------------------------------------------------
# Façade objet (utile pour DI / tests)
# ---------------------------------------------------------------------------
class NotificationProviderRouter:
    """Façade orientée objet — utilisée par le dispatcher et les tests."""

    @staticmethod
    def normalize(phone: str) -> str:
        return normalize_phone_number(phone)

    @staticmethod
    def validate(phone: str) -> str:
        return validate_phone_number(phone)

    @staticmethod
    def is_ivoirian(phone: str) -> bool:
        return is_ivoirian_number(phone)

    @staticmethod
    def detect(phone: str, channel: str = "sms") -> RoutingDecision:
        return detect_provider(phone, channel)
