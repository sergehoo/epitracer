"""Services métier — fondation Phase 9A.

Pour l'instant on n'expose que ce qui est strictement nécessaire à la
géolocalisation obligatoire (Option 3) et aux signaux automatiques entre
modèles `medical`. Les services d'orchestration plus larges
(création de cas, transitions de classification…) arrivent en 9B.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.utils import timezone

from apps.companion.models import ConsentScope, TravelerLocationPing
from apps.companion.services import get_active_consent
from apps.surveillance.services import trigger_alert

from .models import (
    DiseaseFollowupProtocol,
    FollowUpAction,
    FollowUpActionStatus,
    FollowUpActionType,
)

import logging

logger = logging.getLogger("epidemitracker.medical")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_protocol(disease) -> Optional[DiseaseFollowupProtocol]:
    """Renvoie le protocole actif pour cette maladie, ou None.

    On filtre sur `is_active=True` pour ne pas se baser sur un protocole
    archivé. Pas de cache : la table contient < 20 lignes et la lecture
    est rare (1 fois par évaluation).
    """
    if not disease:
        return None
    return (
        DiseaseFollowupProtocol.objects
        .filter(disease=disease, is_active=True)
        .first()
    )


def _has_recent_alert(case, within_hours: int) -> bool:
    """Anti-spam — True si une alerte géoloc a déjà été levée récemment."""
    raised_at = getattr(case, "geolocation_alert_raised_at", None)
    if raised_at is None:
        return False
    return (timezone.now() - raised_at) < timedelta(hours=within_hours)


# ---------------------------------------------------------------------------
# Géolocalisation obligatoire — Option 3 (RGPD-safe)
# ---------------------------------------------------------------------------


def check_geolocation_compliance(case) -> bool:
    """Évalue si un voyageur en suivi actif partage bien sa position.

    Renvoie :
      - True  : conformité OK (consentement présent ET ping récent), OU
                le protocole n'exige pas la géoloc.
      - False : alerte levée (manque de ping > N heures malgré protocole
                exigeant). Crée une `HealthAlert` ET un `FollowUpAction`
                la première fois, puis applique un anti-spam de 24 h via
                `case.geolocation_alert_raised_at`.

    IMPORTANT — on ne FORCE pas la collecte. La géoloc reste conditionnée
    au consentement explicite du voyageur (`PrivacyConsent` scope
    GEOLOCATION). Si le voyageur retire son consentement, on n'a plus de
    ping → on alerte l'INHP pour intervention physique. C'est conforme
    RGPD car :
      1. le consentement reste révocable à tout moment ;
      2. la révocation génère une alerte légitime, pas une sanction
         automatisée — un agent humain décide de la suite.
    """
    if case is None:
        return True

    protocol = _get_protocol(getattr(case, "disease", None))
    if protocol is None or not protocol.require_geolocation:
        return True

    # Pas d'évaluation pour les quarantaines non-actives.
    if getattr(case, "status", None) != "active":
        return True

    threshold_hours = protocol.geolocation_alert_after_hours or 24
    now = timezone.now()
    threshold = now - timedelta(hours=threshold_hours)

    # 1) Consentement actif ?
    consent = get_active_consent(case.traveler, ConsentScope.GEOLOCATION)
    has_consent = consent is not None

    # 2) Dernier ping consenti dans la fenêtre ?
    last_ping = None
    if has_consent:
        last_ping = (
            TravelerLocationPing.objects
            .filter(traveler=case.traveler, captured_at__gte=threshold)
            .order_by("-captured_at")
            .first()
        )

    if has_consent and last_ping is not None:
        # Compliance OK — rien à faire.
        return True

    # 3) Non-conforme — éviter le spam d'alerte (1 toutes les 24 h max).
    if _has_recent_alert(case, within_hours=24):
        return False

    # 4) Lever l'alerte + logger l'action de suivi.
    reason = "consent_revoked" if not has_consent else "no_recent_ping"
    alert = trigger_alert(
        code="followup_geolocation_missing",
        title="Géoloc absente — voyageur en suivi",
        description=(
            f"Aucune position partagée depuis > {threshold_hours} h pour "
            f"le voyageur {case.traveler.public_id} en suivi {case.disease.code}. "
            f"Motif : {reason}."
        ),
        severity="medium",
        disease=case.disease,
        target=case,
        metadata={
            "reason": reason,
            "threshold_hours": threshold_hours,
            "traveler_public_id": case.traveler.public_id,
        },
    )

    # Anti-spam — marque la date pour éviter de re-alerter dans 24 h.
    case.geolocation_alert_raised_at = now
    try:
        case.save(update_fields=["geolocation_alert_raised_at", "updated_at"])
    except Exception:  # pragma: no cover - resilience
        logger.exception("Impossible de mettre à jour geolocation_alert_raised_at")

    FollowUpAction.objects.create(
        followup_case=case,
        action_type=FollowUpActionType.ALERT_CREATED,
        title="Alerte géoloc",
        description=(
            f"Aucun ping géoloc reçu depuis > {threshold_hours} h "
            f"(motif: {reason}). Alerte sanitaire {alert.code} créée."
        ),
        status=FollowUpActionStatus.COMPLETED,
        metadata={
            "alert_code": alert.code,
            "alert_uuid": str(alert.uuid),
            "reason": reason,
        },
    )
    return False
