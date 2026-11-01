import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Notification, Ticket
from .selectors import visible_tickets

logger = logging.getLogger(__name__)


def _enqueue(task, pk):
    try:
        task.delay(pk)
    except Exception:
        # The DB row is a durable outbox. Beat or retry_pending recovers broker outages.
        logger.warning("task_dispatch_deferred task=%s object_id=%s", task.name, pk)


def enqueue_analysis(ticket_id):
    _enqueue(analyze_ticket_task, ticket_id)


def enqueue_email(notification_id):
    _enqueue(send_notification_email, notification_id)


@shared_task(name="tickets.tasks.analyze_ticket")
def analyze_ticket_task(ticket_id):
    from ai_service.services import analyze_ticket

    analyze_ticket(ticket_id)


@shared_task(name="tickets.tasks.send_notification_email")
def send_notification_email(notification_id):
    now = timezone.now()
    with transaction.atomic():
        item = (
            Notification.objects.select_for_update().filter(pk=notification_id).first()
        )
        if item is None or item.email_status in {"sent", "disabled", "failed"}:
            return
        if (
            item.email_status == "sending"
            and item.email_started_at
            and item.email_started_at > now - timedelta(minutes=5)
        ):
            return
        if (
            not settings.EMAIL_NOTIFICATIONS
            or not visible_tickets(item.recipient).filter(pk=item.ticket_id).exists()
        ):
            item.email_status = "disabled"
            item.save(update_fields=["email_status"])
            return
        item.email_status = "sending"
        item.email_started_at = now
        item.save(update_fields=["email_status", "email_started_at"])
        email = item.recipient.email
    try:
        # Generic body avoids leaking customer content into inboxes or console logs.
        send_mail(
            "Smart Support Desk: ticket update",
            "A support ticket was updated. Sign in to your support desk to view it.",
            settings.DEFAULT_FROM_EMAIL,
            [email],
        )
    except Exception:
        Notification.objects.filter(pk=notification_id, email_started_at=now).update(
            email_status="failed"
        )
        logger.warning("notification_email_failed notification_id=%s", notification_id)
    else:
        Notification.objects.filter(pk=notification_id, email_started_at=now).update(
            email_status="sent"
        )


@shared_task(name="tickets.tasks.dispatch_pending")
def dispatch_pending():
    stale = timezone.now() - timedelta(minutes=5)
    for pk in (
        Ticket.objects.filter(
            Q(ai_status="pending") | Q(ai_status="processing", ai_started_at__lt=stale)
        )
        .order_by("created_at")
        .values_list("pk", flat=True)[:100]
    ):
        enqueue_analysis(pk)
    if settings.EMAIL_NOTIFICATIONS:
        for pk in (
            Notification.objects.filter(
                Q(email_status="pending")
                | Q(email_status="sending", email_started_at__lt=stale)
            )
            .order_by("created_at")
            .values_list("pk", flat=True)[:100]
        ):
            enqueue_email(pk)
