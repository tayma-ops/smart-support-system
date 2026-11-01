from django.contrib.admin.apps import AdminConfig


class SupportAdminConfig(AdminConfig):
    default_site = "core.admin.SupportAdminSite"
