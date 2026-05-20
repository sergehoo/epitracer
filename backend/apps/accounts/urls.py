from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .views import (
    ChangePasswordView,
    EpidemiTokenObtainPairView,
    LoginEventListView,
    MeView,
    MFADisableView,
    MFASetupView,
    MFAVerifyView,
    OrganizationViewSet,
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
    path("mfa/setup/", MFASetupView.as_view(), name="mfa_setup"),
    path("mfa/verify/", MFAVerifyView.as_view(), name="mfa_verify"),
    path("mfa/disable/", MFADisableView.as_view(), name="mfa_disable"),
    path("login-events/", LoginEventListView.as_view(), name="login_events"),
    path("", include(router.urls)),
]
