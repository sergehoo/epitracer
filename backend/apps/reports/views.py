"""Centre de rapports — API d'export.

Endpoints (tous protégés NATIONAL_ADMIN / MINISTRY / INHP) :

    GET /api/v1/reports/types/                       → métadonnées des rapports
    GET /api/v1/reports/travelers/?format=csv|pdf    → liste voyageurs
    GET /api/v1/reports/alerts/?format=csv|pdf       → liste alertes santé
    GET /api/v1/reports/followups/?format=csv|pdf    → quarantaines + check-ins
    GET /api/v1/reports/checkins/?format=csv|pdf     → check-ins quotidiens
    GET /api/v1/reports/overview/?format=pdf         → synthèse globale (KPIs)

Tous les rapports acceptent :
    date_from = YYYY-MM-DD
    date_to   = YYYY-MM-DD
Plus quelques filtres spécifiques par rapport (cf. handler).
"""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import RoleCode
from apps.core.permissions import HasRole, IsAuthenticatedAndActive

from .utils import (
    csv_response,
    default_period,
    parse_date,
    pdf_response,
    safe_getattr,
)


# ---------------------------------------------------------------------------
# Métadonnées des rapports — utilisées par le frontend pour générer les cartes.
# ---------------------------------------------------------------------------
REPORT_CATALOG = [
    {
        "key": "travelers",
        "title": "Voyageurs enregistrés",
        "description": "Liste des voyageurs avec point d'entrée, transport, statut.",
        "icon": "users",
        "tone": "green",
        "formats": ["csv", "pdf"],
        "filters": ["date_from", "date_to", "entry_point", "transport_mode"],
    },
    {
        "key": "alerts",
        "title": "Alertes de santé",
        "description": "Alertes ouvertes / résolues avec sévérité et maladie associée.",
        "icon": "alert",
        "tone": "rose",
        "formats": ["csv", "pdf"],
        "filters": ["date_from", "date_to", "severity", "status", "disease"],
    },
    {
        "key": "followups",
        "title": "Suivi 21 jours",
        "description": "Quarantaines actives ou clôturées avec taux de complétion check-ins.",
        "icon": "clock",
        "tone": "orange",
        "formats": ["csv", "pdf"],
        "filters": ["date_from", "date_to", "status", "disease"],
    },
    {
        "key": "checkins",
        "title": "Check-ins quotidiens",
        "description": "Détail des auto-déclarations quotidiennes (symptômes, ressenti).",
        "icon": "check",
        "tone": "blue",
        "formats": ["csv", "pdf"],
        "filters": ["date_from", "date_to", "alert_raised"],
    },
    {
        "key": "overview",
        "title": "Synthèse épidémiologique",
        "description": "Vue d'ensemble nationale (KPIs + répartition par maladie/point d'entrée).",
        "icon": "report",
        "tone": "dark",
        "formats": ["pdf"],
        "filters": ["date_from", "date_to"],
    },
]


