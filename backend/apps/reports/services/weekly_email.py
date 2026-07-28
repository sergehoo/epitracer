"""Rendu du rapport hebdomadaire en HTML pour email.

Design : palette Côte d'Ivoire (orange #F77F00 / vert #009E60 / dark #003366),
inline CSS uniquement (compat clients email : Outlook, Gmail, iOS Mail).

Contient :
  - Header brandé MSHPCMU/INHP
  - Période + résumé exécutif
  - Grille de KPI cards (voyageurs, suivis, check-ins, alertes)
  - Tableau des niveaux de risque avec % et évolution
  - Comparaison vs semaine précédente
  - Top 5 points d'entrée, districts, maladies
  - Événements marquants
  - Recommandations opérationnelles (auto-générées selon seuils)
  - Lien signé vers le rapport complet
  - Footer avec disclaimer
"""
from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path

from django.conf import settings


# ---------------------------------------------------------------------------
# Chargement des logos officiels en base64 (inline dans le HTML email pour
# compat clients qui bloquent les images externes — Gmail, Outlook, Apple Mail)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=8)
def _logo_data_uri(filename: str) -> str:
    """Charge backend/static/branding/{filename} en data-URI base64.

    Retourne "" si le fichier n'existe pas → le template dégrade proprement
    en n'affichant que le nom textuel.
    """
    try:
        base_dir = Path(getattr(settings, "BASE_DIR", "."))
        path = base_dir / "static" / "branding" / filename
        if not path.exists():
            return ""
        mime = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except Exception:  # noqa: BLE001
        return ""


# ---------------------------------------------------------------------------
# Palette CI (correspond au dashboard admin)
# ---------------------------------------------------------------------------
CI_ORANGE = "#F77F00"
CI_GREEN = "#009E60"
CI_DARK = "#003366"
CI_GOLD = "#D4AF37"
SLATE_50 = "#F8FAFC"
SLATE_100 = "#F1F5F9"
SLATE_200 = "#E2E8F0"
SLATE_600 = "#475569"
SLATE_900 = "#0F172A"
RISK_COLORS = {
    "critical": "#DC2626",
    "high": "#EA580C",
    "moderate": "#EAB308",
    "normal": "#16A34A",
}
RISK_LABELS = {
    "critical": "Critique",
    "high": "Élevé",
    "moderate": "Modéré",
    "normal": "Normal",
}


def _esc(s) -> str:
    """Échappement HTML de toute chaîne (jamais de HTML injection depuis
    des données remontées de la DB)."""
    return html.escape(str(s or ""), quote=True)


def _logo_tag(
    filename: str,
    *,
    alt: str,
    height: int = 64,
    bg: str = "",
    padding: int = 0,
    radius: int = 0,
) -> str:
    """Génère un <img> inline base64 avec fallback texte si le fichier manque.

    Le style est inline (compat email) + limite de hauteur + rendering
    optimisé pour Outlook/Gmail.
    """
    uri = _logo_data_uri(filename)
    if not uri:
        # Fallback : bloc texte discret avec les initiales
        initials = "".join(w[0].upper() for w in alt.split()[:3])[:3]
        return (
            f'<div style="display:inline-block;padding:6px 10px;'
            f'background:{SLATE_100};color:{CI_DARK};font-weight:bold;'
            f'font-size:12px;letter-spacing:1px;border-radius:6px;">'
            f'{initials}</div>'
        )
    wrapper_style = ""
    if bg or padding or radius:
        wrapper_style = (
            f'style="display:inline-block;background:{bg or "transparent"};'
            f'padding:{padding}px;border-radius:{radius}px;"'
        )
        return (
            f'<div {wrapper_style}>'
            f'<img src="{uri}" alt="{_esc(alt)}" height="{height}" '
            f'style="height:{height}px;width:auto;display:block;" /></div>'
        )
    return (
        f'<img src="{uri}" alt="{_esc(alt)}" height="{height}" '
        f'style="height:{height}px;width:auto;display:inline-block;" />'
    )


