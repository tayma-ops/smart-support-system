from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from tickets.models import Ticket
from tickets.selectors import prioritized, visible_tickets
from .selectors import ticket_statistics
from .serializers import DashboardSerializer


@login_required
def dashboard(request):
    return render(
        request,
        "dashboard/overview.html",
        {
            "stats": ticket_statistics(request.user),
            "recent_tickets": prioritized(
                visible_tickets(request.user).exclude(status__in=["resolved", "closed"])
            )[:6],
        },
    )


@login_required
def analytics(request):
    return render(
        request,
        "dashboard/analytics.html",
        {
            "stats": ticket_statistics(request.user),
            "statuses": Ticket.Status.choices,
            "priorities": Ticket.Priority.choices,
            "categories": Ticket.Category.choices,
        },
    )


class DashboardAPI(GenericAPIView):
    serializer_class = DashboardSerializer

    def get(self, request):
        return Response(self.get_serializer(ticket_statistics(request.user)).data)
