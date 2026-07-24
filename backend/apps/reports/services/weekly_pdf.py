"""Rendu du rapport hebdomadaire au format PDF A4.

Utilise reportlab (déjà installé). Design cohérent avec l'existant :
  - Bandeau tricolore CI + header institutionnel
  - Sections : Résumé, Risques, Cas, Labo, Répartitions, Événements
  - Footer avec disclaimer + code rapport + généré le
"""
from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


CI_ORANGE = colors.HexColor("#F77F00")
CI_GREEN = colors.HexColor("#009E60")
CI_DARK = colors.HexColor("#003366")
CI_GOLD = colors.HexColor("#D4AF37")
CI_WHITE = colors.white
SLATE_50 = colors.HexColor("#F8FAFC")
SLATE_100 = colors.HexColor("#F1F5F9")
SLATE_600 = colors.HexColor("#475569")
SLATE_900 = colors.HexColor("#0F172A")
RED = colors.HexColor("#DC2626")
GREEN = colors.HexColor("#16A34A")


def _fmt_int(n) -> str:
    try:
        return f"{int(n):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(n)


def render_weekly_pdf(agg: dict) -> bytes:
    """Retourne les bytes d'un PDF A4 contenant le rapport hebdomadaire."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4  # 210 x 297 mm

    period = agg.get("period", {})
    meta = agg.get("meta", {})
    label = period.get("label", "Semaine")

    # ─── Bandeau tricolore ──────────────────────────────────────────
    c.setFillColor(CI_ORANGE); c.rect(0, H - 3, W / 3, 3, stroke=0, fill=1)
    c.setFillColor(CI_WHITE);  c.rect(W / 3, H - 3, W / 3, 3, stroke=0, fill=1)
    c.setFillColor(CI_GREEN);  c.rect(2 * W / 3, H - 3, W / 3, 3, stroke=0, fill=1)

    # ─── En-tête institutionnel ─────────────────────────────────────
    c.setFillColor(CI_DARK)
    c.rect(0, H - 32 * mm, W, 29 * mm, stroke=0, fill=1)
    c.setFillColor(CI_GOLD); c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(W / 2, H - 12 * mm, "MSHPCMU · INHP · République de Côte d'Ivoire")
    c.setFillColor(CI_WHITE); c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(W / 2, H - 20 * mm, "Rapport hebdomadaire de surveillance sanitaire")
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(W / 2, H - 27 * mm, f"{label} — Fuseau {meta.get('tz', 'Africa/Abidjan')}")

    y = H - 42 * mm

    # ─── Section : Résumé ───────────────────────────────────────────
    y = _section_title(c, "Résumé exécutif", y, W)
    travelers = agg.get("travelers", {})
    followups = agg.get("followups", {})
    checkins = agg.get("checkins", {})
    alerts = agg.get("alerts", {})
    assistance = agg.get("assistance", {})

    kpis = [
        ("Voyageurs enregistrés", _fmt_int(travelers.get("registered", 0)), CI_ORANGE),
        ("En suivi actif", _fmt_int(travelers.get("active_followup", 0)), CI_GREEN),
        ("Nouveaux suivis", str(followups.get("new", 0)), CI_DARK),
        ("Suivis terminés", str(followups.get("completed", 0)), CI_GREEN),
        ("Check-ins reçus", _fmt_int(checkins.get("received", 0)), CI_GREEN),
        ("Check-ins manqués", str(checkins.get("missed", 0)), RED),
        ("Demandes d'assistance", str(assistance.get("requests", 0)), CI_GOLD),
        ("Alertes ouvertes", str(alerts.get("open", 0)), RED),
    ]
    y = _draw_kpi_grid(c, kpis, y, W, cols=4, cell_h=18 * mm)

    # ─── Section : Risques ──────────────────────────────────────────
    y -= 6 * mm
    y = _section_title(c, "Répartition par niveau de risque", y, W)
    risks = agg.get("risk_levels", {})
    risk_rows = [
        ("Critique", risks.get("critical", {}), RED),
        ("Élevé", risks.get("high", {}), colors.HexColor("#EA580C")),
        ("Modéré", risks.get("moderate", {}), colors.HexColor("#EAB308")),
        ("Normal", risks.get("normal", {}), GREEN),
    ]
    y = _draw_risk_table(c, risk_rows, risks.get("total", 0), y, W)

    # ─── Section : Cas + Laboratoire ────────────────────────────────
    y -= 8 * mm
    y = _section_title(c, "Classification épidémiologique & Laboratoire", y, W)
    cases = agg.get("cases", {})
    samples = agg.get("samples", {})
    analyses = agg.get("analyses", {})
    y = _draw_two_col_lists(c, [
        ("Cas classifiés", [
            f"Suspects : {cases.get('suspect', 0)}",
            f"Probables : {cases.get('probable', 0)}",
            f"Confirmés : {cases.get('confirmed', 0)}",
            f"Exclus : {cases.get('discarded', 0)}",
        ]),
        ("Laboratoire", [
            f"Prélèvements demandés : {samples.get('requested', 0)}",
            f"Prélèvements réalisés : {samples.get('collected', 0)}",
            f"Analyses en attente : {analyses.get('pending', 0)}",
            f"Analyses positives : {analyses.get('positive', 0)}",
            f"Analyses négatives : {analyses.get('negative', 0)}",
        ]),
    ], y, W)

    # ─── Section : Comparaison ──────────────────────────────────────
    y -= 8 * mm
    y = _section_title(c, "Comparaison avec la semaine précédente", y, W)
    comp = agg.get("comparison", {})
    comp_rows = [
        ("Voyageurs enregistrés", comp.get("travelers", {})),
        ("Nouveaux suivis", comp.get("followups_new", {})),
        ("Check-ins reçus", comp.get("checkins_received", {})),
        ("Alertes créées", comp.get("alerts_created", {})),
    ]
    y = _draw_comparison_table(c, comp_rows, y, W)

    # Nouvelle page si peu de place
    if y < 60 * mm:
        _draw_footer(c, W, meta, agg)
        c.showPage()
        y = H - 15 * mm

    # ─── Section : Répartitions ─────────────────────────────────────
    y -= 8 * mm
    y = _section_title(c, "Répartitions géographiques et épidémiologiques", y, W)
    y = _draw_breakdown_list(c, "Points d'entrée", agg.get("by_entry_point", [])[:8], y, W)
    y -= 4 * mm
    y = _draw_breakdown_list(c, "Districts sanitaires", agg.get("by_district", [])[:8], y, W)
    y -= 4 * mm
    y = _draw_breakdown_list(c, "Maladies surveillées", agg.get("by_disease", [])[:8], y, W)

    # ─── Footer ────────────────────────────────────────────────────
    _draw_footer(c, W, meta, agg)
    c.showPage()
    c.save()
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Helpers de rendu
# ---------------------------------------------------------------------------
def _section_title(c, title: str, y: float, W: float) -> float:
    c.setFillColor(CI_ORANGE); c.rect(10 * mm, y - 2, 2, 6 * mm, stroke=0, fill=1)
    c.setFillColor(CI_DARK); c.setFont("Helvetica-Bold", 13)
    c.drawString(14 * mm, y, title)
    c.setStrokeColor(SLATE_100); c.setLineWidth(0.5)
    c.line(14 * mm, y - 2, W - 10 * mm, y - 2)
    return y - 10 * mm


def _draw_kpi_grid(c, kpis: list, y: float, W: float, cols: int = 4, cell_h: float = 20 * mm) -> float:
    margin = 10 * mm
    cell_w = (W - 2 * margin) / cols
    for i, (label, value, color) in enumerate(kpis):
        row = i // cols
        col = i % cols
        x = margin + col * cell_w
        cy = y - row * cell_h - 2

        c.setFillColor(SLATE_50)
        c.roundRect(x + 1, cy - cell_h + 2, cell_w - 2, cell_h - 4, 2, stroke=0, fill=1)
        c.setFillColor(color); c.rect(x + 1, cy - cell_h + 2, 3, cell_h - 4, stroke=0, fill=1)

        c.setFillColor(SLATE_600); c.setFont("Helvetica-Bold", 6.5)
        c.drawString(x + 6, cy - 4, label.upper()[:26])
        c.setFillColor(CI_DARK); c.setFont("Helvetica-Bold", 15)
        c.drawString(x + 6, cy - 14, value)
    rows = (len(kpis) + cols - 1) // cols
    return y - rows * cell_h


def _draw_risk_table(c, rows: list, total: int, y: float, W: float) -> float:
    margin = 10 * mm
    row_h = 8 * mm
    col_widths = [(W - 2 * margin) * r for r in [0.45, 0.25, 0.30]]

    # Header
    c.setFillColor(SLATE_100)
    c.rect(margin, y - row_h, W - 2 * margin, row_h, stroke=0, fill=1)
    c.setFillColor(SLATE_600); c.setFont("Helvetica-Bold", 8)
    c.drawString(margin + 4, y - row_h + 3, "NIVEAU")
    c.drawRightString(margin + col_widths[0] + col_widths[1] - 4, y - row_h + 3, "NOMBRE")
    c.drawRightString(W - margin - 4, y - row_h + 3, "PART")
    y -= row_h

    for label, data, color in rows:
        cnt = data.get("count", 0)
        pct = data.get("pct", 0)
        c.setFillColor(color); c.rect(margin + 4, y - row_h + 3, 3, 3, stroke=0, fill=1)
        c.setFillColor(SLATE_900); c.setFont("Helvetica-Bold", 10)
        c.drawString(margin + 12, y - row_h + 3, label)
        c.drawRightString(margin + col_widths[0] + col_widths[1] - 4, y - row_h + 3, _fmt_int(cnt))
        c.setFillColor(SLATE_600); c.setFont("Helvetica", 10)
        c.drawRightString(W - margin - 4, y - row_h + 3, f"{pct} %")
        c.setStrokeColor(SLATE_100); c.line(margin, y - row_h, W - margin, y - row_h)
        y -= row_h

    # Total
    c.setFillColor(SLATE_100); c.rect(margin, y - row_h, W - 2 * margin, row_h, stroke=0, fill=1)
    c.setFillColor(CI_DARK); c.setFont("Helvetica-Bold", 10)
    c.drawString(margin + 4, y - row_h + 3, "TOTAL")
    c.drawRightString(margin + col_widths[0] + col_widths[1] - 4, y - row_h + 3, _fmt_int(total))
    c.drawRightString(W - margin - 4, y - row_h + 3, "100 %")
    return y - row_h - 2


def _draw_two_col_lists(c, cols: list, y: float, W: float) -> float:
    margin = 10 * mm
    col_w = (W - 2 * margin - 4 * mm) / 2
    start_y = y
    for i, (title, items) in enumerate(cols):
        x = margin + i * (col_w + 4 * mm)
        c.setFillColor(SLATE_50)
        c.roundRect(x, start_y - (len(items) * 5 * mm + 10 * mm), col_w,
                    len(items) * 5 * mm + 10 * mm, 3, stroke=0, fill=1)
        c.setFillColor(SLATE_600); c.setFont("Helvetica-Bold", 7)
        c.drawString(x + 4, start_y - 6, title.upper())
        c.setFillColor(SLATE_900); c.setFont("Helvetica", 10)
        for j, line in enumerate(items):
            c.drawString(x + 4, start_y - 12 - j * 5 * mm, line)
    return start_y - (max(len(cols[0][1]), len(cols[1][1])) * 5 * mm + 10 * mm)


def _draw_comparison_table(c, rows: list, y: float, W: float) -> float:
    margin = 10 * mm
    row_h = 7 * mm
    for label, data in rows:
        cur = data.get("current", 0)
        prev = data.get("previous", 0)
        delta = data.get("delta_pct", 0.0)
        c.setFillColor(SLATE_900); c.setFont("Helvetica", 10)
        c.drawString(margin + 4, y - row_h + 3, label)
        c.setFillColor(SLATE_600)
        c.drawRightString(W / 2, y - row_h + 3, f"Actuel : {_fmt_int(cur)}")
        c.drawRightString(W / 2 + 40 * mm, y - row_h + 3, f"Préc. : {_fmt_int(prev)}")
        arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "=")
        color = GREEN if delta > 0 else (RED if delta < 0 else SLATE_600)
        c.setFillColor(color); c.setFont("Helvetica-Bold", 10)
        c.drawRightString(W - margin - 4, y - row_h + 3, f"{arrow} {abs(delta):.1f} %")
        c.setStrokeColor(SLATE_100); c.line(margin, y - row_h, W - margin, y - row_h)
        y -= row_h
    return y


def _draw_breakdown_list(c, title: str, items: list, y: float, W: float) -> float:
    if not items:
        return y
    margin = 10 * mm
    c.setFillColor(CI_DARK); c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, title)
    y -= 5 * mm
    max_count = max((it.get("count", 1) for it in items), default=1)
    for it in items[:8]:
        name = str(it.get("name", "—"))[:60]
        cnt = it.get("count", 0)
        c.setFillColor(SLATE_900); c.setFont("Helvetica", 8)
        c.drawString(margin + 2, y, name)
        c.setFillColor(CI_ORANGE); c.setFont("Helvetica-Bold", 8)
        c.drawRightString(W - margin - 2, y, _fmt_int(cnt))
        # Barre de progression
        bar_w = (W - 2 * margin - 6 * mm) * (cnt / max_count)
        c.setFillColor(SLATE_100); c.rect(margin + 2, y - 2, W - 2 * margin - 4 * mm, 1, stroke=0, fill=1)
        c.setFillColor(CI_ORANGE); c.rect(margin + 2, y - 2, bar_w, 1, stroke=0, fill=1)
        y -= 4.5 * mm
    return y


def _draw_footer(c, W: float, meta: dict, agg: dict):
    c.setFillColor(SLATE_100); c.rect(0, 0, W, 12 * mm, stroke=0, fill=1)
    c.setFillColor(SLATE_600); c.setFont("Helvetica", 7)
    c.drawString(10 * mm, 6 * mm,
                 "EpiTrace / Mon Pass Sanitaire — Confidentiel INHP · Ne pas rediffuser sans autorisation MSHPCMU")
    c.drawString(10 * mm, 3 * mm,
                 f"Contact : inhp@veillesanitaire.com · Assistance : 143")
    c.setFont("Helvetica-Oblique", 7)
    generated = (meta.get("generated_at") or "")[:19].replace("T", " ")
    c.drawRightString(W - 10 * mm, 3 * mm,
                      f"Généré le {generated} · durée {meta.get('generation_ms', 0)} ms")
