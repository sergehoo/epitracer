"""Génération PDF Phase 9E — Documents médicaux INHP.

Trois fonctions principales :
  - `render_followup_individual_sheet(case)` — fiche de suivi individuelle
    complète pour dossier patient INHP (DailyCheck, symptômes, prélèvements,
    analyses, classification + historique).
  - `render_sample_collection_report(sample)` — rapport de prélèvement
    accompagnant l'échantillon vers le labo (anonymisation light + QR code).
  - `render_medical_orientation_form(case, agent)` — fiche d'orientation
    médicale pour adresser un cas à un centre de santé.

Toutes les fonctions partagent les helpers :
  - `_draw_inhp_header(c, width, height, title, subtitle)` — bandeau MSHPCMU
    / INHP / Armoiries + drapeau tricolore.
  - `_draw_inhp_footer(c, width, ref)` — pied de page avec mention
    confidentialité loi 2013-450.

Sécurité :
  - Aucun PII en clair dans les noms de fichiers.
  - Le numéro de passeport est tronqué (4 derniers caractères) dans le
    rapport de prélèvement (anonymisation labo).
  - Tous les PDFs sont destinés à être stockés sous MEDIA_ROOT/medical/...
    qui est servi en privé (auth requise côté Django).
"""
from __future__ import annotations

import io
import logging
from datetime import date, datetime
from typing import Optional

from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas

from apps.health_pass.branding import (
    CI_DARK,
    CI_GOLD,
    CI_GREEN,
    CI_ORANGE,
    CI_WHITE,
    HEADER_INHP,
    HEADER_MINISTRY,
    HEADER_MOTTO,
    HEADER_TOP,
    SLATE_500,
    SLATE_900,
    draw_ci_emblem,
    draw_ci_flag_band,
    get_armoirie_logo,
    get_inhp_logo,
    get_mshpcmu_logo,
)

from apps.quarantine.models import DailyCheck, QuarantineRecord

from .models import (
    CaseClassification,
    LabAnalysis,
    MedicalSample,
    MedicalSymptomReport,
)

logger = logging.getLogger("epidemitracker.medical.services_pdf")


# ===========================================================================
# Helpers visuels réutilisables (header / footer / palette)
# ===========================================================================


def _draw_inhp_header(
    c: rl_canvas.Canvas,
    width: float,
    height: float,
    *,
    title: str,
    subtitle: str = "",
    flag_band: bool = True,
) -> float:
    """Trace le bandeau officiel CI (MSHPCMU/INHP/Armoirie) en haut de page.

    Retourne la position Y du bas du bandeau (utile pour positionner la
    suite du contenu). Réutilisable sur toutes les pages.
    """
    # 1) Drapeau tricolore (orange / blanc / vert) en très haut
    if flag_band:
        draw_ci_flag_band(c, 0, height - 6 * mm, width, 6 * mm)
    band_top = height - (6 * mm if flag_band else 0)

    # 2) Bandeau sombre avec logos
    header_h = 30 * mm
    c.setFillColor(CI_DARK)
    c.rect(0, band_top - header_h, width, header_h, fill=1, stroke=0)

    logo_size = 16 * mm
    logo_y = band_top - header_h / 2 - logo_size / 2
    cx_center = width / 2

    # MSHPCMU à gauche
    mshpcmu = get_mshpcmu_logo()
    if mshpcmu:
        c.drawImage(
            mshpcmu, 8 * mm, logo_y, logo_size, logo_size,
            preserveAspectRatio=True, mask="auto",
        )

    # INHP au centre
    inhp = get_inhp_logo()
    if inhp:
        c.drawImage(
            inhp, cx_center - logo_size / 2, logo_y, logo_size, logo_size,
            preserveAspectRatio=True, mask="auto",
        )

    # Armoirie à droite
    armoirie = get_armoirie_logo()
    if armoirie:
        c.drawImage(
            armoirie, width - 8 * mm - logo_size, logo_y,
            logo_size, logo_size, preserveAspectRatio=True, mask="auto",
        )
    else:
        draw_ci_emblem(
            c, width - 8 * mm - logo_size / 2,
            logo_y + logo_size / 2, logo_size / 2,
        )

    # Textes officiels sous les logos (centrés sous la zone)
    text_y = band_top - header_h + 5 * mm
    c.setFillColor(CI_WHITE)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(cx_center, text_y + 4 * mm, HEADER_TOP)
    c.setFont("Helvetica-Oblique", 6)
    c.drawCentredString(cx_center, text_y + 1 * mm, HEADER_MOTTO)
    c.setFillColor(CI_GOLD)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString(cx_center, text_y - 2 * mm, f"{HEADER_MINISTRY} . {HEADER_INHP}")

    bottom_y = band_top - header_h

    # 3) Titre du document
    title_y = bottom_y - 10 * mm
    c.setFillColor(CI_DARK)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, title_y, title)

    if subtitle:
        c.setFillColor(SLATE_500)
        c.setFont("Helvetica", 9)
        c.drawCentredString(width / 2, title_y - 5 * mm, subtitle)
        return title_y - 12 * mm

    return title_y - 8 * mm


