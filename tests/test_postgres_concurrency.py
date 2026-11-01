from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest import skipUnless
from unittest.mock import patch

from django.core.exceptions import PermissionDenied
from django.db import connection, connections
from django.test import TransactionTestCase

from accounts.models import User
from ai_service.providers import Analysis
from ai_service.services import analyze_ticket
from tickets.models import Department, Ticket, TicketEvent
from tickets.services import assign_ticket


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
class PostgreSQLConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Concurrency team")
        self.customer = User.objects.create_user(
            username="concurrency_customer",
            email="concurrency_customer@example.invalid",
        )
        self.employees = []
        for index in range(2):
            employee = User.objects.create_user(
                username=f"concurrency_employee_{index}",
                email=f"employee{index}@example.invalid",
                role="employee",
            )
            employee.departments.add(self.department)
            self.employees.append(employee)
        self.ticket = Ticket.objects.create(
            customer=self.customer,
            department=self.department,
            subject="Concurrent assignment",
            description="Synthetic locking test",
        )

    def test_two_employees_cannot_both_claim_the_same_ticket(self):
        barrier = Barrier(2)

        def claim(user_id):
            try:
                actor = User.objects.get(pk=user_id)
                ticket = Ticket.objects.get(pk=self.ticket.pk)
                barrier.wait(timeout=5)
                try:
                    assign_ticket(actor=actor, ticket=ticket, employee=actor)
                    return "assigned"
                except PermissionDenied:
                    return "denied"
            finally:
                connections["default"].close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(claim, [user.pk for user in self.employees]))
        self.assertCountEqual(results, ["assigned", "denied"])
        self.ticket.refresh_from_db()
        self.assertIn(self.ticket.assigned_to_id, [user.pk for user in self.employees])
        self.assertEqual(
            TicketEvent.objects.filter(
                ticket=self.ticket, message="Assignment updated"
            ).count(),
            1,
        )

    def test_concurrent_analysis_uses_a_single_provider_call(self):
        started, release = Event(), Event()

        def provide(**kwargs):
            started.set()
            if not release.wait(timeout=5):
                raise RuntimeError("Test provider wait timed out")
            return Analysis(
                "technical", "high", "neutral", "Synthetic summary", "Synthetic draft"
            )

        def run_analysis():
            try:
                analyze_ticket(self.ticket.pk)
            finally:
                connections["default"].close()

        with patch("ai_service.services.import_string") as factory, ThreadPoolExecutor(
            max_workers=2
        ) as pool:
            provider = factory.return_value.return_value
            provider.analyze.side_effect = provide
            first = pool.submit(run_analysis)
            try:
                self.assertTrue(started.wait(timeout=5))
                second = pool.submit(run_analysis)
                second.result(timeout=5)
            finally:
                release.set()
            first.result(timeout=5)
            provider.analyze.assert_called_once()
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.ai_status, "complete")
