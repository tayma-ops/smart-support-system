from django.contrib import admin

from .models import (
    Attachment,
    Department,
    Notification,
    Ticket,
    TicketEvent,
    TicketReply,
)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active"]
    search_fields = ["name"]


class ReadOnlyAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Ticket)
class TicketAdmin(ReadOnlyAdmin):
    list_display = [
        "ticket_number",
        "subject",
        "status",
        "priority",
        "department",
        "assigned_to",
    ]
    list_filter = ["status", "priority", "department", "ai_status"]
    search_fields = ["ticket_number", "subject"]


for model in [TicketReply, TicketEvent, Notification, Attachment]:
    admin.site.register(model, ReadOnlyAdmin)

admin.site.site_header = "Smart Support Desk · Administration"
admin.site.site_title = "Support Desk Admin"