def _draw_inhp_footer(
    c: rl_canvas.Canvas,
    width: float,
    *,
    ref: str = "",
    issued_at: Optional[datetime] = None,
) -> None:
    """Pied de page commun : mention confidentialité + signature INHP."""
    issued_at = issued_at or timezone.now()

    # Mention confidentialité — Loi ivoirienne 2013-450 protection des données
    c.setFillColor(colors.HexColor("#94A3B8"))
    c.setFont("Helvetica-Oblique", 7)
    c.drawCentredString(
        width / 2, 14 * mm,
        "Document confidentiel - Loi n. 2013-450 du 19 juin 2013 sur la "
        "protection des donnees a caractere personnel.",
    )

    # Bandeau sombre tout en bas
    c.setFillColor(CI_DARK)
    c.rect(0, 0, width, 10 * mm, fill=1, stroke=0)
    c.setFillColor(CI_WHITE)
    c.setFont("Helvetica", 7)
    left = f"Genere le : {issued_at.strftime('%d/%m/%Y a %H:%M')}"
    c.drawString(8 * mm, 4 * mm, left)
    if ref:
        c.drawCentredString(width / 2, 4 * mm, f"Ref : {ref}")
    c.drawRightString(
        width - 8 * mm, 4 * mm,
        "EpiTrace . INHP Cote d'Ivoire . Signature electronique",
    )


def _section_title(c: rl_canvas.Canvas, x: float, y: float, text: str) -> None:
    """Trace un sous-titre de section (bandeau couleur)."""
    c.setFillColor(CI_GREEN)
    c.rect(x, y - 1.5 * mm, 4 * mm, 4 * mm, fill=1, stroke=0)
    c.setFillColor(CI_DARK)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x + 6 * mm, y, text)


def _kv(c: rl_canvas.Canvas, x: float, y: float, label: str, value: str,
        label_w: float = 35 * mm) -> None:
    """Trace une paire label / valeur sur une ligne."""
    c.setFillColor(SLATE_500)
    c.setFont("Helvetica", 8)
    c.drawString(x, y, label)
    c.setFillColor(SLATE_900)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + label_w, y, value or "-")


def _new_page_if_needed(c: rl_canvas.Canvas, y: float, width: float, height: float,
                       threshold: float = 24 * mm) -> float:
    """Si on est trop bas dans la page, en ouvre une nouvelle et redessine
    un petit header. Retourne la nouvelle position Y de travail."""
    if y > threshold:
        return y
    _draw_inhp_footer(c, width)
    c.showPage()
    new_y = _draw_inhp_header(
        c, width, height,
        title="(suite)", subtitle="",
    )
    return new_y


def _safe(value) -> str:
    if value is None:
        return "-"
    s = str(value).strip()
    return s if s else "-"


def _fmt_date(d) -> str:
    if not d:
        return "-"
    try:
        if isinstance(d, datetime):
            return d.strftime("%d/%m/%Y %H:%M")
        if isinstance(d, date):
            return d.strftime("%d/%m/%Y")
        return str(d)
    except Exception:
        return "-"


def _mask_passport(num: str | None) -> str:
    """Conserve uniquement les 4 derniers caractères du passeport."""
    if not num:
        return "-"
    s = str(num).strip()
    if len(s) <= 4:
        return "****"
    return f"****{s[-4:]}"


def _compute_age_years(traveler) -> str:
    if getattr(traveler, "age", None):
        return f"{traveler.age} {getattr(traveler, 'age_unit', 'ans') or 'ans'}"
    dob = getattr(traveler, "date_of_birth", None)
    if not dob:
        return "-"
    today = date.today()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return f"{years} ans"


# ===========================================================================
# 1) Fiche de suivi individuelle complète
# ===========================================================================


