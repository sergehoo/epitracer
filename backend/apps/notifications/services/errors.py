"""Classification des erreurs d'envoi et libellés compréhensibles.

Les fournisseurs renvoient des réponses techniques (JSON Orange, codes Twilio,
traces réseau). On les range dans une petite taxonomie stable (`error_code`)
qui pilote :
  - la politique de retry (une erreur définitive n'est jamais retentée) ;
  - la suspension du fournisseur (crédit Orange CI épuisé) ;
  - le message affiché aux agents, sans réponse brute du fournisseur.
"""
from __future__ import annotations

import json
import re


class ErrorCode:
    QUOTA_EXHAUSTED = "provider_quota_exhausted"
    PROVIDER_POLICY = "provider_policy"
    PROVIDER_AUTH = "provider_auth"
    PROVIDER_CONFIG = "provider_config"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_SUSPENDED = "provider_suspended"
    NETWORK = "network"
    INVALID_NUMBER = "invalid_number"
    NATIONAL_POLICY = "national_policy"
    NO_DEVICE = "no_device"
    TEMPLATE_VARIABLES = "template_variables"
    EXPIRED_ON_HOLD = "expired_on_hold"
    # Garde anti SMS pumping (services.sms_guard)
    SMS_QUOTA_EXCEEDED = "sms_quota_exceeded"
    BUDGET_EXCEEDED = "sms_budget_exceeded"
    URGENT_CAP = "urgent_cap_reached"
    COUNTRY_BLOCKED = "country_not_allowed"
    RECIPIENT_NOT_ALLOWED = "recipient_not_allowed"
    # Email (SMTP / Amazon SES)
    EMAIL_UNVERIFIED = "email_unverified"
    EMAIL_REJECTED = "email_rejected"
    UNKNOWN = "unknown"


# Erreurs définitives : retenter ne changera rien (et consomme du crédit ou
# spamme le destinataire). Elles ne sont relancées que manuellement.
NON_RETRYABLE = frozenset({
    ErrorCode.QUOTA_EXHAUSTED,
    ErrorCode.PROVIDER_POLICY,
    ErrorCode.PROVIDER_AUTH,
    ErrorCode.PROVIDER_CONFIG,
    ErrorCode.PROVIDER_SUSPENDED,
    ErrorCode.INVALID_NUMBER,
    ErrorCode.NATIONAL_POLICY,
    ErrorCode.NO_DEVICE,
    ErrorCode.TEMPLATE_VARIABLES,
    ErrorCode.EXPIRED_ON_HOLD,
    ErrorCode.SMS_QUOTA_EXCEEDED,
    ErrorCode.BUDGET_EXCEEDED,
    ErrorCode.URGENT_CAP,
    ErrorCode.COUNTRY_BLOCKED,
    ErrorCode.RECIPIENT_NOT_ALLOWED,
    ErrorCode.EMAIL_UNVERIFIED,
    ErrorCode.EMAIL_REJECTED,
})

ERROR_LABELS: dict[str, str] = {
    ErrorCode.QUOTA_EXHAUSTED: (
        "Crédit SMS du fournisseur épuisé : envoi impossible avant réapprovisionnement."
    ),
    ErrorCode.PROVIDER_SUSPENDED: (
        "Fournisseur suspendu (crédit épuisé, budget atteint ou indisponible). Envoi "
        "reporté jusqu'à la reprise par un administrateur."
    ),
    ErrorCode.BUDGET_EXCEEDED: (
        "Budget SMS atteint : envois suspendus jusqu'à décision d'un administrateur."
    ),
    ErrorCode.SMS_QUOTA_EXCEEDED: "Limite d'envoi SMS atteinte pour ce destinataire.",
    ErrorCode.URGENT_CAP: "Plafond journalier des SMS urgents atteint.",
    ErrorCode.COUNTRY_BLOCKED: "Envoi SMS non autorisé vers ce pays.",
    ErrorCode.RECIPIENT_NOT_ALLOWED: "Destinataire non autorisé pour ce compte.",
    ErrorCode.EMAIL_UNVERIFIED: (
        "Email refusé par le fournisseur d'envoi : adresse ou domaine non vérifié "
        "(Amazon SES en mode « bac à sable » ou expéditeur non validé)."
    ),
    ErrorCode.EMAIL_REJECTED: "Adresse email refusée par le serveur destinataire.",
    ErrorCode.PROVIDER_POLICY: "Envoi refusé par le fournisseur (règle de son contrat).",
    ErrorCode.PROVIDER_AUTH: "Connexion au fournisseur refusée : identifiants à vérifier.",
    ErrorCode.PROVIDER_CONFIG: "Fournisseur mal configuré : contacter l'administrateur.",
    ErrorCode.PROVIDER_UNAVAILABLE: (
        "Fournisseur momentanément indisponible. Nouvel essai automatique."
    ),
    ErrorCode.NETWORK: "Problème de connexion au fournisseur. Nouvel essai automatique.",
    ErrorCode.INVALID_NUMBER: "Numéro de destinataire invalide ou non joignable.",
    ErrorCode.NATIONAL_POLICY: (
        "Envoi bloqué : les numéros ivoiriens (+225) passent uniquement par Orange CI."
    ),
    ErrorCode.NO_DEVICE: "Aucun appareil ni abonnement actif pour ce voyageur.",
    ErrorCode.TEMPLATE_VARIABLES: (
        "Message incomplet : des variables du modèle ne sont pas renseignées."
    ),
    ErrorCode.EXPIRED_ON_HOLD: (
        "Rappel devenu obsolète pendant la suspension du fournisseur : non envoyé."
    ),
    ErrorCode.UNKNOWN: "Échec d'envoi. Consulter le détail technique ou réessayer plus tard.",
}

