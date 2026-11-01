from django.utils.translation import gettext_lazy as _
import logging
from pathlib import Path

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from .models import (
    Attachment,
    Department,
    Notification,
    Ticket,
    TicketEvent,
    TicketReply,
)
from .permissions import can_transfer
from .selectors import visible_tickets
from .validators import validate_attachment

logger = logging.getLogger(__name__)


def _require_access(actor, ticket):
    if not visible_tickets(actor).filter(pk=ticket.pk).exists():
        raise PermissionDenied(_("You cannot access this ticket."))


def _text(value, field, limit):
    value = value.strip()
    if not value or len(value) > limit:
        raise ValidationError(
            {field: _("Enter between 1 and %(limit)s characters.") % {"limit": limit}}
        )
    return value


def record_event(ticket, actor, message):
    TicketEvent.objects.create(ticket=ticket, actor=actor, message=message)
    logger.info(
        "ticket_event ticket_id=%s actor_id=%s event=%s", ticket.pk, actor.pk, message
    )


def notify(ticket, recipients, message, actor=None):
    from .tasks import enqueue_email

    for recipient in set(recipients):
        if recipient and recipient != actor and recipient.is_active:
            item = Notification.objects.create(
                ticket=ticket,
                recipient=recipient,
                message=message,
                email_status="pending" if settings.EMAIL_NOTIFICATIONS else "disabled",
            )
            if settings.EMAIL_NOTIFICATIONS:
                transaction.on_commit(lambda pk=item.pk: enqueue_email(pk))


@transaction.atomic
def create_ticket(*, actor, subject, description, department=None, attachment=None):
    if not actor.is_active:
        raise PermissionDenied
    if department and not department.is_active:
        raise ValidationError({"department": _("Select an active department.")})
    if attachment:
        validate_attachment(attachment)
    ticket = Ticket.objects.create(
        customer=actor,
        subject=_text(subject, "subject", 180),
        description=_text(description, "description", 15000),
        department=department,
    )
    record_event(ticket, actor, "Ticket created")
    notify(ticket, [actor], f"{ticket.ticket_number} was created.")
    if attachment:
        add_attachment(actor=actor, ticket=ticket, upload=attachment)
    from .tasks import enqueue_analysis

    transaction.on_commit(lambda: enqueue_analysis(ticket.pk))
    return ticket


@transaction.atomic
def add_reply(*, actor, ticket, message, is_internal_note=False):
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    _require_access(actor, ticket)
    if ticket.status == Ticket.Status.CLOSED:
        raise ValidationError(
            _(
                "Closed tickets cannot receive replies. Ask support to reopen the ticket."
            )
        )
    if is_internal_note and not actor.is_support:
        raise PermissionDenied(_("Only support staff can add internal notes."))
    reply = TicketReply.objects.create(
        ticket=ticket,
        author=actor,
        message=_text(message, "message", 15000),
        is_internal_note=is_internal_note,
    )
    ticket.updated_at = timezone.now()
    ticket.save(update_fields=["updated_at"])
    if not is_internal_note:
        notify(
            ticket,
            [ticket.customer, ticket.assigned_to],
            f"New reply on {ticket.ticket_number}.",
            actor,
        )
    return reply


@transaction.atomic
def change_status(*, actor, ticket, status):
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    _require_access(actor, ticket)
    if status not in Ticket.Status.values:
        raise ValidationError({"status": _("Select a valid status.")})
    if not actor.is_support and status != Ticket.Status.CLOSED:
        raise PermissionDenied(_("Customers may only close their tickets."))
    if ticket.status == status:
        return ticket
    transitions = {
        "open": {"in_progress", "waiting", "resolved", "closed"},
        "in_progress": {"open", "waiting", "resolved", "closed"},
        "waiting": {"open", "in_progress", "resolved", "closed"},
        "resolved": {"in_progress", "closed"},
        "closed": {"open"},
    }
    if status not in transitions[ticket.status]:
        raise ValidationError({"status": _("This status transition is not allowed.")})
    old = ticket.status
    ticket.status = status
    ticket.closed_at = timezone.now() if status == "closed" else None
    if status == "resolved":
        ticket.resolved_at = timezone.now()
    elif status not in {"resolved", "closed"}:
        ticket.resolved_at = None
    ticket.save(update_fields=["status", "closed_at", "resolved_at", "updated_at"])
    record_event(ticket, actor, f"Status: {old} → {ticket.status}")
    notify(
        ticket,
        [ticket.customer, ticket.assigned_to],
        f"{ticket.ticket_number}: {ticket.status}.",
        actor,
    )
    return ticket


