from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SupportUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Support workspace", {"fields": ("role", "departments")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Support workspace", {"fields": ("email", "role", "departments")}),
    )
    list_display = ["username", "email", "role", "is_active"]
    list_filter = ["role", "is_active", "departments"]

    def has_module_permission(self, request):
        return request.user.is_active and getattr(request.user, "is_admin", False)

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)
