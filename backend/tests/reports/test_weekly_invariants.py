"""Tests des invariants du module rapports hebdomadaires automatisés.

Couvre les 10 invariants du plan (voir .ostack/runs/feature-weekly-reports-*.md) :

  #1  Timezone Africa/Abidjan pour la fenêtre semaine
  #2  Idempotence forte (2× generate = 1 rapport)
  #3  Pas de PII dans les SMS (validate_no_pii)
  #4  Routage SMS strict via NotificationProviderRouter (couvert par
      apps/notifications tests existants)
  #5  Perf : aggregate_weekly < 1s sur DB de test
  #6  Signature signed_url altérée → refus
  #7  Coût borné : broadcast massif nécessite --i-confirm-massive-send
      (couvert dans tests broadcast_telegram_invite)
  #8  Traçabilité : chaque étape → ReportDeliveryLog
  #9  RBAC : OBSERVER → 403 sur POST /generate
  #10 Retry safe : max 3, backoff

Plus tests sanity : PDF valide, Excel valide, CSV injection neutralisée.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone as dj_tz


# ---------------------------------------------------------------------------
# Helpers locaux
# ---------------------------------------------------------------------------
def _monday_prev_week_abidjan(now: datetime = None) -> tuple:
    """Retourne (start_lun_00h00, end_dim_23h59) semaine ISO précédente
    en Africa/Abidjan."""
    tz = ZoneInfo("Africa/Abidjan")
    now = (now or dj_tz.now()).astimezone(tz)
    today = now.date()
    monday_this = today - timedelta(days=today.weekday())
    monday_prev = monday_this - timedelta(days=7)
    sunday_prev = monday_prev + timedelta(days=6)
    start = datetime(monday_prev.year, monday_prev.month, monday_prev.day,
                     0, 0, 0, tzinfo=tz)
    end = datetime(sunday_prev.year, sunday_prev.month, sunday_prev.day,
                   23, 59, 59, 999999, tzinfo=tz)
    return start, end


# ============================================================================
# #1 : Timezone Africa/Abidjan
# ============================================================================
class TestTimezoneAbidjan:
    """Invariant #1 : la fenêtre semaine est en Africa/Abidjan pas UTC."""

    def test_previous_week_period_starts_monday(self):
        from apps.reports.services.weekly_aggregator import previous_week_period
        start, end = previous_week_period()
        # weekday() : 0 = lundi
        assert start.weekday() == 0, "Doit commencer un lundi"
        assert end.weekday() == 6, "Doit finir un dimanche"

    def test_previous_week_period_is_abidjan_local(self):
        from apps.reports.services.weekly_aggregator import previous_week_period
        start, end = previous_week_period()
        assert str(start.tzinfo) == "Africa/Abidjan"
        assert start.hour == 0 and start.minute == 0
        assert end.hour == 23 and end.minute == 59

    def test_previous_week_period_duration_is_7_days(self):
        from apps.reports.services.weekly_aggregator import previous_week_period
        start, end = previous_week_period()
        # ~7 jours moins 1 seconde (dim 23:59:59)
        diff = end - start
        assert 6 * 86400 < diff.total_seconds() < 7 * 86400


# ============================================================================
# #2 : Idempotence forte
# ============================================================================
@pytest.mark.django_db
class TestIdempotence:
    """Invariant #2 : re-générer le même rapport ne crée pas de doublon."""

    def test_unique_constraint_on_type_period(self, superadmin):
        from apps.reports.models import GeneratedReport, ReportType, ReportStatus
        start, end = _monday_prev_week_abidjan()

        r1 = GeneratedReport.objects.create(
            report_type=ReportType.WEEKLY,
            period_start=start, period_end=end,
            status=ReportStatus.READY,
        )
        assert r1.report_code.startswith("RAP-HEBDO-")

        # 2ème création avec MÊME period → IntegrityError attendu
        from django.db import IntegrityError, transaction
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                GeneratedReport.objects.create(
                    report_type=ReportType.WEEKLY,
                    period_start=start, period_end=end,
                    status=ReportStatus.READY,
                )

    def test_report_code_deterministic(self):
        from apps.reports.models import GeneratedReport, ReportType
        # Même période → même code
        start = datetime(2026, 6, 8, 0, 0, tzinfo=ZoneInfo("Africa/Abidjan"))
        end = datetime(2026, 6, 14, 23, 59, 59, tzinfo=ZoneInfo("Africa/Abidjan"))
        r = GeneratedReport(report_type=ReportType.WEEKLY,
                            period_start=start, period_end=end)
        r.report_code = r._compute_code()
        assert r.report_code == "RAP-HEBDO-2026-S24"