def _fmt_int(n) -> str:
    """1234 → '1 234' (norme FR)."""
    try:
        return f"{int(n):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(n)


def _delta_badge(delta_pct: float) -> str:
    """Badge HTML compact avec flèche + couleur."""
    if delta_pct > 0:
        arrow = "↑"
        color = "#16A34A"
        bg = "#DCFCE7"
    elif delta_pct < 0:
        arrow = "↓"
        color = "#DC2626"
        bg = "#FEE2E2"
    else:
        arrow = "="
        color = SLATE_600
        bg = SLATE_100
    return (
        f'<span style="background:{bg};color:{color};'
        f'padding:2px 8px;border-radius:10px;font-size:11px;'
        f'font-weight:bold;">{arrow} {abs(delta_pct):.1f}%</span>'
    )


def _generate_recommendations(agg: dict) -> list[str]:
    """Génère 2-4 recommandations opérationnelles selon les seuils.

    Règles simples (à raffiner par l'équipe médicale plus tard) :
      - > 3 cas confirmés → recommander mobilisation
      - > 20% check-ins manqués → recommander rappel SMS bulk
      - > 5 alertes critiques ouvertes → recommander revue INHP
    """
    recos = []

    cases = agg.get("cases", {})
    if cases.get("confirmed", 0) >= 3:
        recos.append(
            f"⚠ {cases['confirmed']} cas confirmés cette semaine — mobiliser "
            "l'équipe d'intervention rapide et rappeler les contacts identifiés."
        )
    if cases.get("suspect", 0) >= 5:
        recos.append(
            f"{cases['suspect']} cas suspects en cours de qualification — "
            "prioriser les prélèvements et analyses en attente."
        )

    checkins = agg.get("checkins", {})
    total_ck = checkins.get("received", 0) + checkins.get("missed", 0)
    if total_ck > 0 and (checkins.get("missed", 0) / total_ck) > 0.20:
        recos.append(
            f"Taux de check-ins manqués élevé ({checkins['missed']}/{total_ck}) — "
            "envisager une campagne de rappel SMS ciblée."
        )

    alerts = agg.get("alerts", {})
    if alerts.get("open", 0) >= 5:
        recos.append(
            f"{alerts['open']} alertes sanitaires ouvertes — organiser une "
            "revue hebdomadaire pour traitement."
        )

    analyses = agg.get("analyses", {})
    if analyses.get("pending", 0) >= 10:
        recos.append(
            f"{analyses['pending']} analyses en attente au laboratoire — "
            "vérifier la capacité de traitement."
        )

    if not recos:
        recos.append(
            "Semaine sans alerte critique. Maintenir la surveillance de routine "
            "et le suivi quotidien des voyageurs en observation."
        )

    return recos


