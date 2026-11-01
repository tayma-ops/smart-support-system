from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

from tickets.selectors import visible_tickets


def ticket_statistics(user):
    tickets = visible_tickets(user)
    counts = dict(tickets.order_by().values_list("status").annotate(total=Count("id")))
    avg = tickets.filter(resolved_at__isnull=False).aggregate(
        duration=Avg(
            ExpressionWrapper(
                F("resolved_at") - F("created_at"), output_field=DurationField()
            )
        )
    )["duration"]

    def group(field):
        return list(
            tickets.order_by().values(field).annotate(count=Count("id")).order_by(field)
        )

    return {
        "total": tickets.count(),
        "open": counts.get("open", 0),
        "in_progress": counts.get("in_progress", 0),
        "waiting": counts.get("waiting", 0),
        "resolved": counts.get("resolved", 0),
        "closed": counts.get("closed", 0),
        "urgent": tickets.filter(priority="urgent")
        .exclude(status__in=["closed", "resolved"])
        .count(),
        "unassigned": tickets.filter(assigned_to__isnull=True)
        .exclude(status__in=["closed", "resolved"])
        .count(),
        "average_resolution_hours": (
            round(avg.total_seconds() / 3600, 1) if avg is not None else None
        ),
        "by_status": group("status"),
        "by_priority": group("priority"),
        "by_category": group("category"),
        "daily": list(
            tickets.filter(
                created_at__date__gte=timezone.localdate() - timedelta(days=13)
            )
            .annotate(day=TruncDate("created_at"))
            .order_by("day")
            .values("day")
            .annotate(count=Count("id"))
        ),
    }
