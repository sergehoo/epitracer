"""Classe abstraite pour les providers WhatsApp.

L'envoi WhatsApp obéit à des contraintes spécifiques :
    - **Hors fenêtre de 24h** depuis le dernier message du destinataire,
      seuls les TEMPLATES APPROUVÉS sont autorisés (Meta + Twilio).
    - À l'intérieur de la fenêtre de 24h, les messages de type "session"
      (texte libre, médias, etc.) sont autorisés.
    - Les delivery reports arrivent via webhooks (Twilio: form ; Meta: JSON).

Cette abstraction expose 4 méthodes :
    send_text(to, body)
    send_template(to, template_code, variables, language="fr")
    validate_webhook(request) -> bool
    parse_status_webhook(payload) -> WhatsAppStatusEvent
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WhatsAppSendResult:
    """Retour standardisé des méthodes d'envoi WhatsApp."""
    ok: bool
    provider_message_id: str = ""
    error: str = ""
    raw_response: Optional[dict] = None


@dataclass
class WhatsAppStatusEvent:
    """Événement de statut parsé depuis un webhook provider."""
    provider_message_id: str
    status: str          # canonical: sent / delivered / failed / read
    timestamp: Optional[str] = None
    error: str = ""
    raw_payload: Optional[dict] = field(default=None, repr=False)


class WhatsAppProviderBase(ABC):
    """Interface commune Twilio / Meta / autre.

    Les implémentations doivent renvoyer un format normalisé pour que
    le dispatcher et les webhooks n'aient pas à connaître le détail
    de chaque API fournisseur.
    """

    name: str = "abstract"

    # ── Envoi ────────────────────────────────────────────────────────
    @abstractmethod
    def send_text(self, to: str, body: str) -> WhatsAppSendResult:
        """Envoi d'un message texte libre.

        Note : selon le provider, ce mode peut être REFUSÉ hors fenêtre
        de 24h depuis le dernier message du destinataire (cf. politique
        WhatsApp Business). Dans ce cas l'erreur est retournée et le
        dispatcher pourra basculer sur send_template.
        """

    @abstractmethod
    def send_template(
        self, to: str, template_code: str,
        variables: Optional[list] = None,
        language: str = "fr",
    ) -> WhatsAppSendResult:
        """Envoi d'un template pré-approuvé.

        Args:
            to: numéro E.164 (+225XXXXXXXXXX)
            template_code: nom du template tel qu'enregistré chez le provider
            variables: liste ordonnée des valeurs des placeholders {{1}}, {{2}}, ...
            language: code ISO de la langue (fr, en, ...)
        """

    # ── Webhooks ────────────────────────────────────────────────────
    @abstractmethod
    def validate_webhook(self, request) -> bool:
        """Vérifie l'authenticité d'un webhook entrant (signature/token)."""

    @abstractmethod
    def parse_status_webhook(self, payload) -> Optional[WhatsAppStatusEvent]:
        """Convertit un payload webhook en WhatsAppStatusEvent normalisé.

        Retourne None si le payload ne contient pas de delivery report
        exploitable (par ex. webhook de message entrant, pas de statut).
        """


def get_active_provider() -> WhatsAppProviderBase:
    """Renvoie l'instance du provider WhatsApp configuré.

    Lit `settings.NOTIFICATIONS["WHATSAPP_PROVIDER"]` :
        "twilio" → TwilioWhatsAppProvider
        "meta"   → MetaWhatsAppProvider
        autre    → fallback Twilio
    """
    from django.conf import settings
    cfg = getattr(settings, "NOTIFICATIONS", {})
    name = (cfg.get("WHATSAPP_PROVIDER") or "twilio").lower()

    if name == "meta":
        from .whatsapp_meta import MetaWhatsAppProvider
        return MetaWhatsAppProvider()
    # Défaut + alias "twilio_whatsapp"
    from .whatsapp_twilio import TwilioWhatsAppProvider
    return TwilioWhatsAppProvider()
