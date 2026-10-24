"""Helpers de génération CSV / PDF pour le centre de rapports.

Conventions:
    * Toutes les fonctions retournent un `HttpResponse` prêt à être streamé.
    * Les rapports sont nommés avec un timestamp ISO court pour éviter les
      collisions côté téléchargement utilisateur.
    * Les PDF sont au format A4 paysage avec un en-tête CI vert/orange.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.http import HttpResponse
from django.utils import timezone

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover
    REPORTLAB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Couleurs CI
# ---------------------------------------------------------------------------
CI_GREEN = colors.HexColor("#009E60") if REPORTLAB_AVAILABLE else None
CI_ORANGE = colors.HexColor("#FF7F00") if REPORTLAB_AVAILABLE else None
CI_DARK = colors.HexColor("#0B1820") if REPORTLAB_AVAILABLE else None
CI_LIGHT_GREEN = colors.HexColor("#E6F4EE") if REPORTLAB_AVAILABLE else None


# ---------------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------------
def csv_response(filename: str, headers: Sequence[str], rows: Iterable[Sequence]) -> HttpResponse:
    """Construit une réponse HTTP CSV (UTF-8 BOM pour ouverture Excel native FR)."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    # BOM UTF-8 → Excel détecte automatiquement l'encodage et les accents
    response.write("﻿")
    writer = csv.writer(response, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_csv_cell(c) for c in row])
    return response


def _csv_cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Oui" if value else "Non"
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