def render_weekly_email_html(agg: dict, *, download_url: str = "", pdf_attached: bool = True) -> str:
    """Retourne le corps HTML complet du rapport pour envoi email.

    Args:
        agg          : dict de aggregate_weekly
        download_url : URL signée (7 jours) vers le rapport complet
        pdf_attached : True si le PDF est en pièce jointe (mention footer)
    """
    period = agg.get("period", {})
    label = _esc(period.get("label", "Semaine"))
    travelers = agg.get("travelers", {})
    followups = agg.get("followups", {})
    checkins = agg.get("checkins", {})
    alerts = agg.get("alerts", {})
    assistance = agg.get("assistance", {})
    risks = agg.get("risk_levels", {})
    cases = agg.get("cases", {})
    samples = agg.get("samples", {})
    analyses = agg.get("analyses", {})
    comparison = agg.get("comparison", {})
    meta = agg.get("meta", {})

    # ==== KPI cards ====
    kpi_cards = _render_kpi_cards(travelers, followups, checkins, alerts, assistance)

    # ==== Tableau des niveaux de risque ====
    risk_table = _render_risk_table(risks)

    # ==== Comparaison ====
    comp_html = _render_comparison(comparison)

    # ==== Cases + labo ====
    cases_html = _render_cases_lab(cases, samples, analyses)

    # ==== Répartitions ====
    breakdowns = _render_breakdowns(agg)

    # ==== Événements marquants ====
    events_html = _render_events(agg.get("top_events", []))

    # ==== Recommandations ====
    recos = _generate_recommendations(agg)
    recos_html = "\n".join(
        f'<li style="margin-bottom:8px;line-height:1.5;">{_esc(r)}</li>' for r in recos
    )

    # ==== Bouton download ====
    download_btn = ""
    if download_url:
        download_btn = f"""
        <div style="text-align:center;margin:32px 0;">
          <a href="{_esc(download_url)}"
             style="display:inline-block;background:{CI_ORANGE};color:#fff;
                    padding:14px 28px;text-decoration:none;border-radius:8px;
                    font-weight:bold;font-size:14px;">
            📄 Télécharger le rapport complet (PDF + Excel)
          </a>
          <div style="color:{SLATE_600};font-size:11px;margin-top:8px;">
            Lien signé valable 7 jours — accès réservé au destinataire.
          </div>
        </div>
        """

    pdf_note = ""
    if pdf_attached:
        pdf_note = (
            f'<p style="color:{SLATE_600};font-size:12px;font-style:italic;">'
            "Le PDF est également joint à cet email pour archivage.</p>"
        )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Rapport hebdomadaire EpiTrace — {label}</title>
</head>
<body style="margin:0;padding:0;background:{SLATE_50};font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:{SLATE_900};">

<!-- Container principal -->
<table role="presentation" cellpadding="0" cellspacing="0" width="100%" style="background:{SLATE_50};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" cellpadding="0" cellspacing="0" width="640" style="max-width:640px;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 12px rgba(0,0,0,0.08);">

<!-- Bandeau tricolore CI -->
<tr><td style="padding:0;">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr>
    <td style="background:{CI_ORANGE};height:8px;"></td>
    <td style="background:#fff;height:8px;"></td>
    <td style="background:{CI_GREEN};height:8px;"></td>
  </tr></table>
</td></tr>

<!-- Bandeau institutionnel — 3 logos officiels + titre -->
<tr><td style="background:#fff;padding:20px 32px 8px 32px;border-bottom:1px solid {SLATE_200};">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <!-- Logo MSHPCMU (gauche) -->
      <td width="80" style="vertical-align:middle;text-align:left;">
        {_logo_tag("mshpcmu.png", alt="MSHPCMU", height=64)}
      </td>
      <!-- Titre institutionnel (centre) -->
      <td style="vertical-align:middle;text-align:center;padding:0 12px;">
        <div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:{CI_ORANGE};font-weight:900;">
          République de Côte d'Ivoire
        </div>
        <div style="font-size:11px;color:{SLATE_600};font-style:italic;margin-top:2px;">
          Union &middot; Discipline &middot; Travail
        </div>
        <div style="font-size:11px;color:{CI_DARK};font-weight:bold;margin-top:6px;line-height:1.35;">
          Ministère de la Santé, de l'Hygiène Publique<br>
          et de la Couverture Maladie Universelle
        </div>
        <div style="font-size:10px;color:{SLATE_600};margin-top:3px;">
          Institut National d'Hygiène Publique — INHP
        </div>
      </td>
      <!-- Armoirie République CI (droite) -->
      <td width="80" style="vertical-align:middle;text-align:right;">
        {_logo_tag("armoirie.png", alt="Armoirie de la République", height=64)}
      </td>
    </tr>
  </table>
</td></tr>

<!-- Titre du rapport -->
<tr><td style="background:{CI_DARK};padding:22px 32px;color:#fff;">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td style="vertical-align:middle;">
        <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:{CI_GOLD};font-weight:bold;">
          Veille sanitaire nationale
        </div>
        <h1 style="margin:6px 0 4px 0;font-size:22px;font-weight:900;line-height:1.25;">
          Rapport hebdomadaire de surveillance
        </h1>
        <div style="font-size:13px;opacity:0.9;">
          {label} · Fuseau <strong>{_esc(meta.get("tz", "Africa/Abidjan"))}</strong>
        </div>
      </td>
      <!-- Logo INHP à droite du titre -->
      <td width="70" style="vertical-align:middle;text-align:right;">
        {_logo_tag("inhp.png", alt="INHP", height=56, bg="rgba(255,255,255,0.10)", padding=6, radius=8)}
      </td>
    </tr>
  </table>