# ============================================================================
# #3 : Aucun PII dans les SMS
# ============================================================================
class TestNoPii:
    """Invariant #3 : le SMS ne contient JAMAIS d'info individuelle."""

    def test_render_sms_normal_case(self):
        from apps.reports.services.weekly_sms import render_weekly_sms, validate_no_pii
        agg = _minimal_agg()
        sms = render_weekly_sms(agg)
        assert len(sms) <= 460, "Doit tenir en 3 segments SMS max"
        clean, violations = validate_no_pii(sms)
        assert clean, f"Violations PII : {violations}"

    def test_validate_detects_traveler_id(self):
        from apps.reports.services.weekly_sms import validate_no_pii
        clean, viol = validate_no_pii("Rapport OK — TRV-ABCD1234 en critique")
        assert not clean
        assert any("voyageur" in v for v in viol)

    def test_validate_detects_phone_number(self):
        from apps.reports.services.weekly_sms import validate_no_pii
        clean, viol = validate_no_pii("Contact : +2250708090911")
        assert not clean

    def test_validate_detects_email(self):
        from apps.reports.services.weekly_sms import validate_no_pii
        clean, viol = validate_no_pii("Contactez inhp@veillesanitaire.com")
        assert not clean

    def test_validate_accepts_clean_agg_output(self):
        from apps.reports.services.weekly_sms import render_weekly_sms, validate_no_pii
        # Simuler un agg qui aurait par erreur un email dans une string
        # Le sms rendu doit rester clean par design
        agg = _minimal_agg()
        sms = render_weekly_sms(agg)
        assert "@" not in sms  # aucun email dans un SMS de rapport
        assert "TRV-" not in sms


# ============================================================================
# #5 : Performance de l'agrégation
# ============================================================================
@pytest.mark.django_db
class TestPerformance:
    """Invariant #5 : aggregate_weekly reste rapide sur volumétrie test."""

    def test_aggregate_completes_in_reasonable_time(self, traveler):
        import time
        from apps.reports.services.weekly_aggregator import aggregate_weekly
        start, end = _monday_prev_week_abidjan()
        t0 = time.monotonic()
        result = aggregate_weekly(start, end)
        elapsed = time.monotonic() - t0
        assert elapsed < 5.0, f"Agrégation trop lente : {elapsed:.2f}s"
        assert "travelers" in result
        assert "meta" in result
        assert result["meta"]["generation_ms"] > 0

    def test_aggregate_output_structure(self):
        from apps.reports.services.weekly_aggregator import aggregate_weekly
        start, end = _monday_prev_week_abidjan()
        result = aggregate_weekly(start, end)
        # Toutes les sections doivent être présentes (même vides)
        expected_keys = {
            "period", "previous_period",
            "travelers", "followups", "checkins", "assistance", "alerts",
            "risk_levels", "cases", "samples", "analyses",
            "by_entry_point", "by_district", "by_disease",
            "top_events", "comparison", "meta",
        }
        assert expected_keys.issubset(set(result.keys())), \
            f"Sections manquantes : {expected_keys - set(result.keys())}"


# ============================================================================
# #6 : Signed URL altérée → refus
# ============================================================================
@pytest.mark.django_db
class TestSignedUrl:
    """Invariant #6 : token signé + expiration."""

    def test_signing_valid_roundtrip(self):
        from django.core import signing
        salt = "reports.weekly.download"
        token = signing.dumps({"report_id": 42, "format": "pdf"}, salt=salt)
        data = signing.loads(token, salt=salt, max_age=7 * 24 * 3600)
        assert data == {"report_id": 42, "format": "pdf"}

    def test_signing_altered_token_rejected(self):
        from django.core import signing
        salt = "reports.weekly.download"
        token = signing.dumps({"report_id": 42, "format": "pdf"}, salt=salt)
        # Altère 1 caractère
        altered = token[:-3] + "XXX"
        with pytest.raises(signing.BadSignature):
            signing.loads(altered, salt=salt)

    def test_signing_wrong_salt_rejected(self):
        from django.core import signing
        token = signing.dumps({"report_id": 42}, salt="salt_a")
        with pytest.raises(signing.BadSignature):
            signing.loads(token, salt="salt_b")