# ---------------------------------------------------------------------------
# Excel (XLSX)
# ---------------------------------------------------------------------------
XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def xlsx_response(
    filename: str,
    title: str,
    headers: Sequence[str],
    rows: Iterable[Sequence],
    *,
    summary: Sequence[tuple[str, str]] | None = None,
) -> HttpResponse:
    """Classeur Excel : une feuille de données (mêmes valeurs que le CSV) + synthèse."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Données"
    ws.append(list(headers))
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="009E60")
    for row in rows:
        ws.append([_xlsx_cell(c) for c in row])
        for cell in ws[ws.max_row]:
            # Une chaîne commençant par « = » serait interprétée comme formule.
            if isinstance(cell.value, str) and cell.value.startswith("="):
                cell.data_type = "s"
            elif isinstance(cell.value, datetime):
                cell.number_format = "DD/MM/YYYY HH:MM"
            elif isinstance(cell.value, date):
                cell.number_format = "DD/MM/YYYY"
    ws.freeze_panes = "A2"
    for idx, header in enumerate(headers, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = min(max(len(str(header)) + 2, 12), 40)

    meta = wb.create_sheet("Synthèse")
    meta.append([title])
    meta.append(["Généré le", timezone.localtime().strftime("%d/%m/%Y %H:%M")])
    for label, value in summary or []:
        meta.append([label, value])

    buf = io.BytesIO()
    wb.save(buf)
    response = HttpResponse(buf.getvalue(), content_type=XLSX_CONTENT_TYPE)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _xlsx_cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Oui" if value else "Non"
    if isinstance(value, datetime):
        # Excel ne gère pas les fuseaux : heure locale, sans tzinfo.
        return timezone.localtime(value).replace(tzinfo=None) if timezone.is_aware(value) else value
    if isinstance(value, str | int | float | Decimal | date):
        return value
    # Objets métier (ex. pays de nationalité) : même texte que dans le CSV.
    return str(value)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
# Au-delà de ce nombre de colonnes, les cellules passent à la ligne (police
# réduite) pour tenir dans la largeur A4 paysage au lieu de déborder.
PDF_WRAP_COLUMNS = 12


def pdf_response(
    filename: str,
    title: str,
    subtitle: str | None,
    headers: Sequence[str],
    rows: Iterable[Sequence],
    *,
    summary: Sequence[tuple[str, str]] | None = None,
    page_size=None,
) -> HttpResponse:
    """Génère un PDF tabulaire A4 paysage avec en-tête CI.

    Args:
        summary: liste optionnelle de (label, valeur) affichée en encart KPI
                 sous l'en-tête.
    """
    if not REPORTLAB_AVAILABLE:
        return HttpResponse("reportlab non disponible côté serveur.", status=500)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size or landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=12 * mm,
        title=title,
        author="EpiTrace",
    )

    elements = []
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle(
        "h1",
        parent=styles["Heading1"],
        textColor=CI_DARK,
        fontSize=18,
        spaceAfter=2 * mm,
    )
    h2 = ParagraphStyle(
        "h2",
        parent=styles["Normal"],
        textColor=colors.HexColor("#475569"),
        fontSize=10,
        spaceAfter=4 * mm,
    )

    elements.append(Paragraph(f"<b>{title}</b>", h1))
    sub_line = subtitle or ""
    sub_line += (
        f"  •  Généré le {timezone.localtime().strftime('%d/%m/%Y à %H:%M')}"
        f"  •  EpiTrace — MSHPCMU / INHP"
    )
    elements.append(Paragraph(sub_line, h2))

    # Encart KPI (synthèse)
    if summary:
        kpi_data = [[Paragraph(f"<b>{lbl}</b>", styles["Normal"]), val] for lbl, val in summary]
        kpi_table = Table(kpi_data, colWidths=[60 * mm, None], hAlign="LEFT")
        kpi_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), CI_LIGHT_GREEN),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        elements.append(kpi_table)
        elements.append(Spacer(1, 4 * mm))

    # Tableau principal
    wide = len(headers) > PDF_WRAP_COLUMNS
    font_size = 6 if wide else 8
    cell_style = ParagraphStyle(
        "cell",
        parent=styles["Normal"],
        fontSize=font_size,
        leading=font_size + 1.5,
    )
    head_style = ParagraphStyle("head", parent=cell_style, textColor=colors.white)
    if wide:
        table_data = [[Paragraph(f"<b>{_escape(h)}</b>", head_style) for h in headers]]
        for row in rows:
            table_data.append([Paragraph(_escape(_pdf_cell(c)), cell_style) for c in row])
        col_w = (doc.width / len(headers)) if headers else None
        table = Table(table_data, repeatRows=1, colWidths=[col_w] * len(headers))
    else:
        table_data = [[Paragraph(f"<b>{h}</b>", styles["Normal"]) for h in headers]]
        for row in rows:
            table_data.append([_pdf_cell(c) for c in row])
        table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), CI_GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), font_size),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("LINEBELOW", (0, 0), (-1, 0), 1, CI_DARK),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("INNERGRID", (0, 1), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    elements.append(table)

    # Footer texte (rendu en bas de chaque page via onPage)
    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#94A3B8"))
        canvas.drawString(
            12 * mm,
            8 * mm,
            "EpiTrace — Système national de veille épidémiologique • "
            "Confidentiel — usage administratif uniquement",
        )
        canvas.drawRightString(
            doc.pagesize[0] - 12 * mm,
            8 * mm,
            f"Page {doc.page}",
        )
        canvas.restoreState()

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    pdf = buf.getvalue()
    buf.close()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _escape(text: str) -> str:
    """Échappe le texte pour un Paragraph reportlab (mini-HTML)."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _pdf_cell(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Oui" if value else "Non"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    s = str(value)
    # Truncate très longs textes pour ne pas faire exploser les colonnes
    if len(s) > 80:
        s = s[:77] + "..."
    return s


# ---------------------------------------------------------------------------
# Helpers de parsing de paramètres de requête
# ---------------------------------------------------------------------------
def parse_date(value: str | None) -> date | None:
    """Accepte YYYY-MM-DD ; retourne None si absent/invalide."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def default_period() -> tuple[date, date]:
    """Période par défaut : 30 derniers jours (inclus aujourd'hui)."""
    today = timezone.localdate()
    return today - timedelta(days=30), today


def safe_getattr(obj, *names, default=""):
    """Renvoie le premier attribut trouvé non-vide parmi `names`."""
    for n in names:
        v = getattr(obj, n, None)
        if v is not None and v != "":
            return v
    return default
