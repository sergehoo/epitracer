"""
Services métier du module Companion.

Centralisent toute la logique qui n'a pas vocation à être exposée
directement par une view DRF :

- vérification de l'état de consentement actuel pour un voyageur+scope ;
- création de pings de localisation avec garde de consentement ;
- déclenchement d'alertes sanitaires à partir d'un check-in ;
- journalisation des accès aux données sensibles.
"""
from __future__ import annotations

from typing import Iterable

from django.contrib.gis.geos import Point
from django.utils import timezone

from .models import (
    ConsentScope,
    DataAccessLog,
    LocationEventType,
    LocationSource,
    PrivacyConsent,
    TravelerLocationPing,
)


# ----------------------------------------------------------------------------
# Consentements
# ----------------------------------------------------------------------------


def get_active_consent(traveler, scope: str) -> PrivacyConsent | None:
    """Retourne le consentement ACTIF (granted=True ET non révoqué) le plus
    récent pour ce voyageur+scope, ou None.

    Comme le modèle est append-only, on prend la dernière ligne ordonnée
    par `granted_at desc` et on vérifie `revoked_at IS NULL` et
    `granted IS True`.
    """
    return (
        PrivacyConsent.objects.filter(traveler=traveler, scope=scope, granted=True, revoked_at__isnull=True)
        .order_by("-granted_at")
        .first()
    )


def has_consent(traveler, scope: str) -> bool:
    """True si un consentement actif existe pour ce scope."""
    return get_active_consent(traveler, scope) is not None


def record_consent(
    *, traveler, scope: str, granted: bool, version: str = "v1",
    text_excerpt: str = "", ip: str | None = None, user_agent: str = "",
    revocation_reason: str = "",
) -> PrivacyConsent:
    """Enregistre un consentement (accordé OU retiré).

    JAMAIS d'UPDATE : on crée toujours une nouvelle ligne pour garder la
    chronologie. Si `granted=False`, le champ `revoked_at` est rempli
    automatiquement à `now()`.
    """
    return PrivacyConsent.objects.create(
        traveler=traveler,
        scope=scope,
        granted=granted,
        consent_version=version,
        consent_text_excerpt=text_excerpt[:5000],
        ip_address=ip,
        user_agent=(user_agent or "")[:300],
        granted_at=timezone.now(),
        revoked_at=None if granted else timezone.now(),
        revocation_reason=revocation_reason[:200],
    )


# ----------------------------------------------------------------------------
# Localisation
# ----------------------------------------------------------------------------


def record_location_ping(
    *, traveler, latitude: float, longitude: float,
    accuracy_m: float | None = None, altitude_m: float | None = None,
    speed_mps: float | None = None, heading_deg: float | None = None,
    event_type: str = LocationEventType.DAILY_CHECKIN,
    source: str = LocationSource.PWA,
    device_info: str = "",
) -> TravelerLocationPing | None:
    """Enregistre un ping de localisation, EXCLUSIVEMENT si le voyageur a
    consenti au scope `GEOLOCATION`.

    Retourne None silencieusement (pas d'exception) si pas de consentement,
    pour permettre au check-in de réussir même si la position est
    impossible à collecter — la collecte de position est toujours
    best-effort.
    """
    consent = get_active_consent(traveler, ConsentScope.GEOLOCATION)
    if consent is None:
        return None

    return TravelerLocationPing.objects.create(
        traveler=traveler,
        latitude=latitude,
        longitude=longitude,
        point=Point(float(longitude), float(latitude), srid=4326),
        accuracy_m=accuracy_m,
        altitude_m=altitude_m,
        speed_mps=speed_mps,
        heading_deg=heading_deg,
        event_type=event_type,
        source=source,
        captured_at=timezone.now(),
        consent_version=consent.consent_version,
        device_info=(device_info or "")[:200],
    )


# ----------------------------------------------------------------------------
# Journal d'accès
# ----------------------------------------------------------------------------