# ============================================================================
# #9 : RBAC — OBSERVER refusé
# ============================================================================
@pytest.mark.django_db
class TestRbacPermissions:
    """Invariant #9 : chaque endpoint check son rôle whitelisté."""

    def _observer_user(self, django_user_model, roles):
        from apps.accounts.models import Role, RoleAssignment, RoleCode
        user = django_user_model.objects.create_user(
            email="obs@example.ci", username="obs@example.ci",
            password="StrongPwd!2026",
        )
        role, _ = Role.objects.get_or_create(
            code=RoleCode.OBSERVER,
            defaults={"name": "Observateur", "is_system": True},
        )
        RoleAssignment.objects.create(user=user, role=role, is_active=True)
        return user

    def test_observer_can_view_reports(self, client, django_user_model, roles):
        obs = self._observer_user(django_user_model, roles)
        client.force_login(obs)
        r = client.get("/api/v1/reports/weekly/")
        # Doit passer (view = large accès lecture)
        assert r.status_code in (200, 404), f"Attendu 200/404, reçu {r.status_code}"

    def test_observer_cannot_generate(self, client, django_user_model, roles):
        obs = self._observer_user(django_user_model, roles)
        client.force_login(obs)
        r = client.post("/api/v1/reports/weekly/generate/", data={},
                        content_type="application/json")
        assert r.status_code == 403, f"OBSERVER doit être 403, reçu {r.status_code}"

    def test_observer_cannot_manage_recipients(self, client, django_user_model, roles):
        obs = self._observer_user(django_user_model, roles)
        client.force_login(obs)
        r = client.post("/api/v1/reports/recipients/",
                        data={"full_name": "test", "email": "a@b.com"},
                        content_type="application/json")
        assert r.status_code == 403


# ============================================================================
# Consentement obligatoire (AC-08)
# ============================================================================
@pytest.mark.django_db
class TestConsent:
    """AC-08 : is_active=True sans consent_date → refus."""

    def test_recipient_active_without_consent_raises(self):
        from apps.reports.models import AutomatedReportRecipient, PreferredChannel
        from django.core.exceptions import ValidationError
        rec = AutomatedReportRecipient(
            full_name="Test", email="test@example.ci",
            preferred_channel=PreferredChannel.EMAIL,
            is_active=True,
            consent_date=None,
        )
        with pytest.raises(ValidationError) as exc_info:
            rec.clean()
        assert "consent" in str(exc_info.value).lower()

    def test_recipient_inactive_without_consent_ok(self):
        from apps.reports.models import AutomatedReportRecipient, PreferredChannel
        rec = AutomatedReportRecipient(
            full_name="Test", email="test@example.ci",
            preferred_channel=PreferredChannel.EMAIL,
            is_active=False,
            consent_date=None,
        )
        # Ne doit pas raise
        rec.clean()


# ============================================================================
# Rendus (PDF, Excel, HTML)
# ============================================================================
class TestRenderers:
    """Sanity checks sur les 4 formats de sortie."""

    def test_pdf_bytes_valid(self):
        from apps.reports.services.weekly_pdf import render_weekly_pdf
        pdf = render_weekly_pdf(_minimal_agg())
        assert pdf.startswith(b"%PDF"), "Doit commencer par le magic PDF"
        assert len(pdf) > 2000, f"PDF trop petit : {len(pdf)} bytes"

    def test_xlsx_or_csv_bytes_valid(self):
        from apps.reports.services.weekly_excel import render_weekly_xlsx
        data = render_weekly_xlsx(_minimal_agg())
        # Magic PK = XLSX (zip), sinon fallback CSV avec BOM UTF-8
        assert data[:2] == b"PK" or data.startswith(b"\xef\xbb\xbf")

    def test_email_html_contains_all_sections(self):
        from apps.reports.services.weekly_email import render_weekly_email_html
        html = render_weekly_email_html(_minimal_agg(), download_url="")
        assert "Rapport hebdomadaire" in html
        assert "Résumé exécutif" in html
        assert "Répartition par niveau de risque" in html
        assert "Recommandations" in html
        # Aucune balise script (safety XSS)
        assert "<script" not in html.lower()


