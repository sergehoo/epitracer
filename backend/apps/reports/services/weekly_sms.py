"""Rendu du rapport hebdomadaire en SMS synthétique.

Contraintes :
  - Longueur max 460 caractères (3 segments SMS GSM-7 = 3×153).
    Au-delà, on tronque + suffix "...".
  - Aucune PII : uniquement des agrégats (invariant #3).
  - Aucun URL brut si non-signé (le shortlink est ajouté par le caller
    s'il fournit un download_url signé et éphémère).

Format cible :
    "EpiTrace — RAP-HEBDO-2026-S24 (08→14 juin) : 1245 voyageurs, 45 nouveaux
    suivis. Risques : 4 critiques, 18 élevés, 62 modérés, 1161 normaux.
    7 alertes ouvertes, 5 résolues. Détails par email."
"""
from __future__ import annotations

MAX_SMS_LEN = 460
BRAND = "EpiTrace"


def render_weekly_sms(agg: dict, *, download_url: str = "", brand: str = BRAND) -> str:
    """Retourne le corps du SMS synthétique. Toujours < MAX_SMS_LEN.

    Args:
        agg          : dict retourné par aggregate_weekly
        download_url : URL signée courte optionnelle (ex. bit.ly ou signed_url courte)
        brand        : préfixe (par défaut "EpiTrace")
    """
    period = agg.get("period", {})
    label = period.get("label", "").split(" (", 1)
    week_short = label[1].rstrip(")") if len(label) > 1 else period.get("label", "")

    travelers = agg.get("travelers", {})
    followups = agg.get("followups", {})
    risks = agg.get("risk_levels", {})
    alerts = agg.get("alerts", {})

    # Compteurs (avec fallback 0 partout)
    n_travelers = travelers.get("registered", 0)
    n_new_followups = followups.get("new", 0)
    n_crit = (risks.get("critical") or {}).get("count", 0)
    n_high = (risks.get("high") or {}).get("count", 0)
    n_mod = (risks.get("moderate") or {}).get("count", 0)
    n_norm = (risks.get("normal") or {}).get("count", 0)
    n_open = alerts.get("open", 0)
    n_resolved = alerts.get("resolved", 0)

    # Version longue — la plus informative
    body_long = (
        f"{brand} — Rapport {week_short} : "
        f"{n_travelers:,} voyageurs, {n_new_followups} nouveaux suivis. "
        f"Risques : {n_crit} critiques, {n_high} élevés, {n_mod} modérés, {n_norm} normaux. "
        f"Alertes : {n_open} ouvertes, {n_resolved} résolues. "
        "Détail complet par email."
    ).replace(",", " ")  # séparateur milliers = espace (norme FR)

    if download_url:
        body_long += f" {download_url}"

    if len(body_long) <= MAX_SMS_LEN:
        return body_long

    # Version courte — priorité aux risques + total voyageurs
    body_short = (
        f"{brand} — {week_short} : {n_travelers} voyageurs. "
        f"Risques {n_crit}C/{n_high}E/{n_mod}M. "
        f"Alertes {n_open} ouv./{n_resolved} rés. Détails email."
    )
    if download_url and len(body_short) + len(download_url) + 1 <= MAX_SMS_LEN:
        body_short += f" {download_url}"

    if len(body_short) <= MAX_SMS_LEN:
        return body_short

    # Ultra-court fallback (ne devrait jamais arriver, mais safety)
    return body_short[: MAX_SMS_LEN - 3] + "..."


def validate_no_pii(sms_body: str) -> tuple[bool, list[str]]:
    """Vérifie que le SMS ne contient AUCUN motif PII (invariant #3).

    Motifs interdits :
      - TRV-XXXX (identifiant voyageur)
      - +225XXXXXXXXXX (numéro CI)
      - email@domain (email)

    Retourne (is_clean, list_of_violations).
    """
    import re
    violations = []
    if re.search(r"\bTRV-[A-Z0-9]{5,}\b", sms_body):
        violations.append("Contient un identifiant voyageur TRV-XXX")
    if re.search(r"\+\d{10,15}\b", sms_body):
        violations.append("Contient un numéro de téléphone en clair")
    if re.search(r"\b[\w.+-]+@[\w-]+\.[a-z]{2,}\b", sms_body):
        violations.append("Contient une adresse email")
    return (len(violations) == 0), violations
