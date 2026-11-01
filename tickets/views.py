from django.utils.translation import gettext_lazy as _
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST
from drf_spectacular.utils import extend_schema, OpenApiTypes
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication

from . import services
from .filters import TicketFilter
from .forms import (
    AssignmentForm,
    AttachmentForm,
    ReplyForm,
    StatusForm,
    TicketForm,
    TriageForm,
)
from .models import Attachment, Department, Ticket
from .permissions import can_claim, can_transfer
from .selectors import prioritized, visible_notifications, visible_tickets


def _form_error(form, exc):
    form.add_error(None, " ".join(exc.messages))


@login_required
def ticket_list(request):
    queryset = visible_tickets(request.user)
    query = request.GET.get("search", "").strip()
    if query:
        from django.db.models import Q

        queryset = queryset.filter(
            Q(ticket_number__icontains=query) | Q(subject__icontains=query)
        )
    filters = TicketFilter(request.GET, queryset=queryset)
    queryset = filters.qs
    ordering = request.GET.get("ordering", "-created_at")
    if ordering == "priority":
        queryset = prioritized(queryset)
    else:
        queryset = queryset.order_by(
            ordering
            if ordering in {"created_at", "-created_at", "updated_at", "-updated_at"}
            else "-created_at"
        )
    params = request.GET.copy()
    params.pop("page", None)
    return render(
        request,
        "tickets/list.html",
        {
            "page_obj": Paginator(queryset, 15).get_page(request.GET.get("page")),
            "filter": filters,
            "search": query,
            "query_params": params.urlencode(),
            "statuses": Ticket.Status.choices,
            "priorities": Ticket.Priority.choices,
            "categories": Ticket.Category.choices,
            "departments": Department.objects.filter(is_active=True),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def ticket_create(request):
    form = TicketForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            ticket = services.create_ticket(actor=request.user, **form.cleaned_data)
        except ValidationError as exc:
            _form_error(form, exc)
        else:
            messages.success(request, _("Your ticket is in. We’ll take it from here."))
            return redirect(ticket)
    return render(request, "tickets/create.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def ticket_detail(request, pk):
    ticket = get_object_or_404(visible_tickets(request.user), pk=pk)
    forms = {
        "reply": ReplyForm(user=request.user),
        "status": StatusForm(initial={"status": ticket.status}),
        "assign": AssignmentForm(
            ticket=ticket, initial={"assigned_to": ticket.assigned_to_id}
        ),
        "triage": TriageForm(
            initial={"priority": ticket.priority, "category": ticket.category}
        ),
        "attachment": AttachmentForm(),
    }
    if request.method == "POST":
        action = request.POST.get("action")
        if action in {"assign", "triage", "claim"} and not request.user.is_support:
            raise PermissionDenied
        if action == "assign" and not can_transfer(request.user):
            raise PermissionDenied(_("Use Assign to me to claim an available ticket."))
        if action == "claim":
            if not can_claim(request.user, ticket):
                raise PermissionDenied
            try:
                services.assign_ticket(
                    actor=request.user, ticket=ticket, employee=request.user
                )
            except ValidationError as exc:
                # Membership can change between rendering and the locked write.
                messages.error(request, " ".join(exc.messages))
            else:
                messages.success(request, _("Ticket updated."))
            return redirect(ticket)
        if action == "close":
            services.change_status(actor=request.user, ticket=ticket, status="closed")
            return redirect(ticket)
        if action not in forms:
            raise Http404
        kwargs = (
            {"user": request.user}
            if action == "reply"
            else {"ticket": ticket} if action == "assign" else {}
        )
        form = type(forms[action])(request.POST, request.FILES, **kwargs)
        forms[action] = form
        if form.is_valid():
            try:
                if action == "reply":
                    services.add_reply(
                        actor=request.user, ticket=ticket, **form.cleaned_data
                    )
                elif action == "status":
                    services.change_status(
                        actor=request.user, ticket=ticket, **form.cleaned_data
                    )
                elif action == "assign":
                    services.assign_ticket(
                        actor=request.user,
                        ticket=ticket,
                        employee=form.cleaned_data["assigned_to"],
                    )
                elif action == "triage":
                    services.update_triage(
                        actor=request.user, ticket=ticket, **form.cleaned_data
                    )
                elif action == "attachment":
                    services.add_attachment(
                        actor=request.user,
                        ticket=ticket,
                        upload=form.cleaned_data["file"],
                    )
            except ValidationError as exc:
                _form_error(form, exc)
            else:
                messages.success(request, _("Ticket updated."))
                return redirect(
                    ticket
                    if visible_tickets(request.user).filter(pk=pk).exists()
                    else "ticket_list"
                )
    replies = ticket.replies.select_related("author")
    if not request.user.is_support:
        replies = replies.filter(is_internal_note=False)
    return render(
        request,
        "tickets/detail.html",
        {
            "ticket": ticket,
            "replies": replies,
            "can_transfer": can_transfer(request.user),
            "can_claim": can_claim(request.user, ticket),
            **{f"{name}_form": form for name, form in forms.items()},
        },
    )


@extend_schema(responses={(200, "application/octet-stream"): OpenApiTypes.BINARY})
@api_view(["GET"])
@authentication_classes([JWTAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def attachment_download(request, pk):
    item = get_object_or_404(
        Attachment.objects.filter(ticket__in=visible_tickets(request.user)), pk=pk
    )
    try:
        response = FileResponse(
            item.file.open("rb"),
            as_attachment=True,
            filename=item.original_name,
            content_type="application/octet-stream",
        )
    except FileNotFoundError:
        raise Http404("This attachment is no longer available.") from None
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
def notifications(request):
    return render(
        request,
        "tickets/notifications.html",
        {
            "page_obj": Paginator(visible_notifications(request.user), 20).get_page(
                request.GET.get("page")
            )
        },
    )


@login_required
@require_POST
def notification_read(request, pk):
    item = get_object_or_404(visible_notifications(request.user), pk=pk)
    item.is_read = True
    item.save(update_fields=["is_read"])
    return redirect(item.ticket)
