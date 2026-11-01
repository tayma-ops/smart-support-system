from io import StringIO

from django.core.management import call_command
from django.test import override_settings

from accounts.models import User
from tickets.models import Ticket
from .base import SupportTestCase


class PageTests(SupportTestCase):
    def test_arabic_browser_language_enables_translated_rtl_interface(self):
        response = self.client.get("/accounts/login/", HTTP_ACCEPT_LANGUAGE="ar")
        self.assertContains(response, 'lang="ar"')
        self.assertContains(response, 'dir="rtl"')
        self.assertContains(response, "تسجيل الدخول")

    def test_public_pages_render(self):
        for url in [
            "/",
            "/accounts/login/",
            "/accounts/register/",
            "/accounts/password_reset/",
            "/admin/login/",
            "/api/docs/",
            "/api/schema/",
            "/health/",
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_authenticated_pages_render_for_all_roles(self):
        for user in [self.customer, self.employee, self.admin]:
            self.client.force_login(user)
            for url in [
                "/dashboard/",
                "/analytics/",
                "/tickets/",
                "/tickets/new/",
                self.ticket.get_absolute_url(),
                "/notifications/",
                "/accounts/profile/",
                "/accounts/password_change/",
            ]:
                with self.subTest(role=user.role, url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_workspace_and_employee_boundary(self):
        self.client.force_login(self.admin)
        for url in [
            "/admin/",
            "/admin/accounts/user/",
            "/admin/tickets/department/",
            "/admin/tickets/ticket/",
        ]:
            self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.employee)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    @override_settings(DEBUG=False)
    def test_custom_404_does_not_expose_traceback(self):
        response = self.client.get("/missing-page/")
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "A small detour", status_code=404)
        self.assertNotContains(response, "Traceback", status_code=404)

    @override_settings(DEBUG=True)
    def test_demo_seeding_is_idempotent_and_does_not_fabricate_ai(self):
        output = StringIO()
        call_command("seed_demo", stdout=output)
        count = Ticket.objects.count()
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Ticket.objects.count(), count)
        self.assertFalse(Ticket.objects.exclude(ai_summary="").exists())
        self.assertEqual(User.objects.get(username="demo_customer").role, "customer")
        self.assertIn("DEMO ONLY", output.getvalue())
