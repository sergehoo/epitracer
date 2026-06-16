"""Services Health Pass : émission, QR + PDF tricolore CI,
fiche officielle INHP pré-remplie, vérification, révocation.
"""
from __future__ import annotations

from datetime import timedelta
from io import BytesIO

import qrcode
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.diseases.models import Disease
from apps.ebola.models import EbolaInvestigation
from apps.travelers.models import Traveler

from .branding import (
    CI_DARK, CI_GOLD, CI_GREEN, CI_ORANGE, CI_WHITE,
    HEADER_INHP, HEADER_MINISTRY, HEADER_MINISTRY_FULL,
    HEADER_MOTTO, HEADER_TOP, INHP_CONTACT,
    SLATE_500, SLATE_900,
    draw_ci_emblem, draw_ci_flag_band,
    get_armoirie_logo, get_inhp_logo, get_mshpcmu_logo,
)
from .crypto import is_expired, public_kid, sign_payload, verify_token
from .models import HealthPass, HealthPassStatus, PassBlacklistEntry, PassVerificationLog


def issue_pass(
    *,
    traveler: Traveler,
    disease: Disease,
    risk_level: str = "low",
    risk_score: int = 0,
    investigation_ref: str = "",
    ttl_days: int | None = None,
) -> HealthPass:
    ttl = ttl_days or settings.HEALTHPASS["DEFAULT_TTL_DAYS"]
    expires_at = timezone.now() + timedelta(days=ttl)

    hp = HealthPass.objects.create(
        traveler=traveler,
        disease=disease,
        investigation_ref=investigation_ref,
        risk_level=risk_level,
        risk_score=risk_score,
        expires_at=expires_at,
        signing_kid=public_kid(),
    )

    payload = {
        "iss": settings.HEALTHPASS["ISSUER"],
        "kid": hp.signing_kid,
        "pid": hp.pass_number,
        "tid": traveler.public_id,
        "name": f"{traveler.last_name} {traveler.first_name}",
        "dis": disease.code if disease else None,
        "rsk": risk_level,
        "scr": risk_score,
        "iat": hp.issued_at.isoformat(),
        "exp": expires_at.isoformat(),
    }
    token, signature = sign_payload(payload)
    hp.payload = payload
    hp.signature_b64 = signature

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10, border=2,
    )
    qr.add_data(token); qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    hp.qr_image.save(f"{hp.pass_number}.png", ContentFile(buf.getvalue()), save=False)

    pdf_bytes = render_pass_pdf(hp, token)
    hp.pdf_file.save(f"{hp.pass_number}.pdf", ContentFile(pdf_bytes), save=False)

    hp.save()
    return hp


def issue_pass_for_ebola_investigation(investigation: EbolaInvestigation) -> HealthPass:
    disease = Disease.objects.filter(code="EBOLA").first()
    return issue_pass(
        traveler=investigation.traveler,
        disease=disease,
        risk_level=investigation.risk_level,
        risk_score=investigation.risk_score,
        investigation_ref=investigation.case_number,
    )


