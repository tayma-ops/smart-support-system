from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from accounts import api as auth_api, views as accounts
from core import views as core
from dashboard import views as dashboard
from tickets import views as tickets
from tickets.api import DepartmentViewSet, NotificationViewSet, TicketViewSet

router = DefaultRouter()
router.register("tickets", TicketViewSet, basename="ticket")
router.register("departments", DepartmentViewSet, basename="department")
router.register("notifications", NotificationViewSet, basename="notification")
router.register("users", auth_api.UserViewSet, basename="user")

urlpatterns = [
    path("i18n/", include("django.conf.urls.i18n")),
    path("", core.landing, name="landing"),
    path("health/", core.health, name="health"),
    path("admin/", admin.site.urls),
    path("accounts/register/", accounts.register, name="register"),
    path("accounts/login/", accounts.ThrottledLoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/profile/", accounts.profile, name="profile"),
    path(
        "accounts/password_reset/",
        accounts.ThrottledPasswordResetView.as_view(),
        name="password_reset",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    path("dashboard/", dashboard.dashboard, name="dashboard"),
    path("analytics/", dashboard.analytics, name="analytics"),
    path("tickets/", tickets.ticket_list, name="ticket_list"),
    path("tickets/new/", tickets.ticket_create, name="ticket_create"),
    path("tickets/<int:pk>/", tickets.ticket_detail, name="ticket_detail"),
    path(
        "attachments/<int:pk>/download/",
        tickets.attachment_download,
        name="attachment_download",
    ),
    path("notifications/", tickets.notifications, name="notifications"),
    path(
        "notifications/<int:pk>/read/",
        tickets.notification_read,
        name="notification_read",
    ),
    path("api/auth/register/", auth_api.RegisterView.as_view(), name="api_register"),
    path(
        "api/auth/token/", auth_api.LoginTokenView.as_view(), name="token_obtain_pair"
    ),
    path(
        "api/auth/token/refresh/", auth_api.RefreshView.as_view(), name="token_refresh"
    ),
    path("api/auth/logout/", auth_api.LogoutView.as_view(), name="api_logout"),
    path("api/auth/me/", auth_api.ProfileView.as_view(), name="api_profile"),
    path(
        "api/auth/password/change/",
        auth_api.PasswordChangeView.as_view(),
        name="api_password_change",
    ),
    path("api/dashboard/", dashboard.DashboardAPI.as_view(), name="api_dashboard"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("api/", include(router.urls)),
]
