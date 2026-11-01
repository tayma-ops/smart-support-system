from django.test import Client
from django.utils.translation import override

from tickets.models import Notification, TicketEvent, TicketReply
from .base import SupportTestCase


class LocalizationTests(SupportTestCase):
    def test_english_remains_the_default(self):
        response = self.client.get("/accounts/login/")
        self.assertContains(response, 'lang="en"')
        self.assertContains(response, "Sign in")

    def test_language_switch_is_csrf_protected_and_persists_preference(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            client.post("/i18n/setlang/", {"language": "ar"}).status_code, 403
        )
        client.get("/accounts/login/")
        response = client.post(
            "/i18n/setlang/",
            {
                "language": "ar",
                "next": "/accounts/login/",
                "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(client.cookies["django_language"].value, "ar")
        self.assertContains(client.get("/accounts/login/"), "تسجيل الدخول")

    def test_all_application_pages_render_arabic_for_each_role(self):
        for user in [self.customer, self.employee, self.admin]:
            self.client.force_login(user)
            for path in [
                "/dashboard/",
                "/analytics/",
                "/tickets/",
                "/tickets/new/",
                self.ticket.get_absolute_url(),
                "/notifications/",
                "/accounts/profile/",
                "/accounts/password_change/",
            ]:
                with self.subTest(role=user.role, path=path):
                    response = self.client.get(path, HTTP_ACCEPT_LANGUAGE="ar")
                    self.assertEqual(response.status_code, 200)
                    self.assertContains(response, 'dir="rtl"')
                    self.assertContains(response, "مساحة العمل")

    def test_arabic_forms_choices_and_chart_labels_are_translated(self):
        self.client.force_login(self.employee)
        response = self.client.get("/tickets/new/", HTTP_ACCEPT_LANGUAGE="ar")
        self.assertContains(response, "العنوان")
        self.assertContains(response, "الدعم الفني")
        self.assertContains(response, "دع فريق الدعم يحدد القسم المناسب")
        response = self.client.get("/analytics/", HTTP_ACCEPT_LANGUAGE="ar")
        self.assertContains(response, "التذاكر حسب الحالة")
        self.assertIn(
            "مفتوحة", str(response.context["ui_strings"]["labels"]["status"]["open"])
        )

    def test_customer_text_and_internal_note_visibility_are_preserved_in_arabic(self):
        text = "An original customer sentence. مشكلة أصلية من العميل."
        self.ticket.description = text
        self.ticket.save()
        TicketReply.objects.create(
            ticket=self.ticket,
            author=self.employee,
            message="Private note marker",
            is_internal_note=True,
        )
        self.client.force_login(self.customer)
        response = self.client.get(
            self.ticket.get_absolute_url(), HTTP_ACCEPT_LANGUAGE="ar"
        )
        self.assertContains(response, text)
        self.assertNotContains(response, "Private note marker")
        self.assertNotContains(response, "المساعدة الذكية غير مهيأة")

    def test_stored_system_events_are_localized_when_read_not_when_created(self):
        event = TicketEvent.objects.create(
            ticket=self.ticket,
            actor=self.employee,
            message="Status: open → in_progress",
        )
        notification = Notification.objects.create(
            ticket=self.ticket,
            recipient=self.customer,
            message=f"{self.ticket.ticket_number} was created.",
        )
        with override("ar"):
            self.assertIn("قيد المعالجة", event.display_message)
            self.assertIn("تم إنشاء التذكرة", notification.display_message)
        with override("en"):
            self.assertIn("In progress", event.display_message)
            self.assertIn("was created", notification.display_message)

    def test_api_machine_codes_stay_stable_in_arabic(self):
        self.authenticate(self.customer)
        response = self.api.get(self.ticket_url(), HTTP_ACCEPT_LANGUAGE="ar")
        self.assertEqual(response.data["status"], "open")
        self.assertEqual(response.data["priority"], "medium")
