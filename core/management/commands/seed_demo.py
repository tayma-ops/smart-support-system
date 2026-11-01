import secrets
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from tickets.models import Department, Ticket, TicketEvent, TicketReply


class Command(BaseCommand):
    help = "Create clearly labeled synthetic demo records in development only. Existing records are preserved."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "Demo seeding requires DEBUG=True. Never seed a production database."
            )
        departments = {}
        for name in [
            "Technical Support",
            "Billing",
            "Sales",
            "Account Support",
            "General Support",
        ]:
            departments[name], _ = Department.objects.get_or_create(name=name)
        users = {}
        for username, first_name, last_name, role in [
            ("demo_customer", "Alex", "Morgan", "customer"),
            ("demo_customer_two", "Jordan", "Lee", "customer"),
            ("demo_employee", "Sam", "Taylor", "employee"),
            ("demo_admin", "Morgan", "Reed", "admin"),
        ]:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": f"{username}@example.invalid",
                    "role": role,
                },
            )
            if created:
                password = secrets.token_urlsafe(16)
                user.set_password(password)
                user.save()
                self.stdout.write(
                    f"DEMO ONLY · {username} · temporary password: {password}"
                )
            else:
                self.stdout.write(f"Preserved existing demo account: {username}")
            users[username] = user
        employee = users["demo_employee"]
        employee.departments.add(*departments.values())
        from django.contrib.auth.models import Permission

        employee.user_permissions.add(
            Permission.objects.get(
                codename="assign_ticket", content_type__app_label="tickets"
            )
        )
        samples = [
            (
                "Unable to sign in after password reset",
                "Account Support",
                "account",
                "high",
                "in_progress",
            ),
            (
                "Invoice includes a duplicate charge",
                "Billing",
                "billing",
                "high",
                "open",
            ),
            (
                "Production dashboard is unavailable",
                "Technical Support",
                "technical",
                "urgent",
                "in_progress",
            ),
            (
                "How do I invite a new team member?",
                "General Support",
                "general",
                "low",
                "resolved",
            ),
            (
                "Exported report has missing columns",
                "Technical Support",
                "technical",
                "medium",
                "waiting",
            ),
            ("Updating the billing contact", "Billing", "billing", "low", "closed"),
            (
                "Webhook deliveries are delayed",
                "Technical Support",
                "delivery",
                "high",
                "open",
            ),
            ("A question about the enterprise plan", "Sales", "general", "low", "open"),
            (
                "Two-factor authentication recovery",
                "Account Support",
                "account",
                "medium",
                "resolved",
            ),
            (
                "Search results are taking too long",
                "Technical Support",
                "technical",
                "medium",
                "in_progress",
            ),
            (
                "Please explain this month’s usage",
                "Billing",
                "billing",
                "medium",
                "waiting",
            ),
            (
                "Thank you for helping with the migration",
                "General Support",
                "general",
                "low",
                "closed",
            ),
        ]
        for index, (subject, department, category, priority, status) in enumerate(
            samples
        ):
            customer = (
                users["demo_customer_two"] if index % 4 == 3 else users["demo_customer"]
            )
            ticket, created = Ticket.objects.get_or_create(
                subject=f"[Demo] {subject}",
                customer=customer,
                defaults={
                    "description": f"This is a synthetic demo support request: {subject}.\n\nWe noticed this while testing our workspace. Please help us understand the next steps. No real customer information is included.",
                    "department": departments[department],
                    "assigned_to": employee if index % 3 != 1 else None,
                    "category": category,
                    "priority": priority,
                    "status": status,
                    "ai_status": "disabled",
                    "triage_version": 1,
                },
            )
            if not created:
                continue
            created_at = timezone.now() - timedelta(days=index % 12, hours=index + 1)
            Ticket.objects.filter(pk=ticket.pk).update(
                created_at=created_at,
                updated_at=created_at + timedelta(hours=1),
                resolved_at=(
                    created_at + timedelta(hours=2)
                    if status in {"resolved", "closed"}
                    else None
                ),
                closed_at=(
                    created_at + timedelta(hours=3) if status == "closed" else None
                ),
            )
            TicketEvent.objects.create(
                ticket=ticket, actor=customer, message="Synthetic demo ticket created"
            )
            if status != "open":
                TicketReply.objects.create(
                    ticket=ticket,
                    author=employee,
                    message="Thanks for the details. I’m looking into this and will share the next steps here.",
                )
        self.stdout.write(
            self.style.SUCCESS(
                "Demo data is ready. All sample tickets are labeled [Demo]. No AI results were fabricated."
            )
        )
