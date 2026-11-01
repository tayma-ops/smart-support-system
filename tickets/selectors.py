from django.db.models import Case, IntegerField, Q, Value, When

from .models import Notification, Ticket


def visible_tickets(user):
    queryset = Ticket.objects.select_related("customer", "assigned_to", "department")
    if not user.is_authenticated or not user.is_active:
        return queryset.none()
    if user.is_admin:
        return queryset
    if user.role == user.Role.EMPLOYEE:
        return queryset.filter(
            Q(customer=user)
            | Q(assigned_to=user)
            | Q(assigned_to__isnull=True, department__in=user.departments.all())
        )
    return queryset.filter(customer=user)


def prioritized(queryset):
    return queryset.annotate(
        priority_rank=Case(
            When(priority="urgent", then=Value(0)),
            When(priority="high", then=Value(1)),
            When(priority="medium", then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    ).order_by("priority_rank", "created_at")


def visible_notifications(user):
    # Scope again at read time: reassignment or a role change may revoke access.
    return Notification.objects.filter(
        recipient=user, ticket__in=visible_tickets(user)
    ).select_related("ticket")