def log_data_access(
    *, traveler, user, resource: str, reason: str = "",
    ip: str | None = None, user_agent: str = "",
) -> DataAccessLog:
    """Enregistre un accès agent à des données sensibles."""
    role_label = ""
    try:
        # Récupère le code du premier rôle de l'utilisateur (snapshot)
        first_role = user.role_assignments.select_related("role").first() if user else None
        if first_role and first_role.role:
            role_label = first_role.role.code
    except Exception:  # noqa: BLE001 — best-effort
        role_label = ""

    return DataAccessLog.objects.create(
        traveler=traveler,
        accessed_by=user if (user and user.is_authenticated) else None,
        accessed_by_role=role_label[:40],
        resource=resource,
        reason=(reason or "")[:200],
        ip_address=ip,
        user_agent=(user_agent or "")[:300],
        accessed_at=timezone.now(),
    )


# ----------------------------------------------------------------------------
# Détection des symptômes critiques (pour HealthAlert)
# ----------------------------------------------------------------------------


def evaluate_checkin_severity(symptoms: dict) -> tuple[str, list[str]]:
    """Retourne (severity, reasons[]) à partir d'un dict de symptômes.

    Severity values alignés sur apps.surveillance.HealthAlert.Severity :
    INFO < LOW < MEDIUM < HIGH < CRITICAL.

    Règles (simples, non médicales — à raffiner par l'INHP) :
    - saignement inexpliqué → CRITICAL (red flag)
    - fièvre + 2 autres symptômes → HIGH
    - fièvre seule ou 2+ symptômes → MEDIUM
    - 1 symptôme → LOW
    - rien → INFO
    """
    red_flag = bool(symptoms.get("unexplained_bleeding"))
    fever = bool(symptoms.get("fever"))
    other_keys = ["intense_fatigue", "muscle_joint_pain", "severe_headache",
                  "sore_throat_or_abdominal", "diarrhea_nausea_vomiting"]
    positives = [k for k in other_keys if symptoms.get(k)]
    n_positives = len(positives) + (1 if fever else 0)

    reasons: list[str] = []

    if red_flag:
        reasons.append("Saignements inexpliqués déclarés")
        return "CRITICAL", reasons

    if fever and len(positives) >= 2:
        reasons.append("Fièvre + plusieurs symptômes")
        return "HIGH", reasons

    if fever:
        reasons.append("Fièvre déclarée")
        return "MEDIUM", reasons

    if n_positives >= 2:
        reasons.append(f"{n_positives} symptômes simultanés")
        return "MEDIUM", reasons

    if n_positives == 1:
        return "LOW", [f"Symptôme isolé déclaré"]

    return "INFO", []


def raise_alert_from_checkin(
    *, traveler, symptoms: dict, location: TravelerLocationPing | None = None,
    needs_assistance: bool = False,
) -> object | None:
    """Crée une HealthAlert si nécessaire à partir d'un check-in.

    Retourne l'instance HealthAlert créée, ou None si rien à signaler.
    Le HealthAlert est mis sur le voyageur (target générique). L'app
    surveillance gère la suite (notification dashboard, assignation
    équipe, etc.).
    """
    from django.contrib.contenttypes.models import ContentType
    from apps.surveillance.models import HealthAlert

    if needs_assistance:
        severity = "HIGH"
        reasons = ["Le voyageur a explicitement demandé une assistance"]
        alert_type = "assistance_request"
    else:
        severity, reasons = evaluate_checkin_severity(symptoms)
        if severity == "INFO":
            return None  # rien à signaler
        alert_type = "symptom_declared"

    title_by_sev = {
        "CRITICAL": "🚨 Symptôme critique déclaré",
        "HIGH": "Symptômes importants déclarés",
        "MEDIUM": "Symptômes à surveiller",
        "LOW": "Symptôme isolé",
    }
    summary = title_by_sev.get(severity, "Check-in à surveiller")

    return HealthAlert.objects.create(
        code=f"CHK-{traveler.public_id}",
        title=f"{summary} — {traveler.public_id}",
        description="\n".join(reasons),
        severity=severity,
        status="OPEN",
        target_ct=ContentType.objects.get_for_model(traveler),
        target_id=traveler.pk,
    )
