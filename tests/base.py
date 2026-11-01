from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from tickets.models import Department, Ticket


class SupportTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tech = Department.objects.create(name="Technical Support")
        cls.billing = Department.objects.create(name="Billing")
        cls.customer = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="Test-pass-strong-982",
        )
        cls.other = User.objects.create_user(
            username="other", email="other@example.com", password="Test-pass-strong-982"
        )
        cls.employee = User.objects.create_user(
            username="employee",
            email="employee@example.com",
            password="Test-pass-strong-982",
            role="employee",
        )
        cls.colleague = User.objects.create_user(
            username="colleague",
            email="colleague@example.com",
            password="Test-pass-strong-982",
            role="employee",
        )
        cls.outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="Test-pass-strong-982",
            role="employee",
        )
        cls.admin = User.objects.create_user(
            username="administrator",
            email="admin@example.com",
            password="Test-pass-strong-982",
            role="admin",
        )
        cls.employee.departments.add(cls.tech)
        cls.colleague.departments.add(cls.tech)
        cls.outsider.departments.add(cls.billing)
        cls.ticket = Ticket.objects.create(
            customer=cls.customer,
            department=cls.tech,
            subject="Dashboard unavailable",
            description="Our workspace fails to load.",
            ai_status="disabled",
        )
        cls.private_ticket = Ticket.objects.create(
            customer=cls.other,
            department=cls.billing,
            subject="Private billing issue",
            description="A billing question.",
            ai_status="disabled",
        )

    def setUp(self):
        self.api = APIClient()

    def authenticate(self, user):
        self.api.force_authenticate(user)

    def ticket_url(self, suffix="", ticket=None):
        return f"/api/tickets/{(ticket or self.ticket).pk}/{suffix}"