@transaction.atomic
def assign_ticket(*, actor, ticket, employee):
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    _require_access(actor, ticket)
    claiming = employee == actor and ticket.assigned_to_id is None and actor.is_support
    if not claiming and not can_transfer(actor):
        raise PermissionDenied(_("You do not have permission to transfer tickets."))
    if employee:
        employee = User.objects.get(pk=employee.pk)
        if not employee.is_active or employee.role != User.Role.EMPLOYEE:
            raise ValidationError(
                {"assigned_to": _("Select an active support employee.")}
            )
        if (
            ticket.department_id
            and not employee.departments.filter(pk=ticket.department_id).exists()
        ):
            raise ValidationError(
                {"assigned_to": _("The employee must belong to this department.")}
            )
    ticket.assigned_to = employee
    ticket.save(update_fields=["assigned_to", "updated_at"])
    record_event(ticket, actor, "Assignment updated")
    notify(
        ticket,
        [ticket.customer, employee],
        f"Assignment updated for {ticket.ticket_number}.",
        actor,
    )
    return ticket


@transaction.atomic
def update_triage(*, actor, ticket, **changes):
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    _require_access(actor, ticket)
    if not actor.is_support:
        raise PermissionDenied(_("Only support staff can edit triage fields."))
    allowed = {"priority", "category", "department"}
    if set(changes) - allowed:
        raise ValidationError(
            _("Only priority, category and department can be edited here.")
        )
    for field, choices in [
        ("priority", Ticket.Priority.values),
        ("category", Ticket.Category.values),
    ]:
        if field in changes and changes[field] not in choices:
            raise ValidationError({field: _("Select a valid choice.")})
    if "department" in changes:
        if not can_transfer(actor):
            raise PermissionDenied(
                _("Transferring departments requires assignment permission.")
            )
        department = changes["department"]
        if (
            department
            and not Department.objects.filter(pk=department.pk, is_active=True).exists()
        ):
            raise ValidationError({"department": _("Select an active department.")})
        if (
            ticket.assigned_to_id
            and department
            and not ticket.assigned_to.departments.filter(pk=department.pk).exists()
        ):
            raise ValidationError(
                {
                    "department": _(
                        "Unassign this ticket before moving it to another team."
                    )
                }
            )
    for field, value in changes.items():
        setattr(ticket, field, value)
    ticket.triage_version += 1
    ticket.save(update_fields=[*changes, "triage_version", "updated_at"])
    record_event(ticket, actor, "Triage details updated")
    return ticket


@transaction.atomic
def add_attachment(*, actor, ticket, upload):
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    _require_access(actor, ticket)
    if ticket.status == "closed":
        raise ValidationError(_("Closed tickets cannot receive attachments."))
    if ticket.attachments.count() >= 10:
        raise ValidationError(_("A ticket can have at most 10 attachments."))
    validate_attachment(upload)
    return Attachment.objects.create(
        ticket=ticket,
        uploaded_by=actor,
        file=upload,
        original_name=Path(upload.name.replace("\\", "/")).name[:180],
    )


@transaction.atomic
def delete_ticket(*, actor, ticket):
    if not actor.is_admin:
        raise PermissionDenied(_("Only administrators can delete tickets."))
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)
    files = [(item.file.storage, item.file.name) for item in ticket.attachments.all()]
    ticket_id = ticket.pk
    ticket.delete()

    def cleanup_files():
        for storage, name in files:
            try:
                storage.delete(name)
            except OSError:
                logger.warning("attachment_cleanup_failed ticket_id=%s", ticket_id)

    transaction.on_commit(cleanup_files)
