from django.utils.translation import gettext_lazy as _
import django_filters
from django import forms
from rest_framework.filters import OrderingFilter

from .models import Ticket


class TicketFilter(django_filters.FilterSet):
    created_after = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__gte",
        label=_("Created from"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    created_before = django_filters.DateFilter(
        field_name="created_at",
        lookup_expr="date__lte",
        label=_("Created through"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from accounts.models import User

        # Choices must not reveal users outside the caller's ticket scope.
        self.filters["assigned_to"].queryset = User.objects.filter(
            pk__in=self.queryset.order_by().values("assigned_to_id")
        )
        for name, label in {
            "status": _("Status"),
            "priority": _("Priority"),
            "category": _("Category"),
            "department": _("Department"),
            "assigned_to": _("Assigned to"),
        }.items():
            self.filters[name].label = label
            self.filters[name].extra["empty_label"] = _("All")

    class Meta:
        model = Ticket
        fields = ["status", "priority", "category", "department", "assigned_to"]


class TicketOrderingFilter(OrderingFilter):
    def get_ordering(self, request, queryset, view):
        ordering = super().get_ordering(request, queryset, view)
        if not ordering:
            return ordering
        return [
            (
                ("-" if field.startswith("-") else "") + "priority_rank"
                if field.lstrip("-") == "priority"
                else field
            )
            for field in ordering
        ]
