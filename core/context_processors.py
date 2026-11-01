from tickets.selectors import visible_notifications
from tickets.models import Ticket
from django.utils.translation import gettext as _


def workspace(request):
    context = {
        "ui_strings": {
            "labels": {
                "status": dict(Ticket.Status.choices),
                "priority": dict(Ticket.Priority.choices),
                "category": dict(Ticket.Category.choices),
            },
            "replace_draft": _("Replace your current draft with the AI suggestion?"),
        }
    }
    if not request.user.is_authenticated:
        return context
    context["unread_notifications"] = (
        visible_notifications(request.user).filter(is_read=False).count()
    )
    return context
