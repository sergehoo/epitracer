"""URLs de l'API mobile EpiTrace.

Branchées sous /api/mobile/ dans config/urls.py.

Endpoints livrés Phase 2 :
    POST /api/mobile/auth/login/                  (alias → apps.accounts.EpidemiTokenObtainPairView)
    POST /api/mobile/auth/refresh/                (TokenRefreshView)
    POST /api/mobile/auth/otp/resend/             (MobileOtpResendView)
    GET  /api/mobile/profile/
    GET  /api/mobile/passes/
    GET  /api/mobile/passes/<id>/
    GET  /api/mobile/vaccinations/                + POST/PATCH/DELETE
    GET  /api/mobile/followups/
    POST /api/mobile/checkins/
    POST /api/mobile/location/share/
    GET  /api/mobile/notifications/
    POST /api/mobile/push/register/
    POST /api/mobile/assistance/request/
    POST /api/mobile/qr/import/
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from apps.accounts.views import EpidemiTokenObtainPairView

from .views import (
    MobileAssistanceRequestView, MobileCheckinCreateView,
    MobileFollowupSummaryView, MobileLocationShareView,
    MobileNotificationsListView, MobileOtpResendView,
    MobilePassesViewSet, MobileProfileView, MobilePushRegisterView,
    MobileQrImportView, MobileVaccinationsViewSet,
)
from .voyageur_auth import VoyageurRequestOtpView, VoyageurVerifyOtpView
from .registration import (
    ActiveFormsListView,
    MobileFormSchemaView,
    MobileFormSubmissionView,
)

router = DefaultRouter()
router.register("passes", MobilePassesViewSet, basename="mobile-pass")
router.register("vaccinations", MobileVaccinationsViewSet, basename="mobile-vaccination")

urlpatterns = [
    # ── Auth agents INHP (email + password + MFA) ────────────────────
    path("auth/login/", EpidemiTokenObtainPairView.as_view(), name="mobile-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="mobile-refresh"),
    path("auth/otp/resend/", MobileOtpResendView.as_view(), name="mobile-otp-resend"),

    # ── Auth voyageurs (passport/phone + OTP SMS) ────────────────────
    path("auth/voyageur/request-otp/",
         VoyageurRequestOtpView.as_view(), name="mobile-voyageur-request-otp"),
    path("auth/voyageur/verify-otp/",
         VoyageurVerifyOtpView.as_view(), name="mobile-voyageur-verify-otp"),

    # ── Enregistrement voyageur (liste formulaires actifs, public) ────
    path("registration/forms/",
         ActiveFormsListView.as_view(), name="mobile-registration-forms"),

    # ── Phase 8B — Schéma complet + soumission native mobile ─────────
    # GET  /api/mobile/forms/<code>/schema/        → DynamicFormSerializer
    # POST /api/mobile/forms/<code>/submissions/   → délivre traveler+pass
    path("forms/<slug:code>/schema/",
         MobileFormSchemaView.as_view(), name="mobile-form-schema"),
    path("forms/<slug:code>/submissions/",
         MobileFormSubmissionView.as_view(), name="mobile-form-submission"),

    # ── Profil ────────────────────────────────────────────────────────
    path("profile/", MobileProfileView.as_view(), name="mobile-profile"),

    # ── Suivi 21j ─────────────────────────────────────────────────────
    path("followups/", MobileFollowupSummaryView.as_view(), name="mobile-followup-summary"),
    path("checkins/", MobileCheckinCreateView.as_view(), name="mobile-checkin-create"),

    # ── Position volontaire ───────────────────────────────────────────
    path("location/share/", MobileLocationShareView.as_view(), name="mobile-location-share"),

    # ── Notifications + Push ──────────────────────────────────────────
    path("notifications/", MobileNotificationsListView.as_view(), name="mobile-notifications"),
    path("push/register/", MobilePushRegisterView.as_view(), name="mobile-push-register"),

    # ── Assistance ────────────────────────────────────────────────────
    path("assistance/request/", MobileAssistanceRequestView.as_view(), name="mobile-assistance"),

    # ── QR import wallet ──────────────────────────────────────────────
    path("qr/import/", MobileQrImportView.as_view(), name="mobile-qr-import"),

    # ── Router ViewSets (passes, vaccinations) ────────────────────────
    path("", include(router.urls)),
]
