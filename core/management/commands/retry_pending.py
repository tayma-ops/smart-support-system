from django.core.management.base import BaseCommand

from tickets.models import Notification, Ticket
from tickets.tasks import dispatch_pending


class Command(BaseCommand):
    help = "Dispatch pending work; optionally reset failed/disabled analysis after fixing provider settings."

    def add_arguments(self, parser):
        parser.add_argument("--retry-failed", action="store_true")

    def handle(self, *args, **options):
        if options["retry_failed"]:
            Ticket.objects.filter(ai_status__in=["failed", "disabled"]).update(
                ai_status="pending"
            )
            Notification.objects.filter(email_status="failed").update(
                email_status="pending"
            )
        dispatch_pending()
        self.stdout.write(
            "Pending work dispatched. In asynchronous mode, a running worker is required."
        )