</td></tr>

<!-- Contenu -->
<tr><td style="padding:32px;">

<!-- Résumé exécutif -->
<h2 style="color:{CI_DARK};font-size:18px;margin:0 0 12px 0;
           border-bottom:2px solid {CI_ORANGE};padding-bottom:8px;">
  Résumé exécutif
</h2>
{_render_exec_summary(travelers, followups, checkins, assistance, alerts, label)}

<!-- KPI cards -->
{kpi_cards}

<!-- Niveaux de risque -->
<h2 style="color:{CI_DARK};font-size:18px;margin:32px 0 12px 0;
           border-bottom:2px solid {CI_ORANGE};padding-bottom:8px;">
  Répartition par niveau de risque
</h2>
{risk_table}

<!-- Comparaison semaine précédente -->
<h2 style="color:{CI_DARK};font-size:18px;margin:32px 0 12px 0;
           border-bottom:2px solid {CI_ORANGE};padding-bottom:8px;">
  Comparaison avec la semaine précédente
</h2>
{comp_html}

<!-- Cas + labo -->
<h2 style="color:{CI_DARK};font-size:18px;margin:32px 0 12px 0;
           border-bottom:2px solid {CI_ORANGE};padding-bottom:8px;">
  Classification épidémiologique et laboratoire
</h2>
{cases_html}

<!-- Répartitions -->
{breakdowns}

<!-- Événements marquants -->
{events_html}

<!-- Recommandations opérationnelles -->
<h2 style="color:{CI_DARK};font-size:18px;margin:32px 0 12px 0;
           border-bottom:2px solid {CI_ORANGE};padding-bottom:8px;">
  Recommandations opérationnelles
</h2>
<ul style="padding-left:24px;margin:0 0 24px 0;color:{SLATE_900};">
  {recos_html}
</ul>

<!-- Bouton download -->
{download_btn}
{pdf_note}

</td></tr>

<!-- Footer institutionnel -->
<tr><td style="background:{SLATE_100};padding:22px 32px;color:{SLATE_600};font-size:12px;line-height:1.55;border-top:1px solid {SLATE_200};">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
    <tr>
      <td style="vertical-align:top;">
        <div style="color:{CI_DARK};font-weight:900;font-size:13px;">
          EpiTrace / Mon Pass Sanitaire
        </div>
        <div style="margin-top:4px;">
          Institut National d'Hygiène Publique — INHP<br>
          Ministère de la Santé, de l'Hygiène Publique<br>
          et de la Couverture Maladie Universelle
        </div>
        <div style="margin-top:8px;">
          <strong>Contact :</strong> inhp@veillesanitaire.com<br>
          <strong>Assistance :</strong> 143 · SAMU 185
        </div>
      </td>
      <td style="vertical-align:top;text-align:right;">
        <div style="font-size:10px;color:{SLATE_600};">
          Généré le<br>
          <strong style="color:{CI_DARK};">{_esc(meta.get("generated_at", ""))[:19].replace("T", " à ")}</strong>
        </div>
        <div style="font-size:9px;color:{SLATE_600};margin-top:6px;">
          Durée {meta.get("generation_ms", 0)} ms · Schéma v{meta.get("schema_version", 1)}
        </div>
      </td>
    </tr>
  </table>
  <div style="border-top:1px dashed {SLATE_200};margin:14px 0 10px 0;"></div>
  <p style="margin:0;font-size:10px;font-style:italic;color:{SLATE_600};">
    Ce document est <strong>confidentiel</strong>. Ne pas rediffuser sans
    autorisation MSHPCMU. Conservation légale : 5 ans conformément à l'arrêté
    ministériel MSHPCMU.
  </p>