def render_followup_individual_sheet(case: QuarantineRecord) -> bytes:
    """Fiche de suivi individuelle — dossier patient INHP (multi-pages A4).

    Sections :
      1. Identité voyageur
      2. Voyage (vol, siège, point d'entrée, date arrivée)
      3. État du suivi (maladie, jour actuel, durée, statut)
      4. Classification actuelle + historique
      5. Check-ins quotidiens (DailyCheck J1-J21)
      6. Symptômes déclarés (MedicalSymptomReport)
      7. Prélèvements (MedicalSample)
      8. Analyses labo (LabAnalysis)
    """
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    traveler = case.traveler
    disease = case.disease

    y = _draw_inhp_header(
        c, width, height,
        title="FICHE DE SUIVI SANITAIRE INDIVIDUELLE",
        subtitle="Programme national de surveillance epidemiologique des voyageurs",
    )

    # --- 1) Identité voyageur ---------------------------------------------
    _section_title(c, 12 * mm, y, "1. Identite du voyageur")
    y -= 6 * mm

    nom = f"{(traveler.last_name or '').upper()} {traveler.first_name or ''}".strip()
    public_id = getattr(traveler, "public_id", "") or "-"
    nat = getattr(traveler.nationality, "name", None) if traveler.nationality_id else "-"

    _kv(c, 14 * mm, y, "Nom complet :", nom, label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Identifiant :", public_id, label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Passeport :", _safe(traveler.id_document_number), label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Date naissance :", _fmt_date(traveler.date_of_birth), label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Sexe :", _safe(traveler.get_gender_display() if hasattr(traveler, "get_gender_display") and traveler.gender else None), label_w=30 * mm)

    # Colonne droite identité
    rx = width / 2 + 5 * mm
    yy = y + 20 * mm
    _kv(c, rx, yy, "Telephone :", _safe(traveler.phone_mobile), label_w=25 * mm); yy -= 5 * mm
    _kv(c, rx, yy, "Email :", _safe(traveler.email), label_w=25 * mm); yy -= 5 * mm
    _kv(c, rx, yy, "Nationalite :", _safe(nat), label_w=25 * mm); yy -= 5 * mm
    _kv(c, rx, yy, "Profession :", _safe(getattr(traveler, "profession", None)), label_w=25 * mm); yy -= 5 * mm
    _kv(c, rx, yy, "Age :", _compute_age_years(traveler), label_w=25 * mm)

    y -= 8 * mm

    # --- 2) Voyage --------------------------------------------------------
    _section_title(c, 12 * mm, y, "2. Voyage")
    y -= 6 * mm
    entry_name = "-"
    if traveler.entry_point_id and getattr(traveler.entry_point, "name", None):
        entry_name = traveler.entry_point.name
    _kv(c, 14 * mm, y, "Point d'entree :", _safe(entry_name), label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Vol / Voyage :", _safe(getattr(traveler, "flight_or_voyage_number", None)), label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Siege :", _safe(getattr(traveler, "seat_number", None)), label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Date arrivee :", _fmt_date(getattr(traveler, "arrival_date", None)), label_w=30 * mm)
    y -= 8 * mm

    # --- 3) État du suivi -------------------------------------------------
    _section_title(c, 12 * mm, y, "3. Etat du suivi")
    y -= 6 * mm

    today = date.today()
    started = case.started_on
    expected_end = case.expected_end_on
    if started:
        current_day = max(1, (today - started).days + 1)
    else:
        current_day = 0
    duration = (expected_end - started).days + 1 if started and expected_end else 21

    disease_name = disease.name if disease else "-"
    _kv(c, 14 * mm, y, "Maladie :", _safe(disease_name), label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Jour actuel :", f"J{current_day} / J{duration}", label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Debut suivi :", _fmt_date(started), label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Fin prevue :", _fmt_date(expected_end), label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Statut :", _safe(case.status), label_w=30 * mm)
    y -= 8 * mm

    # --- 4) Classification ------------------------------------------------
    _section_title(c, 12 * mm, y, "4. Classification du cas")
    y -= 6 * mm

    classifications = list(
        CaseClassification.objects
        .filter(followup_case=case)
        .order_by("-classified_at")[:8]
    )
    current_cls = next((cl for cl in classifications if cl.is_current), None)
    if current_cls:
        _kv(c, 14 * mm, y, "Actuelle :",
            f"{current_cls.get_classification_display()} ({_fmt_date(current_cls.classified_at)})",
            label_w=30 * mm)
    else:
        _kv(c, 14 * mm, y, "Actuelle :", "Aucune classification enregistree", label_w=30 * mm)
    y -= 6 * mm

    c.setFont("Helvetica", 8); c.setFillColor(SLATE_500)
    c.drawString(14 * mm, y, "Historique (8 dernieres) :")
    y -= 4 * mm
    c.setFont("Helvetica", 8); c.setFillColor(SLATE_900)
    if classifications:
        for cl in classifications:
            line = (
                f"{'*' if cl.is_current else '.'} {_fmt_date(cl.classified_at)}  "
                f"- {cl.get_classification_display()}  "
                f"- {(cl.reason or '')[:60]}"
            )
            c.drawString(16 * mm, y, line[:120])
            y -= 4 * mm
            y = _new_page_if_needed(c, y, width, height)
    else:
        c.drawString(16 * mm, y, "(vide)")
        y -= 4 * mm

    y -= 4 * mm
    y = _new_page_if_needed(c, y, width, height, threshold=70 * mm)

    # --- 5) Check-ins quotidiens -----------------------------------------
    _section_title(c, 12 * mm, y, "5. Check-ins quotidiens (J1 -> J21)")
    y -= 6 * mm
    # En-tête tableau
    c.setFillColor(colors.HexColor("#E5E7EB"))
    c.rect(12 * mm, y - 1 * mm, width - 24 * mm, 5 * mm, fill=1, stroke=0)
    c.setFillColor(SLATE_900); c.setFont("Helvetica-Bold", 8)
    c.drawString(14 * mm, y + 0.5 * mm, "Jour")
    c.drawString(24 * mm, y + 0.5 * mm, "Date")
    c.drawString(48 * mm, y + 0.5 * mm, "Statut")
    c.drawString(78 * mm, y + 0.5 * mm, "Check OK")
    c.drawString(102 * mm, y + 0.5 * mm, "Temp.")
    c.drawString(120 * mm, y + 0.5 * mm, "Symptomes")
    c.drawString(150 * mm, y + 0.5 * mm, "Agent")
    y -= 5 * mm

    checks = list(
        DailyCheck.objects
        .filter(quarantine=case)
        .select_related("reported_by_user")
        .order_by("day_index")
    )
    c.setFont("Helvetica", 8); c.setFillColor(SLATE_900)
    for d in checks:
        check_ok = "Oui" if d.reported_by_user_id else ("Non" if d.status == "missed" else "-")
        temp = f"{d.temperature_celsius}°C" if d.temperature_celsius else "-"
        sympt = "Oui" if d.has_symptoms else "Non"
        agent = "-"
        if d.reported_by_user_id and hasattr(d, "reported_by_user") and d.reported_by_user:
            agent = (d.reported_by_user.get_full_name() or d.reported_by_user.email or "-")[:20]
        c.drawString(14 * mm, y, f"J{d.day_index}")
        c.drawString(24 * mm, y, _fmt_date(d.check_date))
        c.drawString(48 * mm, y, _safe(d.status)[:14])
        c.drawString(78 * mm, y, check_ok)
        c.drawString(102 * mm, y, temp)
        c.drawString(120 * mm, y, sympt)
        c.drawString(150 * mm, y, agent)
        y -= 4 * mm
        y = _new_page_if_needed(c, y, width, height)
    if not checks:
        c.drawString(14 * mm, y, "(aucun check-in)"); y -= 4 * mm

    y -= 4 * mm
    y = _new_page_if_needed(c, y, width, height, threshold=70 * mm)

    # --- 6) Symptômes -----------------------------------------------------
    _section_title(c, 12 * mm, y, "6. Symptomes declares")
    y -= 6 * mm
    c.setFillColor(colors.HexColor("#E5E7EB"))
    c.rect(12 * mm, y - 1 * mm, width - 24 * mm, 5 * mm, fill=1, stroke=0)
    c.setFillColor(SLATE_900); c.setFont("Helvetica-Bold", 8)
    c.drawString(14 * mm, y + 0.5 * mm, "Date")
    c.drawString(40 * mm, y + 0.5 * mm, "Symptome")
    c.drawString(95 * mm, y + 0.5 * mm, "Severite")
    c.drawString(125 * mm, y + 0.5 * mm, "Source")
    c.drawString(155 * mm, y + 0.5 * mm, "Crit.")
    y -= 5 * mm

    symptoms = list(
        MedicalSymptomReport.objects
        .filter(followup_case=case)
        .order_by("-onset_date", "-created_at")[:50]
    )
    c.setFont("Helvetica", 8); c.setFillColor(SLATE_900)
    for s in symptoms:
        c.drawString(14 * mm, y, _fmt_date(s.onset_date))
        c.drawString(40 * mm, y, _safe(s.symptom_label)[:32])
        c.drawString(95 * mm, y, _safe(s.severity))
        c.drawString(125 * mm, y, _safe(s.source))
        if s.is_critical:
            c.setFillColor(colors.HexColor("#DC2626"))
            c.drawString(155 * mm, y, "OUI")
            c.setFillColor(SLATE_900)
        else:
            c.drawString(155 * mm, y, "non")
        y -= 4 * mm
        y = _new_page_if_needed(c, y, width, height)
    if not symptoms:
        c.drawString(14 * mm, y, "(aucun symptome declare)"); y -= 4 * mm

    y -= 4 * mm
    y = _new_page_if_needed(c, y, width, height, threshold=70 * mm)

    # --- 7) Prélèvements --------------------------------------------------
    _section_title(c, 12 * mm, y, "7. Prelevements biologiques")
    y -= 6 * mm
    c.setFillColor(colors.HexColor("#E5E7EB"))
    c.rect(12 * mm, y - 1 * mm, width - 24 * mm, 5 * mm, fill=1, stroke=0)
    c.setFillColor(SLATE_900); c.setFont("Helvetica-Bold", 8)
    c.drawString(14 * mm, y + 0.5 * mm, "Code")
    c.drawString(50 * mm, y + 0.5 * mm, "Type")
    c.drawString(80 * mm, y + 0.5 * mm, "Preleve le")
    c.drawString(118 * mm, y + 0.5 * mm, "Transport")
    c.drawString(148 * mm, y + 0.5 * mm, "Labo")
    y -= 5 * mm

    samples = list(
        MedicalSample.objects.filter(followup_case=case).order_by("-created_at")[:30]
    )
    c.setFont("Helvetica", 8); c.setFillColor(SLATE_900)
    for s in samples:
        c.drawString(14 * mm, y, _safe(s.sample_code)[:18])
        c.drawString(50 * mm, y, _safe(s.sample_type))
        c.drawString(80 * mm, y, _fmt_date(s.collected_at))
        c.drawString(118 * mm, y, _safe(s.transport_status)[:14])
        c.drawString(148 * mm, y, _safe(s.destination_lab)[:24])
        y -= 4 * mm
        y = _new_page_if_needed(c, y, width, height)
    if not samples:
        c.drawString(14 * mm, y, "(aucun prelevement)"); y -= 4 * mm

    y -= 4 * mm
    y = _new_page_if_needed(c, y, width, height, threshold=70 * mm)

    # --- 8) Analyses labo -------------------------------------------------
    _section_title(c, 12 * mm, y, "8. Analyses de laboratoire")
    y -= 6 * mm
    c.setFillColor(colors.HexColor("#E5E7EB"))
    c.rect(12 * mm, y - 1 * mm, width - 24 * mm, 5 * mm, fill=1, stroke=0)
    c.setFillColor(SLATE_900); c.setFont("Helvetica-Bold", 8)
    c.drawString(14 * mm, y + 0.5 * mm, "Sample")
    c.drawString(50 * mm, y + 0.5 * mm, "Test")
    c.drawString(95 * mm, y + 0.5 * mm, "Resultat")
    c.drawString(125 * mm, y + 0.5 * mm, "Valide le")
    y -= 5 * mm

    analyses = list(
        LabAnalysis.objects
        .filter(sample__followup_case=case)
        .select_related("sample")
        .order_by("-created_at")[:30]
    )
    c.setFont("Helvetica", 8); c.setFillColor(SLATE_900)
    for a in analyses:
        c.drawString(14 * mm, y, _safe(a.sample.sample_code)[:18])
        c.drawString(50 * mm, y, _safe(a.test_type)[:28])
        if a.result == "positive":
            c.setFillColor(colors.HexColor("#DC2626"))
        c.drawString(95 * mm, y, _safe(a.result))
        c.setFillColor(SLATE_900)
        c.drawString(125 * mm, y, _fmt_date(a.validated_at))
        y -= 4 * mm
        y = _new_page_if_needed(c, y, width, height)
    if not analyses:
        c.drawString(14 * mm, y, "(aucune analyse)"); y -= 4 * mm

    # Footer page courante
    _draw_inhp_footer(c, width, ref=f"FSI-{case.uuid}")
    c.showPage()
    c.save()
    return buf.getvalue()


# ===========================================================================
# 2) Rapport de prélèvement (sample)
# ===========================================================================


def _qr_image_reader(payload: str):
    """Crée un QR code en mémoire et retourne un ImageReader ReportLab."""
    try:
        import qrcode
        from reportlab.lib.utils import ImageReader

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        bio.seek(0)
        return ImageReader(bio)
    except Exception:  # pragma: no cover
        logger.exception("Generation QR code KO")
        return None


def render_sample_collection_report(sample: MedicalSample) -> bytes:
    """Rapport de prélèvement — accompagne l'échantillon vers le labo (A4)."""
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    case = sample.followup_case
    traveler = case.traveler if case else None

    y = _draw_inhp_header(
        c, width, height,
        title="RAPPORT DE PRELEVEMENT BIOLOGIQUE",
        subtitle="Fiche d'accompagnement laboratoire - INHP",
    )

    # 1) Sample code en gros + QR code à droite
    c.setFillColor(CI_DARK)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(14 * mm, y - 2 * mm, sample.sample_code or "-")
    c.setFillColor(SLATE_500); c.setFont("Helvetica", 9)
    c.drawString(14 * mm, y - 9 * mm,
                 f"Type : {sample.get_sample_type_display() if hasattr(sample, 'get_sample_type_display') else sample.sample_type}")
    c.drawString(14 * mm, y - 14 * mm,
                 f"Statut transport : {sample.get_transport_status_display() if hasattr(sample, 'get_transport_status_display') else sample.transport_status}")

    # QR code (sample_code) pour scan labo
    qr_payload = f"EPITRACE:SAMPLE:{sample.sample_code}"
    qr_img = _qr_image_reader(qr_payload)
    if qr_img is not None:
        c.drawImage(qr_img, width - 50 * mm, y - 35 * mm, 36 * mm, 36 * mm)
    else:
        c.setStrokeColor(SLATE_500)
        c.rect(width - 50 * mm, y - 35 * mm, 36 * mm, 36 * mm)

    y -= 42 * mm

    # 2) Identité voyageur (anonymisée light)
    _section_title(c, 12 * mm, y, "Identite du voyageur (anonymisee)")
    y -= 6 * mm
    if traveler is not None:
        _kv(c, 14 * mm, y, "ID public :", _safe(traveler.public_id), label_w=30 * mm); y -= 5 * mm
        sex_label = (
            traveler.get_gender_display()
            if hasattr(traveler, "get_gender_display") and traveler.gender else "-"
        )
        _kv(c, 14 * mm, y, "Sexe :", sex_label, label_w=30 * mm); y -= 5 * mm
        _kv(c, 14 * mm, y, "Age :", _compute_age_years(traveler), label_w=30 * mm); y -= 5 * mm
        _kv(c, 14 * mm, y, "Passeport :", _mask_passport(traveler.id_document_number), label_w=30 * mm); y -= 5 * mm
        if case and case.disease_id:
            _kv(c, 14 * mm, y, "Maladie cible :", _safe(case.disease.name), label_w=30 * mm); y -= 5 * mm
    else:
        c.setFont("Helvetica", 9); c.setFillColor(SLATE_900)
        c.drawString(14 * mm, y, "(voyageur non renseigne)")
        y -= 5 * mm

    y -= 4 * mm

    # 3) Détails prélèvement
    _section_title(c, 12 * mm, y, "Details du prelevement")
    y -= 6 * mm
    _kv(c, 14 * mm, y, "Date / heure :", _fmt_date(sample.collected_at), label_w=35 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Lieu :", _safe(sample.collection_location), label_w=35 * mm); y -= 5 * mm
    agent_name = "-"
    if sample.collected_by_id and sample.collected_by:
        agent_name = (sample.collected_by.get_full_name()
                      or sample.collected_by.email or "-")
    _kv(c, 14 * mm, y, "Agent preleveur :", _safe(agent_name), label_w=35 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Conditions transport :", _safe(sample.transport_conditions)[:60], label_w=35 * mm); y -= 5 * mm
    y -= 4 * mm

    # 4) Chaîne de possession
    _section_title(c, 12 * mm, y, "Chaine de possession")
    y -= 6 * mm
    _kv(c, 14 * mm, y, "Depart transport :", _fmt_date(sample.transport_departed_at), label_w=40 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Recu au labo :", _fmt_date(sample.received_at), label_w=40 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Laboratoire destinataire :", _safe(sample.destination_lab), label_w=40 * mm); y -= 5 * mm
    y -= 4 * mm

    # 5) Test demandé (dérivé des analyses associées ou laissé libre)
    _section_title(c, 12 * mm, y, "Test demande")
    y -= 6 * mm
    analyses = list(LabAnalysis.objects.filter(sample=sample).order_by("created_at")[:5])
    if analyses:
        c.setFillColor(SLATE_900); c.setFont("Helvetica", 9)
        for a in analyses:
            c.drawString(14 * mm, y, f"- {a.test_type}  ({a.lab_name})")
            y -= 5 * mm
    else:
        c.setFillColor(SLATE_500); c.setFont("Helvetica-Oblique", 9)
        c.drawString(14 * mm, y, "(test a renseigner par le labo a reception)")
        y -= 5 * mm

    y -= 6 * mm

    # 6) Champ "Réception laboratoire" à remplir
    _section_title(c, 12 * mm, y, "Reception laboratoire (a remplir manuellement)")
    y -= 6 * mm
    c.setStrokeColor(SLATE_500); c.setLineWidth(0.4)
    for label in ("Date / heure de reception :",
                  "Nom du receptionnaire :",
                  "Etat du prelevement :",
                  "Signature :"):
        c.setFillColor(SLATE_500); c.setFont("Helvetica", 8)
        c.drawString(14 * mm, y + 4 * mm, label)
        c.line(60 * mm, y, width - 14 * mm, y)
        y -= 9 * mm
        y = _new_page_if_needed(c, y, width, height)

    _draw_inhp_footer(c, width, ref=f"SCR-{sample.sample_code}")
    c.showPage()
    c.save()
    return buf.getvalue()


# ===========================================================================
# 3) Fiche d'orientation médicale
# ===========================================================================


def render_medical_orientation_form(
    case: QuarantineRecord, agent=None,
) -> bytes:
    """Fiche d'orientation médicale — adresse un cas suspect à un centre."""
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    traveler = case.traveler

    y = _draw_inhp_header(
        c, width, height,
        title="FICHE D'ORIENTATION MEDICALE",
        subtitle="Orientation vers une structure de soins - INHP",
    )

    # En-tête bandeau orange
    c.setFillColor(CI_ORANGE)
    c.roundRect(12 * mm, y - 12 * mm, width - 24 * mm, 10 * mm, 3, fill=1, stroke=0)
    c.setFillColor(CI_WHITE); c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, y - 7.5 * mm,
                        "ORIENTATION VERS UN CENTRE DE SANTE")
    y -= 18 * mm

    # 1) Identité voyageur
    _section_title(c, 12 * mm, y, "1. Identite du voyageur")
    y -= 6 * mm
    nom = f"{(traveler.last_name or '').upper()} {traveler.first_name or ''}".strip()
    _kv(c, 14 * mm, y, "Nom complet :", nom, label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Identifiant :", _safe(traveler.public_id), label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Sexe :",
        traveler.get_gender_display() if hasattr(traveler, "get_gender_display") and traveler.gender else "-",
        label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Age :", _compute_age_years(traveler), label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Telephone :", _safe(traveler.phone_mobile), label_w=30 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Maladie suivie :",
        _safe(case.disease.name if case.disease_id else None), label_w=30 * mm)
    y -= 9 * mm

    # 2) Émetteur
    _section_title(c, 12 * mm, y, "2. Emetteur")
    y -= 6 * mm
    issued_at = timezone.now()
    agent_name = "Systeme EpiTrace"
    if agent is not None:
        agent_name = (
            getattr(agent, "get_full_name", lambda: None)()
            or getattr(agent, "email", None)
            or "Systeme EpiTrace"
        )
    _kv(c, 14 * mm, y, "Date emission :", issued_at.strftime("%d/%m/%Y a %H:%M"), label_w=35 * mm); y -= 5 * mm
    _kv(c, 14 * mm, y, "Agent INHP :", agent_name, label_w=35 * mm); y -= 9 * mm

    # 3) Motif d'orientation (classification)
    _section_title(c, 12 * mm, y, "3. Motif d'orientation")
    y -= 6 * mm
    current_cls = (
        CaseClassification.objects
        .filter(followup_case=case, is_current=True)
        .order_by("-classified_at")
        .first()
    )
    classification_label = (
        current_cls.get_classification_display() if current_cls else "Non classe"
    )

    # Cases à cocher pour les motifs
    motifs = ["Cas suspect", "Cas probable", "Cas confirme"]
    box_x = 16 * mm
    for motif in motifs:
        c.setStrokeColor(SLATE_900); c.setLineWidth(0.6)
        c.rect(box_x, y - 1 * mm, 3 * mm, 3 * mm, fill=0, stroke=1)
        match = (motif.lower().replace("cas ", "").replace("é", "e")
                 in (classification_label or "").lower().replace("é", "e"))
        if match:
            c.setFillColor(CI_DARK)
            c.rect(box_x + 0.5 * mm, y - 0.5 * mm, 2 * mm, 2 * mm, fill=1, stroke=0)
        c.setFillColor(SLATE_900); c.setFont("Helvetica", 10)
        c.drawString(box_x + 5 * mm, y, motif)
        box_x += 50 * mm
    y -= 8 * mm

    if current_cls and current_cls.reason:
        c.setFillColor(SLATE_500); c.setFont("Helvetica", 8)
        c.drawString(14 * mm, y, f"Motif detaille : {current_cls.reason[:120]}")
        y -= 5 * mm

    y -= 4 * mm

    # 4) Symptômes critiques observés
    _section_title(c, 12 * mm, y, "4. Symptomes critiques observes")
    y -= 6 * mm
    critical_symptoms = list(
        MedicalSymptomReport.objects
        .filter(followup_case=case, is_critical=True)
        .order_by("-onset_date")[:10]
    )
    c.setFillColor(SLATE_900); c.setFont("Helvetica", 9)
    if critical_symptoms:
        for s in critical_symptoms:
            line = f"- {s.symptom_label} ({s.severity}) - {_fmt_date(s.onset_date)}"
            c.drawString(14 * mm, y, line[:90])
            y -= 5 * mm
    else:
        c.setFillColor(SLATE_500); c.setFont("Helvetica-Oblique", 9)
        c.drawString(14 * mm, y, "Aucun symptome critique enregistre a ce jour.")
        y -= 5 * mm

    y -= 4 * mm

    # 5) Centre de santé destinataire (à remplir)
    _section_title(c, 12 * mm, y, "5. Centre de sante destinataire (a remplir)")
    y -= 6 * mm
    c.setStrokeColor(SLATE_500); c.setLineWidth(0.4)
    for label in (
        "Nom du centre :",
        "Adresse / localite :",
        "Medecin receveur :",
        "Telephone du centre :",
    ):
        c.setFillColor(SLATE_500); c.setFont("Helvetica", 8)
        c.drawString(14 * mm, y + 4 * mm, label)
        c.line(60 * mm, y, width - 14 * mm, y)
        y -= 9 * mm

    # 6) Mesures d'isolement préventif (case à cocher)
    _section_title(c, 12 * mm, y, "6. Mesures d'isolement preventif")
    y -= 6 * mm
    c.setStrokeColor(SLATE_900); c.setLineWidth(0.6)
    c.rect(14 * mm, y - 1 * mm, 3 * mm, 3 * mm, fill=0, stroke=1)
    c.setFillColor(SLATE_900); c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, "Isolement preventif recommande des reception")
    y -= 6 * mm
    c.setStrokeColor(SLATE_900)
    c.rect(14 * mm, y - 1 * mm, 3 * mm, 3 * mm, fill=0, stroke=1)
    c.drawString(20 * mm, y, "EPI complet exige (gants, masque FFP2, lunettes, blouse)")
    y -= 8 * mm

    # 7) Consignes spécifiques (texte libre)
    _section_title(c, 12 * mm, y, "7. Consignes specifiques")
    y -= 5 * mm
    c.setStrokeColor(SLATE_500)
    for _ in range(3):
        c.line(14 * mm, y, width - 14 * mm, y)
        y -= 6 * mm

    y -= 4 * mm
    y = _new_page_if_needed(c, y, width, height, threshold=40 * mm)

    # 8) Signature électronique INHP
    _section_title(c, 12 * mm, y, "8. Signature electronique INHP")
    y -= 6 * mm
    c.setFillColor(SLATE_900); c.setFont("Helvetica", 9)
    c.drawString(14 * mm, y, f"Reference du cas : {case.uuid}")
    y -= 5 * mm
    c.drawString(14 * mm, y, f"Emis par : {agent_name}")
    y -= 5 * mm
    c.drawString(14 * mm, y, f"Date : {issued_at.strftime('%d/%m/%Y a %H:%M')}")
    y -= 5 * mm
    c.setFillColor(SLATE_500); c.setFont("Helvetica-Oblique", 8)
    c.drawString(14 * mm, y, "Document signe electroniquement par EpiTrace.")

    _draw_inhp_footer(c, width, ref=f"MOF-{case.uuid}", issued_at=issued_at)
    c.showPage()
    c.save()
    return buf.getvalue()