# =========================================================================
#                        PDF DU PASS — couleurs CI
# =========================================================================
def render_pass_pdf(hp: HealthPass, token: str) -> bytes:
    """Pass sanitaire premium aux couleurs ivoiriennes (A5)."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A5)
    width, height = A5  # 148 x 210 mm

    # 1) Bandeau drapeau tricolore en haut
    draw_ci_flag_band(c, 0, height - 8 * mm, width, 8 * mm)

    # 2) Bandeau d'en-tête sombre + 3 logos officiels
    header_h = 38 * mm
    c.setFillColor(CI_DARK)
    c.rect(0, height - 8 * mm - header_h, width, header_h, fill=1, stroke=0)

    logo_size = 18 * mm
    logo_y = height - 8 * mm - header_h / 2 - logo_size / 2

    # Disposition officielle : MSHPCMU (gauche) · INHP (centre) · Armoirie (droite)
    cx_center = width / 2

    # Logo MSHPCMU à l'extrême gauche
    mshpcmu = get_mshpcmu_logo()
    if mshpcmu:
        c.drawImage(mshpcmu, 6 * mm, logo_y, logo_size, logo_size,
                    preserveAspectRatio=True, mask="auto")

    # Logo INHP au centre
    inhp = get_inhp_logo()
    if inhp:
        c.drawImage(inhp, cx_center - logo_size / 2, logo_y, logo_size, logo_size,
                    preserveAspectRatio=True, mask="auto")

    # Armoirie de la République à droite
    armoirie = get_armoirie_logo()
    if armoirie:
        c.drawImage(armoirie, width - 6 * mm - logo_size, logo_y,
                    logo_size, logo_size, preserveAspectRatio=True, mask="auto")
    else:
        draw_ci_emblem(c, width - 6 * mm - logo_size / 2,
                       logo_y + logo_size / 2, logo_size / 2)

    # Textes d'en-tête (sous les logos, centrés)
    text_top = logo_y - 1 * mm
    c.setFillColor(CI_WHITE)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(cx_center, text_top - 3.5 * mm, HEADER_TOP)
    c.setFont("Helvetica-Oblique", 6.5)
    c.drawCentredString(cx_center, text_top - 7 * mm, HEADER_MOTTO)
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(CI_GOLD)
    c.drawCentredString(cx_center, text_top - 10.5 * mm, f"{HEADER_MINISTRY} · INHP")

    # 3) Titre du pass
    title_y = height - 8 * mm - header_h - 12 * mm
    c.setFillColor(CI_DARK)
    c.setFont("Helvetica-Bold", 17)
    c.drawCentredString(width / 2, title_y, "PASS SANITAIRE NATIONAL")
    c.setFont("Helvetica", 8)
    c.setFillColor(SLATE_500)
    c.drawCentredString(width / 2, title_y - 5 * mm,
                        "Surveillance épidémiologique des voyageurs — Ebola (MVE)")

    # 4) Bloc d'informations à gauche
    card_top = title_y - 12 * mm
    info_x = 10 * mm

    def line(label: str, value: str, y: float, accent=False):
        c.setFont("Helvetica", 7)
        c.setFillColor(SLATE_500)
        c.drawString(info_x, y, label.upper())
        c.setFont("Helvetica-Bold", 11 if accent else 9.5)
        c.setFillColor(CI_ORANGE if accent else SLATE_900)
        c.drawString(info_x, y - 4.5 * mm, value or "—")

    y = card_top
    line("N° de pass", hp.pass_number, y, accent=True); y -= 11 * mm
    line("Voyageur", f"{hp.traveler.last_name.upper()} {hp.traveler.first_name}", y); y -= 9 * mm
    line("ID voyageur", hp.traveler.public_id, y); y -= 9 * mm
    line("Maladie suivie", hp.disease.name if hp.disease else "—", y); y -= 9 * mm

    # Bandeau "Suivi sanitaire actif" (remplace l'ancien bandeau de risque).
    # On retire l'affichage du niveau de risque + score sur le PDF pour ne
    # pas exposer cette info au voyageur ni à toute personne qui pourrait
    # avoir le PDF en main (vol, prêt, etc.). Le niveau de risque reste
    # interne au système (agents INHP) et ne figure plus sur les supports
    # qui circulent.
    c.setFillColor(CI_GREEN)
    c.roundRect(info_x, y - 7 * mm, 60 * mm, 8 * mm, 3, stroke=0, fill=1)
    c.setFillColor(CI_WHITE); c.setFont("Helvetica-Bold", 9)
    c.drawString(info_x + 3 * mm, y - 4.5 * mm, "ACCOMPAGNEMENT SANITAIRE — 21 JOURS")

    y -= 14 * mm
    line("Émis le", hp.issued_at.strftime("%d/%m/%Y %H:%M"), y); y -= 9 * mm
    line("Expire le", hp.expires_at.strftime("%d/%m/%Y %H:%M"), y); y -= 9 * mm
    line("Émetteur", settings.HEALTHPASS["ISSUER"], y)

    # 5) QR à droite avec cadre tricolore
    qr_size = 55 * mm
    qr_x = width - qr_size - 8 * mm
    qr_y = card_top - qr_size - 4 * mm
    c.setFillColor(CI_ORANGE); c.rect(qr_x - 2, qr_y + qr_size + 1, qr_size + 4, 1.5, stroke=0, fill=1)
    c.setFillColor(CI_WHITE);  c.rect(qr_x - 2, qr_y - 2.5, qr_size + 4, 1.5, stroke=0, fill=1)
    c.setFillColor(CI_GREEN);  c.rect(qr_x - 2, qr_y - 4, qr_size + 4, 1.5, stroke=0, fill=1)
    if hp.qr_image:
        c.drawImage(
            ImageReader(hp.qr_image.path), qr_x, qr_y, qr_size, qr_size,
            preserveAspectRatio=True, mask="auto",
        )
    c.setFillColor(SLATE_500); c.setFont("Helvetica-Oblique", 6)
    c.drawCentredString(qr_x + qr_size / 2, qr_y - 8,
                        "Vérification cryptographique Ed25519")

    # 6) Encadré "Informations utiles"
    box_y = 18 * mm
    box_h = 28 * mm
    c.setFillColor(colors.HexColor("#FFF7ED"))
    c.roundRect(8 * mm, box_y, width - 16 * mm, box_h, 4, stroke=0, fill=1)
    c.setFillColor(CI_DARK); c.setFont("Helvetica-Bold", 9)
    c.drawString(12 * mm, box_y + box_h - 6 * mm, "INFORMATIONS UTILES")
    c.setFont("Helvetica", 7.5); c.setFillColor(SLATE_900)
    tips = [
        "• Présentez ce pass aux équipes sanitaires aux points d'entrée.",
        "• Surveillance médicale de 21 jours conformément au protocole INHP.",
        "• En cas de symptôme : SAMU 185 · Allô Santé 143 · Secours 101.",
        "• Document signé numériquement — toute falsification est punie par la loi.",
    ]
    ty = box_y + box_h - 11 * mm
    for t in tips:
        c.drawString(12 * mm, ty, t); ty -= 4 * mm

    # 7) Footer
    c.setFillColor(SLATE_500); c.setFont("Helvetica-Oblique", 6)
    c.drawString(8 * mm, 10 * mm, INHP_CONTACT)
    c.setFont("Helvetica", 6)
    c.drawRightString(width - 8 * mm, 10 * mm, f"kid={hp.signing_kid}")
    # Bande tricolore de pied
    draw_ci_flag_band(c, 0, 0, width, 5 * mm)

    c.showPage(); c.save()
    return buf.getvalue()


# =========================================================================
#         FICHE OFFICIELLE INHP PRÉ-REMPLIE — PDF A4
# =========================================================================
def render_official_form_pdf(traveler: Traveler) -> bytes:
    """Reproduit la FICHE DE RENSEIGNEMENT PASSAGER officielle INHP avec
    les données saisies par le voyageur (7 sections + notice + urgences).
    """
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import (
        Image as RLImage, KeepTogether, Paragraph, SimpleDocTemplate,
        Spacer, Table, TableStyle,
    )

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=16 * mm, rightMargin=16 * mm,
        topMargin=12 * mm, bottomMargin=14 * mm,
        title="Fiche de renseignement passager - Ebola (INHP)",
        author="INHP - République de Côte d'Ivoire",
    )
    styles = getSampleStyleSheet()
    H_TITLE = ParagraphStyle("HTitle", parent=styles["Title"], fontName="Helvetica-Bold",
                             fontSize=14, textColor=CI_DARK, alignment=1, spaceAfter=2)
    H_SUB = ParagraphStyle("HSub", parent=styles["Normal"], fontSize=9,
                           textColor=SLATE_500, alignment=1)
    SECTION = ParagraphStyle("Section", parent=styles["Heading2"], fontName="Helvetica-Bold",
                             fontSize=10.5, textColor=CI_WHITE, leading=14,
                             backColor=CI_DARK, leftIndent=6, spaceBefore=10, spaceAfter=4)
    BODY = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=12)
    LABEL = ParagraphStyle("Label", parent=styles["Normal"], fontSize=8, textColor=SLATE_500)
    VALUE = ParagraphStyle("Value", parent=styles["Normal"], fontSize=9.5,
                           textColor=SLATE_900, fontName="Helvetica-Bold")
    SMALL = ParagraphStyle("Small", parent=styles["Normal"], fontSize=7.5, textColor=SLATE_500)

    story: list = []

    # ====================================================================
    # EN-TÊTE OFFICIEL — disposition à 3 colonnes équi-largeur
    #   ┌──────────────┬──────────────┬──────────────┐
    #   │   MSHPCMU    │     INHP     │   ARMOIRIE   │
    #   │ (ministère)  │  (institut)  │  (république)│
    #   └──────────────┴──────────────┴──────────────┘
    #   Sous l'en-tête : pavé légendes (MSHPCMU + INHP + devise),
    #   puis le titre du document SUR SA PROPRE LIGNE.
    # ====================================================================
    from .branding import LOGO_ARMOIRIE, LOGO_INHP, LOGO_MSHPCMU

    def _img(path, w=20 * mm, h=20 * mm):
        try:
            return RLImage(str(path), width=w, height=h, kind="proportional")
        except Exception:
            return Paragraph("&nbsp;", BODY)

    # Largeur utile de page (A4 - 2*16mm de marge = 178 mm)
    PAGE_W = 178 * mm
    LOGO_BOX = 22 * mm    # hauteur réservée pour chaque logo
    COL_W = PAGE_W / 3.0  # 3 colonnes équi-largeur

    H_LABEL = ParagraphStyle(
        "HLabel", parent=styles["Normal"], fontSize=7.5, leading=9,
        textColor=SLATE_500, alignment=1,  # centré
    )

    # Ligne 1 : les 3 logos sur la même rangée
    logos_row = Table(
        [[
            _img(LOGO_MSHPCMU, LOGO_BOX, LOGO_BOX),
            _img(LOGO_INHP, LOGO_BOX, LOGO_BOX),
            _img(LOGO_ARMOIRIE, LOGO_BOX, LOGO_BOX),
        ]],
        colWidths=[COL_W, COL_W, COL_W],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (0, -1), "LEFT"),    # MSHPCMU collé à gauche
            ("ALIGN", (1, 0), (1, -1), "CENTER"),  # INHP au centre
            ("ALIGN", (2, 0), (2, -1), "RIGHT"),   # Armoirie collée à droite
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )

    # Ligne 2 : libellés sous chaque logo (alignés avec leur colonne)
    labels_row = Table(
        [[
            Paragraph(f"<b>{HEADER_MINISTRY}</b><br/>"
                      f"<font size=6.5 color='#64748B'>{HEADER_MINISTRY_FULL}</font>", H_LABEL),
            Paragraph(f"<b>INHP</b><br/>"
                      f"<font size=6.5 color='#64748B'>Institut National d'Hygiène Publique</font>", H_LABEL),
            Paragraph(f"<b>RÉPUBLIQUE DE CÔTE D'IVOIRE</b><br/>"
                      f"<font size=6.5 color='#64748B'><i>{HEADER_MOTTO}</i></font>", H_LABEL),
        ]],
        colWidths=[COL_W, COL_W, COL_W],
        style=TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )

    # Assemblage en-tête : logos puis libellés, encadré ligne orange dessous.
    story.append(Table(
        [[logos_row], [labels_row]],
        colWidths=[PAGE_W],
        style=TableStyle([
            ("LINEBELOW", (0, -1), (-1, -1), 0.7, CI_ORANGE),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]),
    ))
    story.append(Spacer(1, 8))

    # ====================================================================
    # TITRE DU DOCUMENT — sur sa propre ligne, centré
    # ====================================================================
    story.append(Paragraph("SURVEILLANCE DE LA MALADIE À VIRUS ÉBOLA (MVE)", H_TITLE))
    story.append(Paragraph("FICHE DE RENSEIGNEMENT PASSAGER", H_TITLE))
    story.append(Paragraph(
        "(À remplir obligatoirement par tout passager à l'arrivée sur le territoire national)",
        H_SUB,
    ))
    story.append(Spacer(1, 3))
    story.append(Paragraph(
        f"<i>Document généré le {timezone.now().strftime('%d/%m/%Y à %H:%M')} — "
        f"identifiant voyageur <b>{traveler.public_id}</b></i>", SMALL,
    ))
    story.append(Spacer(1, 10))

    def kv_table(rows, col1=58 * mm, col2=120 * mm):
        wrapped = []
        for label, value in rows:
            wrapped.append([
                Paragraph(label, LABEL),
                Paragraph(str(value) if value not in (None, "", []) else "—", VALUE),
            ])
        t = Table(wrapped, colWidths=[col1, col2])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    # Section 1
    story.append(Paragraph("1. Informations sur le voyage", SECTION))
    story.append(kv_table([
        ["Date d'arrivée", traveler.arrival_date.strftime("%d/%m/%Y") if traveler.arrival_date else ""],
        ["N° de vol / moyen de transport", traveler.flight_or_voyage_number],
        ["N° de siège", traveler.seat_number],
        ["Point d'entrée", traveler.entry_point.name if traveler.entry_point_id else ""],
    ]))

    # Section 2
    story.append(Paragraph("2. Identité et contacts du passager", SECTION))
    story.append(kv_table([
        ["Nom de famille", traveler.last_name],
        ["Prénoms", traveler.first_name],
        ["Âge", f"{traveler.age} {('Ans' if traveler.age_unit == 'years' else 'Mois')}"
                if traveler.age else ""],
        ["Sexe", {"M": "Masculin", "F": "Féminin"}.get(traveler.gender, "")],
        ["Profession", traveler.profession],
        ["N° Passeport", traveler.id_document_number],
        ["Téléphone portable", traveler.phone_mobile],
        ["Adresse e-mail", traveler.email],
        ["Adresse postale", traveler.postal_address],
        ["Pièce jointe", "Document de voyage joint" if traveler.passport_document
                          else "Aucun document joint"],
    ]))

    # Section 3 — historique
    story.append(Paragraph(
        "3. Historique des déplacements (3 dernières semaines / 21 derniers jours)",
        SECTION,
    ))
    history = list(traveler.travel_history.select_related("country").all())
    if not history:
        story.append(Paragraph("<i>Aucun déplacement déclaré.</i>", BODY))
    else:
        rows = [[
            Paragraph("<b>Rôle</b>", LABEL),
            Paragraph("<b>Pays</b>", LABEL),
            Paragraph("<b>Ville</b>", LABEL),
            Paragraph("<b>Hôtel / Chambre</b>", LABEL),
            Paragraph("<b>Durée / Période</b>", LABEL),
        ]]
        for h in history:
            role = {"origin": "Provenance", "transit": "Transit", "visited": "Visité"}.get(
                h.role, h.role)
            period = h.duration_text or (
                f"{h.arrival_date} → {h.departure_date}"
                if h.arrival_date or h.departure_date else ""
            )
            hotel = h.hotel + (f" / {h.room_number}" if h.room_number else "")
            rows.append([
                Paragraph(role, BODY),
                Paragraph(h.country.name if h.country_id else "", BODY),
                Paragraph(h.city or "", BODY),
                Paragraph(hotel or "—", BODY),
                Paragraph(period or "—", BODY),
            ])
        t = Table(rows, colWidths=[22 * mm, 38 * mm, 30 * mm, 45 * mm, 43 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF7ED")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)

    # Section 4 — confinement
    story.append(Paragraph("4. Adresse de résidence et confinement en Côte d'Ivoire", SECTION))
    story.append(kv_table([
        ["Ville", traveler.confinement_city],
        ["Commune", traveler.confinement_commune],
        ["Quartier", traveler.confinement_neighborhood],
        ["N° de rue", traveler.confinement_street_number],
        ["N° de lot", traveler.confinement_lot],
        ["Hôtel / lieu d'hébergement", traveler.confinement_hotel],
        ["N° de chambre", traveler.confinement_room_number],
        ["Téléphone d'urgence (CI)", traveler.emergency_phone_ci],
    ]))

    inv = traveler.ebola_investigations.order_by("-created_at").first()

    # Section 5 — exposition
    story.append(Paragraph(
        "5. Évaluation Épidémiologique du Risque (21 derniers jours)", SECTION))
    exp = getattr(inv, "exposure", None) if inv else None

    def yn(v):
        if v is True:
            return "<font color='#B91C1C'><b>OUI</b></font>"
        if v is False:
            return "<font color='#047857'><b>NON</b></font>"
        return "—"

    if exp is None:
        story.append(Paragraph("<i>Section non renseignée.</i>", BODY))
    else:
        ex_rows = [
            ["Avez-vous séjourné ou transité par une zone touchée par l'épidémie d'Ebola ?",
             yn(exp.visited_ebola_zone)],
        ]
        if exp.visited_ebola_zone and exp.visited_ebola_zone_details:
            ex_rows.append(["Précision (ville / région et pays)",
                            exp.visited_ebola_zone_details])
        ex_rows += [
            ["Avez-vous été en contact avec une personne malade ou suspectée d'avoir Ebola ?",
             yn(exp.contact_with_case)],
            ["Avez-vous assisté à des funérailles ou touché une dépouille humaine ?",
             yn(exp.attended_funeral_or_touched_corpse)],
            ["Avez-vous fréquenté un établissement de soins traitant des patients Ebola ?",
             yn(exp.visited_ebola_healthcare_facility)],
        ]
        rows = [[Paragraph(label, BODY), Paragraph(value, BODY)] for label, value in ex_rows]
        t = Table(rows, colWidths=[125 * mm, 53 * mm])
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)

    # Section 6 — symptômes
    story.append(Paragraph(
        "6. État de santé (Symptômes ressentis au cours des 48 dernières heures)",
        SECTION,
    ))
    sym = inv.symptom_reports.order_by("-reported_at").first() if inv else None
    SYMPT = [
        ("Fièvre (≥ 38°C) ou sensation de forte chaleur", "fever"),
        ("Fatigue intense, faiblesse généralisée inexpliquée", "intense_fatigue"),
        ("Douleurs musculaires, articulaires ou courbatures", "muscle_joint_pain"),
        ("Maux de tête intenses (Céphalées)", "severe_headache"),
        ("Maux de gorge ou douleurs abdominales (estomac)", "sore_throat_or_abdominal"),
        ("Diarrhée, nausées ou vomissements fréquents", "diarrhea_nausea_vomiting"),
        ("Saignements inexpliqués (nez, gencives, peau, urines, selles)",
         "unexplained_bleeding"),
    ]
    rows = [[
        Paragraph("<b>Symptômes observés</b>", LABEL),
        Paragraph("<b>OUI</b>", LABEL),
        Paragraph("<b>NON</b>", LABEL),
    ]]
    for label, attr in SYMPT:
        val = getattr(sym, attr, None) if sym else None
        rows.append([
            Paragraph(label, BODY),
            Paragraph("☒" if val is True else "☐", BODY),
            Paragraph("☒" if val is False else "☐", BODY),
        ])
    t = Table(rows, colWidths=[140 * mm, 20 * mm, 20 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF7ED")),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t)
    if sym and sym.temperature_celsius:
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            f"Température mesurée : <b>{sym.temperature_celsius} °C</b>", BODY,
        ))

    # Section 7 — déclaration + signature manuscrite
    story.append(Paragraph("7. Déclaration sur l'honneur", SECTION))
    decl = getattr(inv, "declaration", None) if inv else None
    story.append(Paragraph(
        "« Je certifie sur l'honneur l'exactitude des renseignements portés sur cette fiche. »",
        BODY,
    ))
    story.append(Spacer(1, 6))
    if decl:
        story.append(kv_table([
            ["Fait à", decl.signed_place or ""],
            ["Le", decl.declared_at.strftime("%d/%m/%Y") if decl.declared_at else ""],
            ["Signataire", decl.declarant_full_name or traveler.full_name],
        ]))

        # --- Cadre signature ---
        from reportlab.platypus import Image
        signature_file = None
        try:
            if decl.signature and decl.signature.path:
                signature_file = decl.signature.path
            elif traveler.consent_signature and traveler.consent_signature.path:
                signature_file = traveler.consent_signature.path
        except (ValueError, FileNotFoundError):
            signature_file = None

        if signature_file:
            try:
                sig_img = Image(signature_file, width=70 * mm, height=22 * mm, kind="proportional")
            except Exception:
                sig_img = Paragraph("<i>(signature non lisible)</i>", BODY)
        else:
            sig_img = Paragraph(
                "<i>Signature électronique non capturée. Voir cachet INHP.</i>", BODY,
            )

        signature_block = Table(
            [
                [Paragraph("<b>Signature du passager</b>", LABEL),
                 Paragraph(f"<b>Empreinte</b> : <font face='Courier' size=7>"
                           f"{(decl.signature_hash or '—')[:24]}…</font>"
                           if decl.signature_hash else
                           "<i>Empreinte non disponible</i>", SMALL)],
                [sig_img, Paragraph(
                    f"<b>Déclarant :</b> {decl.declarant_full_name or traveler.full_name}<br/>"
                    f"<b>Fait à :</b> {decl.signed_place or '—'}<br/>"
                    f"<b>Le :</b> {decl.declared_at.strftime('%d/%m/%Y') if decl.declared_at else '—'}<br/>"
                    f"<b>Identifiant :</b> {traveler.public_id}",
                    BODY,
                )],
            ],
            colWidths=[90 * mm, 88 * mm],
        )
        signature_block.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, CI_DARK),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFFBEB")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 1), (0, 1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(Spacer(1, 6))
        story.append(signature_block)

    # Notice INHP
    story.append(Spacer(1, 10))
    story.append(Paragraph("NOTICE SANITAIRE INDIVIDUELLE AUX VOYAGEURS", H_TITLE))
    story.append(Paragraph("Surveillance de la Maladie à Virus Ébola (MVE)", H_SUB))
    story.append(Spacer(1, 4))
    NOTICE = [
        ("Qu'est-ce que la Maladie à Virus Ébola ?",
         "La maladie à virus Ébola (MVE) est une infection d'une extrême gravité provoquée "
         "par le virus Ébola. Elle se caractérise par l'apparition brutale d'une forte fièvre, "
         "d'une fatigue généralisée intense, de douleurs musculaires, articulaires et de maux de tête. "
         "Ces symptômes initiaux sont rapidement suivis de maux de gorge, de vomissements, de diarrhée "
         "profuse, d'éruptions cutanées, d'insuffisance rénale ou hépatique et, dans certains cas graves, "
         "d'hémorragies internes et externes spontanées. La durée d'incubation maximale de la maladie "
         "est de 21 jours."),
        ("Comment se transmet le virus Ébola ?",
         "Le réservoir naturel du virus est la chauve-souris frugivore. La transmission s'effectue selon "
         "deux axes majeurs : <b>de l'animal à l'homme</b> (contact direct avec sang, fluides corporels, "
         "organes ou sécrétions d'animaux sauvages infectés trouvés malades ou morts en forêt tropicale "
         "— singes, chauves-souris, antilopes de forêt) ; <b>de personne à personne</b> (contact étroit "
         "et direct — peau lésée ou muqueuses — avec sang, fluides biologiques d'une personne malade ou "
         "décédée). Le virus se transmet aussi par contact avec matériel médical ou objets personnels contaminés."),
        ("Mesures de prévention obligatoires",
         "<b>Hygiène des mains</b> : se laver fréquemment à l'eau et au savon, ou solution hydroalcoolique. "
         "<b>Distanciation sanitaire</b> : éviter tout contact direct ou non protégé avec toute personne suspecte "
         "ou présentant un état fébrile inexpliqué. <b>Sécurité funéraire</b> : ne pas participer aux rites "
         "de lavage mortuaire traditionnel ni manipuler des dépouilles inconnues — alerter les services de "
         "santé. <b>Interdiction alimentaire</b> : s'abstenir formellement de manipuler ou consommer de la "
         "viande de brousse."),
        ("Dispositif de suivi pendant votre séjour",
         "Conformément aux directives de santé publique, les voyageurs arrivant de zones sous surveillance "
         "font l'objet d'un suivi sanitaire de <b>21 jours</b> par l'Institut National d'Hygiène Publique (INHP)."),
    ]
    for title, body in NOTICE:
        story.append(Paragraph(f"<b><font color='#064E3B'>{title}</font></b>", BODY))
        story.append(Paragraph(body, BODY))
        story.append(Spacer(1, 4))

    # Bandeau urgence (KeepTogether)
    urgence_table = Table(
        [[
            Paragraph("<b>SAMU National</b><br/><font size=14 color='#F77F00'><b>185</b></font>", BODY),
            Paragraph("<b>Allô Santé</b><br/><font size=14 color='#F77F00'><b>143</b></font>", BODY),
            Paragraph("<b>Secours / Police</b><br/><font size=14 color='#F77F00'><b>101</b></font>", BODY),
        ]],
        colWidths=[60 * mm, 60 * mm, 60 * mm],
    )
    urgence_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CI_DARK),
        ("TEXTCOLOR", (0, 0), (-1, -1), CI_WHITE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 1, CI_ORANGE),
        ("GRID", (0, 0), (-1, -1), 0.5, CI_ORANGE),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(KeepTogether([
        Spacer(1, 6),
        Paragraph(
            "<font color='#B91C1C'><b>En cas de symptômes évocateurs (fièvre, maux de tête, "
            "saignement)</b></font> : rendez-vous immédiatement dans le centre de santé le plus proche.",
            BODY,
        ),
        Spacer(1, 4),
        urgence_table,
    ]))

    def _draw_page_chrome(c, _doc):
        w, h = A4
        draw_ci_flag_band(c, 0, h - 4 * mm, w, 4 * mm)
        draw_ci_flag_band(c, 0, 0, w, 4 * mm)
        c.setFont("Helvetica", 7); c.setFillColor(SLATE_500)
        c.drawString(16 * mm, 7 * mm, f"INHP · Fiche officielle MVE · {traveler.public_id}")
        c.drawRightString(A4[0] - 16 * mm, 7 * mm,
                          f"Page {c.getPageNumber()} · Généré le {timezone.now().strftime('%d/%m/%Y')}")

    doc.build(story, onFirstPage=_draw_page_chrome, onLaterPages=_draw_page_chrome)
    return buf.getvalue()


# =========================================================================
#               Révocation / vérification (inchangées)
# =========================================================================
def revoke_pass(hp: HealthPass, *, user=None, reason: str = "") -> HealthPass:
    hp.status = HealthPassStatus.REVOKED
    hp.revoked_at = timezone.now()
    hp.revoked_by = user
    hp.revocation_reason = reason[:200]
    hp.save(update_fields=["status", "revoked_at", "revoked_by", "revocation_reason"])
    return hp


def verify_pass(token: str, *, entry_point=None, user=None, online: bool = True) -> dict:
    result: dict = {"is_valid": False, "reason": "", "payload": None, "online_checked": online}
    try:
        payload = verify_token(token)
    except Exception as exc:
        _log_verification(None, "", False, "bad_signature", entry_point, user)
        return {**result, "reason": f"Signature invalide : {exc}"}
    result["payload"] = payload
    if is_expired(payload):
        _log_verification(None, payload.get("pid", ""), False, "expired", entry_point, user)
        return {**result, "reason": "Pass expiré (crypto)."}
    if not online:
        _log_verification(None, payload.get("pid", ""), True, "offline_only", entry_point, user)
        return {**result, "is_valid": True}
    pass_number = payload.get("pid", "")
    hp = HealthPass.objects.filter(pass_number=pass_number).first()
    if PassBlacklistEntry.objects.filter(pass_number=pass_number).exists():
        _log_verification(hp, pass_number, False, "blacklisted", entry_point, user)
        return {**result, "reason": "Pass en liste noire."}
    if hp is None:
        _log_verification(None, pass_number, False, "unknown", entry_point, user)
        return {**result, "reason": "Pass inconnu côté serveur."}
    # Construit le bloc d'enrichissement métier (niveau de risque, suivi en
    # cours, statut voyageur). Toujours renvoyé même si le pass est invalide
    # pour qu'un agent voie « pourquoi » + « qui ».
    enrichment = _build_pass_enrichment(hp)
    if hp.status != HealthPassStatus.ACTIVE:
        _log_verification(hp, pass_number, False, f"status_{hp.status}", entry_point, user)
        return {**result, "reason": f"Pass non actif ({hp.status}).", **enrichment}
    if not hp.is_valid:
        _log_verification(hp, pass_number, False, "expired_or_inactive", entry_point, user)
        return {**result, "reason": "Pass expiré côté serveur.", **enrichment}
    _log_verification(hp, pass_number, True, "ok", entry_point, user)
    return {**result, "is_valid": True, **enrichment}


def _build_pass_enrichment(hp) -> dict:
    """Construit le bloc d'infos métier renvoyé avec la vérification :
    niveau de risque, statut voyageur, suivi en cours, jours restants.
    """
    if hp is None:
        return {}
    out: dict = {
        "risk_level": (hp.risk_level or "low").lower(),
        "risk_score": float(hp.risk_score or 0),
    }
    # Suivi 21j (Companion) si présent
    try:
        from apps.companion.models import TravelerFollowup

        followup = TravelerFollowup.objects.filter(
            traveler=hp.traveler, active=True,
        ).order_by("-created_at").first()
        if followup:
            from django.utils import timezone

            days_done = (timezone.now().date() - followup.started_at.date()).days
            out["followup"] = {
                "active": True,
                "day": max(0, days_done),
                "total_days": followup.total_days or 21,
                "started_at": followup.started_at.isoformat(),
            }
    except Exception:
        pass
    # Statut du voyageur (Ebola investigation par exemple)
    try:
        from apps.ebola.models import EbolaInvestigation

        last = EbolaInvestigation.objects.filter(
            traveler=hp.traveler,
        ).order_by("-created_at").first()
        if last:
            out["traveler_status"] = {
                "case_status": last.status,
                "risk_level": last.risk_level,
                "last_update": last.updated_at.isoformat()
                    if getattr(last, "updated_at", None) else None,
            }
    except Exception:
        pass
    return out


def _log_verification(hp, pass_number, ok, reason, entry_point, user):
    PassVerificationLog.objects.create(
        pass_obj=hp, pass_number=pass_number, is_valid=ok, reason=reason,
        entry_point=entry_point,
        verified_by=user if user and getattr(user, "is_authenticated", False) else None,
    )
