import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.module_loading import import_string

from tickets.models import Ticket
from .providers import AnalysisNotConfigured, AnalysisUnavailable

logger = logging.getLogger(__name__)


def analyze_ticket(ticket_id):
    now = timezone.now()
    # A DB lease prevents duplicate workers. Expired leases are recovered after crashes.
    with transaction.atomic():
        ticket = Ticket.objects.select_for_update().filter(pk=ticket_id).first()
        if ticket is None or ticket.ai_status in {"complete", "disabled", "failed"}:
            return
        if (
            ticket.ai_status == "processing"
            and ticket.ai_started_at
            and ticket.ai_started_at > now - timedelta(minutes=5)
        ):
            return
        ticket.ai_status = "processing"
        ticket.ai_started_at = now
        ticket.save(update_fields=["ai_status", "ai_started_at"])
        subject, description = ticket.subject, ticket.description
    try:
        provider = import_string(settings.AI_PROVIDER)()
        analysis = provider.analyze(subject=subject, description=description)
    except AnalysisNotConfigured:
        Ticket.objects.filter(pk=ticket_id, ai_started_at=now).update(
            ai_status="disabled"
        )
        return
    except AnalysisUnavailable:
        Ticket.objects.filter(pk=ticket_id, ai_started_at=now).update(
            ai_status="failed"
        )
        logger.warning("ai_analysis_failed ticket_id=%s", ticket_id)
        return
    except Exception:
        # Provider plugins can throw arbitrary exceptions. Keep sensitive exception text out of logs.
        Ticket.objects.filter(pk=ticket_id, ai_started_at=now).update(
            ai_status="failed"
        )
        logger.error("ai_provider_unexpected_failure ticket_id=%s", ticket_id)
        return
    with transaction.atomic():
        ticket = (
            Ticket.objects.select_for_update()
            .filter(pk=ticket_id, ai_started_at=now)
            .first()
        )
        if ticket is None:
            return
        ticket.ai_summary = analysis.summary
        ticket.ai_suggested_reply = analysis.suggested_reply
        ticket.sentiment = analysis.sentiment
        ticket.ai_provider = settings.AI_PROVIDER
        ticket.ai_model = settings.AI_MODEL
        ticket.ai_status = "complete"
        ticket.ai_analyzed_at = timezone.now()
        # Never overwrite triage that a staff member changed while analysis was running.
        if ticket.triage_version == 0:
            ticket.category = analysis.category
            ticket.priority = analysis.priority
        ticket.save()
    logger.info("ai_analysis_complete ticket_id=%s", ticket_id)