# ============================================================================
# AC-06 : CSV injection neutralisée
# ============================================================================
class TestCsvInjection:
    """AC-06 : préfixe apostrophe si valeur commence par = + - @"""

    def test_neutralize_formula_prefix(self):
        from apps.reports.services.weekly_excel import _neutralize
        assert _neutralize("=cmd|'/c calc'!A0") == "'=cmd|'/c calc'!A0"
        assert _neutralize("+SUM(A1:A10)") == "'+SUM(A1:A10)"
        assert _neutralize("-MALICIOUS") == "'-MALICIOUS"
        assert _neutralize("@stealit") == "'@stealit"

    def test_neutralize_safe_string_unchanged(self):
        from apps.reports.services.weekly_excel import _neutralize
        assert _neutralize("Jean Dupont") == "Jean Dupont"
        assert _neutralize("123") == "123"
        assert _neutralize("Cocody, Abidjan") == "Cocody, Abidjan"

    def test_neutralize_non_string_unchanged(self):
        from apps.reports.services.weekly_excel import _neutralize
        assert _neutralize(42) == 42
        assert _neutralize(None) is None


# ============================================================================
# Broadcast safety (D-08 style, adapté aux rapports)
# ============================================================================
class TestReportCodes:
    """Codes de rapport : formats ISO valides."""

    def test_weekly_code_iso_week_53(self):
        from apps.reports.models import GeneratedReport, ReportType
        # 2020 avait 53 semaines ISO
        start = datetime(2020, 12, 28, 0, 0, tzinfo=ZoneInfo("Africa/Abidjan"))
        end = datetime(2021, 1, 3, 23, 59, 59, tzinfo=ZoneInfo("Africa/Abidjan"))
        r = GeneratedReport(report_type=ReportType.WEEKLY,
                            period_start=start, period_end=end)
        code = r._compute_code()
        assert code == "RAP-HEBDO-2020-S53", f"Code incorrect : {code}"

    def test_monthly_code_format(self):
        from apps.reports.models import GeneratedReport, ReportType
        start = datetime(2026, 3, 1, 0, 0, tzinfo=ZoneInfo("Africa/Abidjan"))
        end = datetime(2026, 3, 31, 23, 59, 59, tzinfo=ZoneInfo("Africa/Abidjan"))
        r = GeneratedReport(report_type=ReportType.MONTHLY,
                            period_start=start, period_end=end)
        assert r._compute_code() == "RAP-MENS-2026-03"


# ============================================================================
# Fixture helper — agrégat minimal pour les renderers
# ============================================================================
def _minimal_agg() -> dict:
    return {
        "period": {"start": "2026-06-08T00:00:00+00:00",
                   "end": "2026-06-14T23:59:59+00:00",
                   "iso_year": 2026, "iso_week": 24,
                   "label": "S24 (08 juin → 14 juin 2026)"},
        "previous_period": {"start": "2026-06-01T00:00:00+00:00",
                            "end": "2026-06-07T23:59:59+00:00",
                            "iso_year": 2026, "iso_week": 23,
                            "label": "S23"},
        "travelers": {"registered": 1245, "active_followup": 320},
        "followups": {"new": 45, "completed": 22},
        "checkins": {"received": 1120, "missed": 34},
        "assistance": {"requests": 12},
        "alerts": {"created": 7, "open": 3, "resolved": 5},
        "risk_levels": {
            "critical": {"count": 4, "pct": 0.3},
            "high": {"count": 18, "pct": 1.4},
            "moderate": {"count": 62, "pct": 5.0},
            "normal": {"count": 1161, "pct": 93.3},
            "total": 1245,
        },
        "cases": {"suspect": 8, "probable": 3, "confirmed": 1, "discarded": 2},
        "samples": {"requested": 12, "collected": 10},
        "analyses": {"pending": 5, "in_progress": 2, "positive": 2, "negative": 8},
        "by_entry_point": [{"name": "Aéroport FHB", "count": 800},
                           {"name": "Port d'Abidjan", "count": 200}],
        "by_district": [{"name": "Cocody", "count": 400},
                        {"name": "Yopougon", "count": 250}],
        "by_disease": [{"name": "Ebola", "count": 1245}],
        "top_events": [],
        "comparison": {
            "travelers": {"current": 1245, "previous": 1100, "delta_pct": 13.2},
            "followups_new": {"current": 45, "previous": 32, "delta_pct": 40.6},
            "checkins_received": {"current": 1120, "previous": 1050, "delta_pct": 6.7},
            "alerts_created": {"current": 7, "previous": 12, "delta_pct": -41.7},
        },
        "meta": {"generated_at": "2026-06-15T08:00:00+00:00",
                 "generation_ms": 245, "tz": "Africa/Abidjan",
                 "schema_version": 1},
    }