</td></tr>
<!-- Bande tricolore de pied -->
<tr><td style="padding:0;">
  <table role="presentation" cellpadding="0" cellspacing="0" width="100%"><tr>
    <td style="background:{CI_ORANGE};height:5px;"></td>
    <td style="background:#fff;height:5px;"></td>
    <td style="background:{CI_GREEN};height:5px;"></td>
  </tr></table>
</td></tr>

</table>
</td></tr>
</table>

</body>
</html>"""


# ---------------------------------------------------------------------------
# Helpers internes de rendu (isolés pour lisibilité)
# ---------------------------------------------------------------------------
def _render_exec_summary(travelers, followups, checkins, assistance, alerts, label) -> str:
    """Résumé exécutif adaptatif : formule différente si activité nulle."""
    n_travelers = travelers.get("registered", 0)
    n_active = travelers.get("active_followup", 0)
    n_new_fu = followups.get("new", 0)
    n_done_fu = followups.get("completed", 0)
    n_checkins = checkins.get("received", 0)
    n_missed = checkins.get("missed", 0)
    n_assist = assistance.get("requests", 0)
    n_alerts_open = alerts.get("open", 0)

    total_activity = n_travelers + n_new_fu + n_checkins + n_alerts_open

    if total_activity == 0:
        # Semaine sans activité
        return (
            f'<div style="background:{SLATE_50};border-left:4px solid {CI_GREEN};'
            f'padding:14px 18px;border-radius:0 8px 8px 0;margin:0 0 20px 0;">'
            f'<p style="margin:0;line-height:1.6;color:{SLATE_900};">'
            f'<strong style="color:{CI_GREEN};">Semaine calme</strong> — '
            f'aucune activité enregistrée sur la période <strong>{label}</strong>. '
            f'La surveillance de routine reste active.'
            f'</p></div>'
        )

    return (
        f'<div style="background:{SLATE_50};border-left:4px solid {CI_ORANGE};'
        f'padding:14px 18px;border-radius:0 8px 8px 0;margin:0 0 20px 0;">'
        f'<p style="line-height:1.6;color:{SLATE_900};margin:0;">'
        f'Sur la période <strong>{label}</strong>, EpiTrace a enregistré '
        f'<strong>{_fmt_int(n_travelers)} voyageurs</strong>, '
        f'ouvert <strong>{n_new_fu} nouveaux suivis</strong>, '
        f'clos <strong>{n_done_fu} suivis</strong> et compte '
        f'<strong>{_fmt_int(n_active)} personnes actuellement en suivi actif</strong>. '
        f'Les équipes ont reçu <strong>{_fmt_int(n_checkins)} check-ins</strong> '
        f'quotidiens ({n_missed} manqués) et traité '
        f'<strong>{n_assist} demandes d\'assistance</strong>. '
        f'{n_alerts_open} <strong>alertes sanitaires</strong> restent ouvertes.'
        f'</p></div>'
    )



def _render_kpi_cards(travelers, followups, checkins, alerts, assistance) -> str:
    cards = [
        ("Voyageurs enregistrés", _fmt_int(travelers.get("registered", 0)), CI_ORANGE),
        ("En suivi actif", _fmt_int(travelers.get("active_followup", 0)), CI_GREEN),
        ("Nouveaux suivis", followups.get("new", 0), CI_DARK),
        ("Check-ins reçus", _fmt_int(checkins.get("received", 0)), CI_GREEN),
        ("Check-ins manqués", checkins.get("missed", 0), "#DC2626"),
        ("Demandes d'assistance", assistance.get("requests", 0), CI_GOLD),
        ("Alertes créées", alerts.get("created", 0), CI_ORANGE),
        ("Alertes ouvertes", alerts.get("open", 0), "#DC2626"),
    ]
    cells = ""
    for i, (label, value, color) in enumerate(cards):
        if i % 2 == 0 and i > 0:
            cells += "</tr><tr>"
        elif i == 0:
            cells += "<tr>"
        cells += f"""
        <td style="width:50%;padding:8px;">
          <div style="border-left:4px solid {color};background:{SLATE_50};padding:16px;border-radius:0 8px 8px 0;">
            <div style="font-size:11px;color:{SLATE_600};text-transform:uppercase;letter-spacing:1px;font-weight:bold;">{_esc(label)}</div>
            <div style="font-size:26px;font-weight:900;color:{CI_DARK};margin-top:4px;">{value}</div>
          </div>
        </td>
        """
    cells += "</tr>"
    return f'<table role="presentation" cellpadding="0" cellspacing="0" width="100%">{cells}</table>'


def _render_risk_table(risks: dict) -> str:
    total = risks.get("total", 0)
    rows = ""
    for level in ("critical", "high", "moderate", "normal"):
        data = risks.get(level, {}) or {}
        cnt = data.get("count", 0)
        pct = data.get("pct", 0)
        color = RISK_COLORS[level]
        label = RISK_LABELS[level]
        rows += f"""
        <tr>
          <td style="padding:12px 16px;border-bottom:1px solid {SLATE_200};">
            <span style="display:inline-block;width:12px;height:12px;background:{color};border-radius:2px;margin-right:8px;vertical-align:middle;"></span>
            <strong>{label}</strong>
          </td>
          <td style="padding:12px 16px;border-bottom:1px solid {SLATE_200};text-align:right;font-weight:bold;">{_fmt_int(cnt)}</td>
          <td style="padding:12px 16px;border-bottom:1px solid {SLATE_200};text-align:right;color:{SLATE_600};">{pct} %</td>
        </tr>"""
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
           style="border-collapse:collapse;border:1px solid {SLATE_200};border-radius:8px;overflow:hidden;">
      <thead style="background:{SLATE_50};">
        <tr>
          <th style="padding:12px 16px;text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{SLATE_600};">Niveau</th>
          <th style="padding:12px 16px;text-align:right;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{SLATE_600};">Nombre</th>
          <th style="padding:12px 16px;text-align:right;font-size:11px;text-transform:uppercase;letter-spacing:1px;color:{SLATE_600};">Part</th>
        </tr>
      </thead>
      <tbody>{rows}
      <tr>
        <td style="padding:12px 16px;font-weight:bold;background:{SLATE_100};"><strong>TOTAL</strong></td>
        <td style="padding:12px 16px;text-align:right;font-weight:bold;background:{SLATE_100};">{_fmt_int(total)}</td>
        <td style="padding:12px 16px;text-align:right;background:{SLATE_100};">100 %</td>
      </tr>
      </tbody>
    </table>
    """