_HTTP_STATUS_RE = re.compile(r"HTTP\s+(\d{3})")


def _orange_policy_id(text: str) -> str:
    """Extrait `policyException.messageId` d'une réponse Orange (si JSON)."""
    start = text.find("{")
    if start < 0:
        return ""
    try:
        data = json.loads(text[start:])
    except ValueError:
        m = re.search(r'"messageId"\s*:\s*"([A-Z]{3}\d{4})"', text)
        return m.group(1) if m else ""
    exc = (data.get("requestError") or {}) if isinstance(data, dict) else {}
    policy = exc.get("policyException") or exc.get("serviceException") or {}
    return str(policy.get("messageId") or "")


def _has(low: str, *needles: str) -> bool:
    return any(n in low for n in needles)


# Règles évaluées dans l'ordre : (code, prédicat(texte minuscule, statut HTTP,
# identifiant de politique Orange)). La première qui correspond l'emporte.
_RULES = (
    (ErrorCode.QUOTA_EXHAUSTED, lambda low, status, pol: (
        pol == "POL0001"
        or _has(low, "consumed all available units", "buy a new bundle")
        # Twilio : solde du compte insuffisant.
        or _has(low, "insufficient funds", "balance is too low", "insufficient balance")
    )),
    (ErrorCode.NATIONAL_POLICY, lambda low, status, pol: "politique nationale" in low),
    (ErrorCode.EMAIL_UNVERIFIED, lambda low, status, pol: (
        _has(low, "not verified", "identities failed the check")
    )),
    (ErrorCode.EMAIL_REJECTED, lambda low, status, pol: (
        _has(low, "recipient address rejected", "mailbox unavailable", "user unknown",
             "recipients refused", "no such user")
    )),
    (ErrorCode.TEMPLATE_VARIABLES, lambda low, status, pol: (
        "variable" in low and _has(low, "non renseign", "manquant")
    )),
    (ErrorCode.PROVIDER_POLICY, lambda low, status, pol: pol.startswith("POL") or status == 403),
    (ErrorCode.PROVIDER_AUTH, lambda low, status, pol: (
        status == 401 or _has(low, "oauth", "re-auth", "authenticate", "authentication", "(535")
    )),
    (ErrorCode.PROVIDER_CONFIG, lambda low, status, pol: (
        _has(low, "non configur", "manquant", "not configured", "senderprofile")
    )),
    (ErrorCode.INVALID_NUMBER, lambda low, status, pol: (
        _has(low, "numéro", "numero", "invalid", "21211", "21614")
        or (status == 400 and "address" in low)
    )),
    (ErrorCode.NO_DEVICE, lambda low, status, pol: _has(low, "aucun appareil", "aucun abonnement")),
    (ErrorCode.PROVIDER_UNAVAILABLE, lambda low, status, pol: status is not None and status >= 500),
    (ErrorCode.NETWORK, lambda low, status, pol: (
        _has(low, "réseau", "timeout", "timed out", "connect")
    )),
)


def classify_error(error: str, *, http_status: int | None = None) -> str:
    """Retourne l'`ErrorCode` correspondant à un message d'erreur brut."""
    if not error and http_status is None:
        return ""
    text = error or ""
    if http_status is None:
        m = _HTTP_STATUS_RE.search(text)
        http_status = int(m.group(1)) if m else None
    low, policy_id = text.lower(), _orange_policy_id(text)
    for code, matches in _RULES:
        if matches(low, http_status, policy_id):
            return code
    return ErrorCode.UNKNOWN


def is_retryable(error_code: str) -> bool:
    return error_code not in NON_RETRYABLE


def friendly_error(error_code: str, error_message: str = "") -> str:
    """Libellé lisible pour un agent — jamais la réponse brute du fournisseur."""
    if not error_code and not error_message:
        return ""
    code = error_code or classify_error(error_message)
    return ERROR_LABELS.get(code, ERROR_LABELS[ErrorCode.UNKNOWN])
