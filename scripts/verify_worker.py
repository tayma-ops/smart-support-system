"""Development integration check for PostgreSQL, a real broker and a real worker."""

import os
import time
import uuid
from pathlib import Path
import sys
import argparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()

from django.conf import settings
from django.db import connection
from accounts.models import User
from tickets.models import Ticket
from tickets.services import create_ticket

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--check-email",
    action="store_true",
    help="Also wait for the worker to deliver an email through its configured backend",
)
parser.add_argument(
    "--expect-analysis",
    action="store_true",
    help="Test the configured real AI model; a cloud provider may incur its usual cost",
)
args = parser.parse_args()

if (
    not settings.DEBUG
    or settings.CELERY_TASK_ALWAYS_EAGER
    or connection.vendor != "postgresql"
):
    raise SystemExit(
        "Requires PostgreSQL, DEBUG=True and eager=False. Use an isolated development database."
    )
if not args.expect_analysis and (
    settings.AI_API_KEY or settings.AI_PROVIDER != "ai_service.providers.OpenAIProvider"
):
    raise SystemExit(
        "The no-key check requires OpenAIProvider without an API key. Use --expect-analysis for a configured model."
    )
if args.expect_analysis and not settings.AI_MODEL:
    raise SystemExit("Configure AI_MODEL before testing real analysis.")

identifier = uuid.uuid4().hex
user = User.objects.create_user(
    username=f"worker_check_{identifier[:12]}", email=f"{identifier}@example.invalid"
)
ticket = create_ticket(
    actor=user,
    subject="[Integration] Production API unavailable",
    description="All customers receive HTTP 503 errors from our production API. No orders can be processed. This is a complete service outage.",
)
try:
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        ticket.refresh_from_db()
        email_ready = (
            not args.check_email
            or ticket.notifications.filter(email_status="sent").exists()
        )
        if ticket.ai_status == "failed":
            raise SystemExit(
                "The worker ran but AI analysis failed. Inspect provider configuration."
            )
        if (
            ticket.ai_status == ("complete" if args.expect_analysis else "disabled")
            and email_ready
        ):
            if args.expect_analysis:
                assert (
                    ticket.ai_summary and ticket.ai_suggested_reply and ticket.sentiment
                )
                assert (
                    not ticket.replies.exists()
                ), "AI must never send an automatic reply"
                print(
                    f"PASS: real AI via PostgreSQL -> Redis -> Celery ({ticket.category}, {ticket.priority}); no reply was sent"
                )
            else:
                print(
                    "PASS: PostgreSQL -> Redis -> Celery -> explicit AI-disabled status"
                )
            if args.check_email:
                print(
                    "PASS: Celery notification delivered through the configured email backend"
                )
            break
        time.sleep(0.25)
    else:
        raise SystemExit(
            f"Worker did not process the ticket within 60 seconds (status={ticket.ai_status})."
        )
finally:
    Ticket.objects.filter(pk=ticket.pk).delete()
    user.delete()