def _render_comparison(comp: dict) -> str:
    rows = ""
    labels = {
        "travelers": "Voyageurs enregistrés",
        "followups_new": "Nouveaux suivis",
        "checkins_received": "Check-ins reçus",
        "alerts_created": "Alertes créées",
    }
    for key, label in labels.items():
        data = comp.get(key, {}) or {}
        cur = data.get("current", 0)
        prev = data.get("previous", 0)
        delta = data.get("delta_pct", 0.0)
        rows += f"""
        <tr>
          <td style="padding:10px 16px;border-bottom:1px solid {SLATE_200};">{_esc(label)}</td>
          <td style="padding:10px 16px;border-bottom:1px solid {SLATE_200};text-align:right;font-weight:bold;">{_fmt_int(cur)}</td>
          <td style="padding:10px 16px;border-bottom:1px solid {SLATE_200};text-align:right;color:{SLATE_600};">{_fmt_int(prev)}</td>
          <td style="padding:10px 16px;border-bottom:1px solid {SLATE_200};text-align:right;">{_delta_badge(delta)}</td>
        </tr>"""
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%"
           style="border-collapse:collapse;border:1px solid {SLATE_200};border-radius:8px;overflow:hidden;">
      <thead style="background:{SLATE_50};">
        <tr>
          <th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;color:{SLATE_600};">Indicateur</th>
          <th style="padding:10px 16px;text-align:right;font-size:11px;text-transform:uppercase;color:{SLATE_600};">Actuel</th>
          <th style="padding:10px 16px;text-align:right;font-size:11px;text-transform:uppercase;color:{SLATE_600};">Précédent</th>
          <th style="padding:10px 16px;text-align:right;font-size:11px;text-transform:uppercase;color:{SLATE_600};">Évolution</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
    """


def _render_cases_lab(cases, samples, analyses) -> str:
    return f"""
    <table role="presentation" cellpadding="0" cellspacing="0" width="100%">
      <tr>
        <td style="padding:8px;width:50%;">
          <div style="background:{SLATE_50};padding:16px;border-radius:8px;">
            <div style="font-size:11px;text-transform:uppercase;color:{SLATE_600};font-weight:bold;margin-bottom:12px;">Cas classifiés</div>
            <div>Suspects : <strong>{cases.get("suspect", 0)}</strong></div>
            <div>Probables : <strong>{cases.get("probable", 0)}</strong></div>
            <div>Confirmés : <strong style="color:#DC2626;">{cases.get("confirmed", 0)}</strong></div>
            <div>Exclus : <strong>{cases.get("discarded", 0)}</strong></div>
          </div>
        </td>
        <td style="padding:8px;width:50%;">
          <div style="background:{SLATE_50};padding:16px;border-radius:8px;">
            <div style="font-size:11px;text-transform:uppercase;color:{SLATE_600};font-weight:bold;margin-bottom:12px;">Laboratoire</div>
            <div>Prélèvements demandés : <strong>{samples.get("requested", 0)}</strong></div>
            <div>Prélèvements réalisés : <strong>{samples.get("collected", 0)}</strong></div>
            <div>Analyses en attente : <strong>{analyses.get("pending", 0)}</strong></div>
            <div>Positives : <strong style="color:#DC2626;">{analyses.get("positive", 0)}</strong></div>
            <div>Négatives : <strong style="color:#16A34A;">{analyses.get("negative", 0)}</strong></div>
          </div>
        </td>
      </tr>
    </table>
    """


def _render_breakdowns(agg: dict) -> str:
    sections = []
    for key, title, emoji in [
        ("by_entry_point", "Top points d'entrée", "🛬"),
        ("by_district", "Top districts sanitaires", "📍"),
        ("by_disease", "Top maladies surveillées", "🦠"),
    ]:
        rows = agg.get(key, [])[:5]
        if not rows:
            continue
        items = "".join(
            f'<li style="margin-bottom:6px;"><span>{_esc(r.get("name", "—"))}</span> '
            f'<span style="float:right;font-weight:bold;color:{CI_ORANGE};">{_fmt_int(r.get("count", 0))}</span></li>'
            for r in rows
        )
        sections.append(f"""
        <h3 style="color:{CI_DARK};font-size:14px;margin:24px 0 8px 0;">{emoji} {title}</h3>
        <ul style="list-style:none;padding:12px 16px;background:{SLATE_50};border-radius:8px;margin:0;">
          {items}
        </ul>
        """)
    return "".join(sections)


def _render_events(events: list) -> str:
    if not events:
        return ""
    items = ""
    for ev in events[:10]:
        sev = ev.get("severity", "")
        color = "#DC2626" if sev == "critical" else "#EA580C" if sev == "high" else SLATE_600
        items += f"""
        <li style="margin-bottom:8px;padding:8px 12px;background:{SLATE_50};border-left:3px solid {color};border-radius:0 6px 6px 0;">
          <strong style="color:{color};">{_esc(ev.get("type", ""))}</strong> — {_esc(ev.get("title", ""))}
          <span style="float:right;color:{SLATE_600};font-size:11px;">{_esc(ev.get("at", ""))[:16].replace("T", " à ")}</span>
        </li>"""
    return f"""
    <h2 style="color:{CI_DARK};font-size:18px;margin:32px 0 12px 0;
               border-bottom:2px solid {CI_ORANGE};padding-bottom:8px;">
      Événements marquants
    </h2>
    <ul style="list-style:none;padding:0;margin:0;">{items}</ul>
    """
