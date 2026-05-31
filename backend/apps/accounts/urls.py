from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    ChangePasswordView,
    EpidemiTokenObtainPairView,
    LoginEventListView,
    MeView,
    MfaEmailDisableView,
    MfaEmailEnableView,
    MfaEmailResendView,
    MFADisableView,
    MFASetupView,
    MFAVerifyView,
    OrganizationViewSet,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RoleAssignmentViewSet,
    RoleViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("roles", RoleViewSet, basename="role")
router.register("organizations", OrganizationViewSet, basename="organization")
router.register("role-assignments", RoleAssignmentViewSet, basename="role-assignment")

urlpatterns = [
    path("login/", EpidemiTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    # MFA TOTP (legacy)
    path("mfa/setup/", MFASetupView.as_view(), name="mfa_setup"),
    path("mfa/verify/", MFAVerifyView.as_view(), name="mfa_verify"),
    path("mfa/disable/", MFADisableView.as_view(), name="mfa_disable"),
    # MFA EMAIL (nouveau — par défaut)
    path("mfa/email/enable/", MfaEmailEnableView.as_view(), name="mfa_email_enable"),
    path("mfa/email/disable/", MfaEmailDisableView.as_view(), name="mfa_email_disable"),
    path("mfa/email/resend/", MfaEmailResendView.as_view(), name="mfa_email_resend"),
    # Reset password public
    path("password-reset/request/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("login-events/", LoginEventListView.as_view(), name="login_events"),
    path("", include(router.urls)),
]