class ReportTypesView(APIView):
    """Renvoie le catalogue des rapports — métadonnées affichées côté admin."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"reports": REPORT_CATALOG})


# ---------------------------------------------------------------------------
# Mixin : permissions communes à tous les rapports
# ---------------------------------------------------------------------------
class _BaseReportView(APIView):
    permission_classes = [IsAuthenticatedAndActive, HasRole]
    required_roles = [
        RoleCode.NATIONAL_ADMIN,
        RoleCode.MINISTRY,
        RoleCode.INHP,
    ]

    def _period(self, request):
        d_from = parse_date(request.query_params.get("date_from"))
        d_to = parse_date(request.query_params.get("date_to"))
        if not d_from or not d_to:
            df, dt = default_period()
            d_from = d_from or df
            d_to = d_to or dt
        return d_from, d_to

    def _fmt(self, request) -> str:
        return (request.query_params.get("format") or "csv").lower()

    def _filename(self, key: str, fmt: str, d_from, d_to) -> str:
        ext = "pdf" if fmt == "pdf" else "csv"
        return f"epitrace_{key}_{d_from.isoformat()}_{d_to.isoformat()}.{ext}"


# ---------------------------------------------------------------------------
# 1) Rapport voyageurs
# ---------------------------------------------------------------------------
class TravelersReportView(_BaseReportView):
    def get(self, request):
        from apps.travelers.models import Traveler

        d_from, d_to = self._period(request)
        qs = (
            Traveler.objects.select_related("entry_point")
            .filter(arrival_date__gte=d_from, arrival_date__lte=d_to)
        )

        entry_point = request.query_params.get("entry_point")
        if entry_point:
            qs = qs.filter(entry_point_id=entry_point)
        transport = request.query_params.get("transport_mode")
        if transport:
            qs = qs.filter(transport_mode=transport)

        qs = qs.order_by("-arrival_date")[:5000]  # garde-fou

        headers = [
            "ID public",
            "Nom",
            "Prénom",
            "Sexe",
            "Âge",
            "Date arrivée",
            "Transport",
            "N° vol/voyage",
            "Point d'entrée",
            "Nationalité",
            "Téléphone",
            "Email",
        ]
        rows = []
        for t in qs:
            rows.append([
                t.public_id,
                t.last_name,
                t.first_name,
                t.get_gender_display() if t.gender else "",
                f"{t.age} {t.age_unit}" if t.age else "",
                t.arrival_date,
                t.get_transport_mode_display() if t.transport_mode else "",
                t.flight_or_voyage_number,
                t.entry_point.name if t.entry_point_id else "",
                safe_getattr(t, "nationality", "nationality_code", "country_of_origin"),
                safe_getattr(t, "whatsapp_number", "phone", "phone_number"),
                safe_getattr(t, "email"),
            ])

        fmt = self._fmt(request)
        filename = self._filename("voyageurs", fmt, d_from, d_to)
        if fmt == "pdf":
            return pdf_response(
                filename,
                title="Rapport — Voyageurs enregistrés",
                subtitle=f"Période du {d_from.strftime('%d/%m/%Y')} au {d_to.strftime('%d/%m/%Y')}",
                headers=headers,
                rows=rows,
                summary=[("Total voyageurs", str(len(rows)))],
            )
        return csv_response(filename, headers, rows)


# ---------------------------------------------------------------------------
# 2) Rapport alertes
# ---------------------------------------------------------------------------
class AlertsReportView(_BaseReportView):
    def get(self, request):
        from apps.surveillance.models import HealthAlert

        d_from, d_to = self._period(request)
        qs = (
            HealthAlert.objects.select_related("disease", "entry_point", "zone")
            .filter(created_at__date__gte=d_from, created_at__date__lte=d_to)
        )

        severity = request.query_params.get("severity")
        if severity:
            qs = qs.filter(severity=severity)
        status_p = request.query_params.get("status")
        if status_p:
            qs = qs.filter(status=status_p)
        disease = request.query_params.get("disease")
        if disease:
            qs = qs.filter(disease_id=disease)

        qs = qs.order_by("-created_at")[:5000]

        headers = [
            "Date",
            "Titre",
            "Sévérité",
            "Statut",
            "Maladie",
            "Point d'entrée",
            "Zone",
            "Acquittée le",
        ]
        rows = []
        for a in qs:
            rows.append([
                timezone.localtime(a.created_at),
                a.title,
                a.get_severity_display(),
                a.get_status_display(),
                a.disease.name if a.disease_id else "",
                a.entry_point.name if a.entry_point_id else "",
                safe_getattr(a.zone, "name") if a.zone_id else "",
                timezone.localtime(a.acknowledged_at) if a.acknowledged_at else None,
            ])

        # KPIs synthèse
        summary = [
            ("Total alertes", str(len(rows))),
            ("Ouvertes", str(sum(1 for r in rows if r[3] == "Ouverte" or r[3] == "Open" or "Ouverte" in str(r[3])))),
            ("Acquittées", str(sum(1 for r in rows if r[7] is not None))),
        ]

        fmt = self._fmt(request)
        filename = self._filename("alertes", fmt, d_from, d_to)
        if fmt == "pdf":
            return pdf_response(
                filename,
                title="Rapport — Alertes de santé",
                subtitle=f"Période du {d_from.strftime('%d/%m/%Y')} au {d_to.strftime('%d/%m/%Y')}",
                headers=headers,
                rows=rows,
                summary=summary,
            )
        return csv_response(filename, headers, rows)


# ---------------------------------------------------------------------------
# 3) Rapport suivi 21 jours
# ---------------------------------------------------------------------------
class FollowupsReportView(_BaseReportView):
    def get(self, request):
        from apps.quarantine.models import QuarantineRecord

        d_from, d_to = self._period(request)
        qs = (
            QuarantineRecord.objects.select_related("traveler", "disease")
            .filter(started_on__gte=d_from, started_on__lte=d_to)
        )

        status_p = request.query_params.get("status")
        if status_p:
            qs = qs.filter(status=status_p)
        disease = request.query_params.get("disease")
        if disease:
            qs = qs.filter(disease_id=disease)

        qs = qs.annotate(
            checks_total=Count("daily_checks"),
            checks_with_symptoms=Count("daily_checks", filter=Q(daily_checks__has_symptoms=True)),
            alerts_raised=Count("daily_checks", filter=Q(daily_checks__alert_raised=True)),
        ).order_by("-started_on")[:5000]

        headers = [
            "ID voyageur",
            "Nom",
            "Maladie",
            "Statut",
            "Début",
            "Fin prévue",
            "Fin réelle",
            "Check-ins faits",
            "Avec symptômes",
            "Alertes",
            "Adresse",
        ]
        rows = []
        for q in qs:
            t = q.traveler
            rows.append([
                t.public_id if t else "",
                f"{t.last_name} {t.first_name}" if t else "",
                q.disease.name if q.disease_id else "",
                q.get_status_display(),
                q.started_on,
                q.expected_end_on,
                q.actual_end_on,
                q.checks_total,
                q.checks_with_symptoms,
                q.alerts_raised,
                q.address,
            ])

        summary = [
            ("Total suivis", str(len(rows))),
            ("Avec ≥1 symptôme", str(sum(1 for r in rows if r[8] and int(r[8]) > 0))),
            ("Avec alerte", str(sum(1 for r in rows if r[9] and int(r[9]) > 0))),
        ]

        fmt = self._fmt(request)
        filename = self._filename("suivi-21j", fmt, d_from, d_to)
        if fmt == "pdf":
            return pdf_response(
                filename,
                title="Rapport — Suivi 21 jours (quarantaines)",
                subtitle=f"Quarantaines débutées entre le {d_from.strftime('%d/%m/%Y')} et le {d_to.strftime('%d/%m/%Y')}",
                headers=headers,
                rows=rows,
                summary=summary,
            )
        return csv_response(filename, headers, rows)


# ---------------------------------------------------------------------------
# 4) Rapport check-ins quotidiens
# ---------------------------------------------------------------------------
class CheckinsReportView(_BaseReportView):
    def get(self, request):
        from apps.quarantine.models import DailyCheck

        d_from, d_to = self._period(request)
        qs = (
            DailyCheck.objects.select_related("quarantine", "quarantine__traveler", "quarantine__disease")
            .filter(check_date__gte=d_from, check_date__lte=d_to)
        )

        alert_raised = request.query_params.get("alert_raised")
        if alert_raised in {"true", "1"}:
            qs = qs.filter(alert_raised=True)
        elif alert_raised in {"false", "0"}:
            qs = qs.filter(alert_raised=False)

        qs = qs.order_by("-check_date")[:10000]

        headers = [
            "Date",
            "J (jour)",
            "ID voyageur",
            "Nom",
            "Maladie",
            "Symptômes",
            "Alerte déclenchée",
            "Auto-déclaré",
        ]
        rows = []
        for c in qs:
            t = c.quarantine.traveler if c.quarantine_id and c.quarantine.traveler_id else None
            rows.append([
                c.check_date,
                f"J{c.day_index}",
                t.public_id if t else "",
                f"{t.last_name} {t.first_name}" if t else "",
                c.quarantine.disease.name if c.quarantine and c.quarantine.disease_id else "",
                c.has_symptoms,
                c.alert_raised,
                c.is_self_reported,
            ])

        summary = [
            ("Total check-ins", str(len(rows))),
            ("Avec symptômes", str(sum(1 for r in rows if r[5]))),
            ("Avec alerte", str(sum(1 for r in rows if r[6]))),
        ]

        fmt = self._fmt(request)
        filename = self._filename("checkins", fmt, d_from, d_to)
        if fmt == "pdf":
            return pdf_response(
                filename,
                title="Rapport — Check-ins quotidiens",
                subtitle=f"Période du {d_from.strftime('%d/%m/%Y')} au {d_to.strftime('%d/%m/%Y')}",
                headers=headers,
                rows=rows,
                summary=summary,
            )
        return csv_response(filename, headers, rows)


# ---------------------------------------------------------------------------
# 5) Synthèse globale (PDF uniquement)
# ---------------------------------------------------------------------------
class OverviewReportView(_BaseReportView):
    def get(self, request):
        from apps.travelers.models import Traveler
        from apps.surveillance.models import HealthAlert
        from apps.quarantine.models import QuarantineRecord, DailyCheck
        from apps.health_pass.models import HealthPass
        from apps.geo.models import EntryPoint
        from apps.diseases.models import Disease

        d_from, d_to = self._period(request)

        # KPIs globaux
        n_travelers = Traveler.objects.filter(arrival_date__gte=d_from, arrival_date__lte=d_to).count()
        n_passes = HealthPass.objects.filter(created_at__date__gte=d_from, created_at__date__lte=d_to).count()
        n_alerts = HealthAlert.objects.filter(created_at__date__gte=d_from, created_at__date__lte=d_to).count()
        n_qr_active = QuarantineRecord.objects.filter(status__in=["ACTIVE", "EXTENDED"]).count()
        n_checkins = DailyCheck.objects.filter(check_date__gte=d_from, check_date__lte=d_to).count()
        n_with_symptoms = DailyCheck.objects.filter(
            check_date__gte=d_from, check_date__lte=d_to, has_symptoms=True
        ).count()

        summary = [
            ("Voyageurs enregistrés", str(n_travelers)),
            ("Health passes émis", str(n_passes)),
            ("Alertes générées", str(n_alerts)),
            ("Quarantaines actives", str(n_qr_active)),
            ("Check-ins reçus", str(n_checkins)),
            ("Check-ins avec symptômes", str(n_with_symptoms)),
        ]

        # Top 5 maladies par alertes
        top_diseases_rows = list(
            HealthAlert.objects.filter(
                created_at__date__gte=d_from, created_at__date__lte=d_to,
            )
            .values("disease__name")
            .annotate(n=Count("id"))
            .order_by("-n")[:5]
        )

        # Top 5 points d'entrée par flux voyageurs
        top_ep_rows = list(
            Traveler.objects.filter(arrival_date__gte=d_from, arrival_date__lte=d_to)
            .values("entry_point__name")
            .annotate(n=Count("id"))
            .order_by("-n")[:5]
        )

        # Construction du PDF avec 2 tableaux
        headers_diseases = ["Maladie", "Nb alertes"]
        rows_diseases = [
            [r["disease__name"] or "—", r["n"]] for r in top_diseases_rows
        ] or [["Aucune alerte sur la période", 0]]

        headers_ep = ["Point d'entrée", "Nb voyageurs"]
        rows_ep = [
            [r["entry_point__name"] or "—", r["n"]] for r in top_ep_rows
        ] or [["Aucun voyageur sur la période", 0]]

        # On compose un PDF combiné en utilisant nos helpers : 2 tableaux successifs.
        # Le helper pdf_response ne prend qu'un seul tableau ; on construit ici
        # manuellement le document pour pouvoir afficher les 2 sections.
        from io import BytesIO
        from reportlab.lib import colors as _colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm as _mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )
        from django.http import HttpResponse

        from .utils import CI_GREEN, CI_DARK, CI_LIGHT_GREEN

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=15 * _mm,
            rightMargin=15 * _mm,
            topMargin=15 * _mm,
            bottomMargin=15 * _mm,
            title="Synthèse épidémiologique EpiTrace",
            author="EpiTrace",
        )
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=CI_DARK, fontSize=20)
        h2 = ParagraphStyle("h2", parent=styles["Normal"], textColor=_colors.HexColor("#475569"), fontSize=10, spaceAfter=4 * _mm)
        h3 = ParagraphStyle("h3", parent=styles["Heading2"], textColor=CI_DARK, fontSize=13, spaceBefore=6 * _mm, spaceAfter=2 * _mm)

        elements = [
            Paragraph("<b>Synthèse épidémiologique nationale</b>", h1),
            Paragraph(
                f"Période du {d_from.strftime('%d/%m/%Y')} au {d_to.strftime('%d/%m/%Y')}  •  "
                f"Généré le {timezone.localtime().strftime('%d/%m/%Y à %H:%M')}  •  "
                f"EpiTrace — MSHPCMU / INHP",
                h2,
            ),
        ]

        # Bloc KPIs (2 colonnes)
        kpi_rows = [[Paragraph(f"<b>{lbl}</b>", styles["Normal"]), val] for lbl, val in summary]
        kpi_table = Table(kpi_rows, colWidths=[100 * _mm, None])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), CI_LIGHT_GREEN),
            ("BOX", (0, 0), (-1, -1), 0.5, _colors.HexColor("#D1D5DB")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, _colors.HexColor("#E5E7EB")),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(kpi_table)

        def _section(title: str, hdrs, body):
            elements.append(Paragraph(title, h3))
            data = [[Paragraph(f"<b>{h}</b>", styles["Normal"]) for h in hdrs]]
            for row in body:
                data.append([str(c) if c is not None else "—" for c in row])
            tbl = Table(data, colWidths=[None, 40 * _mm])
            tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), CI_GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), _colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_colors.white, _colors.HexColor("#F8FAFC")]),
                ("BOX", (0, 0), (-1, -1), 0.25, _colors.HexColor("#D1D5DB")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, _colors.HexColor("#E5E7EB")),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            elements.append(tbl)

        _section("Top 5 maladies par nombre d'alertes", headers_diseases, rows_diseases)
        _section("Top 5 points d'entrée par flux voyageurs", headers_ep, rows_ep)

        def _footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(_colors.HexColor("#94A3B8"))
            canvas.drawString(
                15 * _mm, 8 * _mm,
                "EpiTrace — Système national de veille épidémiologique • "
                "Confidentiel — usage administratif uniquement",
            )
            canvas.drawRightString(doc.pagesize[0] - 15 * _mm, 8 * _mm, f"Page {doc.page}")
            canvas.restoreState()

        doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
        pdf = buf.getvalue()
        buf.close()

        filename = self._filename("synthese", "pdf", d_from, d_to)
        resp = HttpResponse(pdf, content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp
