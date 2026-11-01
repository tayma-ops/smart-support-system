from datetime import timedelta
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.test import Client
from django.utils import timezone
from PIL import Image

from tickets.models import Attachment, Notification, Ticket, TicketReply
from .base import SupportTestCase


class TicketTests(SupportTestCase):
    def test_employee_cannot_claim_own_ticket_in_another_department(self):
        self.private_ticket.customer = self.employee
        self.private_ticket.save()
        self.client.force_login(self.employee)
        response = self.client.get(self.private_ticket.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'value="claim"')
        response = self.client.post(
            self.private_ticket.get_absolute_url(), {"action": "claim"}
        )
        self.assertEqual(response.status_code, 403)
        self.private_ticket.refresh_from_db()
        self.assertIsNone(self.private_ticket.assigned_to_id)

    def test_eligible_employee_can_claim_from_browser(self):
        self.client.force_login(self.employee)
        self.assertContains(
            self.client.get(self.ticket.get_absolute_url()), 'value="claim"'
        )
        response = self.client.post(
            self.ticket.get_absolute_url(), {"action": "claim"}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ticket updated.")
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.assigned_to_id, self.employee.pk)

    def test_claim_membership_race_shows_validation_message_instead_of_500(self):
        self.client.force_login(self.employee)
        with patch(
            "tickets.views.services.assign_ticket",
            side_effect=ValidationError("The employee must belong to this department."),
        ):
            response = self.client.post(
                self.ticket.get_absolute_url(), {"action": "claim"}, follow=True
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "The employee must belong to this department.")
        self.ticket.refresh_from_db()
        self.assertIsNone(self.ticket.assigned_to_id)

    def test_anonymous_api_is_protected(self):
        self.assertEqual(self.api.get("/api/tickets/").status_code, 401)

    def test_creation_assigns_customer_and_enqueues_after_commit(self):
        self.authenticate(self.customer)
        with patch(
            "tickets.tasks.enqueue_analysis"
        ) as enqueue, self.captureOnCommitCallbacks(execute=True):
            response = self.api.post(
                "/api/tickets/",
                {
                    "subject": "A new issue",
                    "description": "Detailed information",
                    "department": self.tech.pk,
                    "customer": self.other.pk,
                    "priority": "urgent",
                    "status": "resolved",
                },
            )
        self.assertEqual(response.status_code, 201)
        ticket = Ticket.objects.get(pk=response.data["id"])
        self.assertEqual(ticket.customer, self.customer)
        self.assertEqual(ticket.priority, "medium")
        self.assertEqual(ticket.status, "open")
        enqueue.assert_called_once_with(ticket.pk)
        self.assertTrue(
            Notification.objects.filter(recipient=self.customer, ticket=ticket).exists()
        )

    def test_customer_cannot_read_or_mutate_another_customers_ticket(self):
        self.authenticate(self.other)
        for method, suffix, payload in [
            ("get", "", None),
            ("patch", "", {"priority": "urgent"}),
            ("delete", "", None),
            ("post", "reply/", {"message": "unauthorized"}),
            ("post", "status/", {"status": "closed"}),
            ("post", "assign/", {"assigned_to": self.employee.pk}),
        ]:
            with self.subTest(method=method, suffix=suffix):
                response = getattr(self.api, method)(
                    self.ticket_url(suffix), payload, format="json"
                )
                self.assertEqual(response.status_code, 404)

    def test_customer_list_and_dashboard_are_scoped(self):
        self.authenticate(self.customer)
        response = self.api.get("/api/tickets/")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.ticket.pk)
        self.assertEqual(self.api.get("/api/dashboard/").data["total"], 1)

    def test_employee_scope_excludes_other_teams_and_colleagues_assigned_work(self):
        self.authenticate(self.employee)
        self.assertEqual(self.api.get(self.ticket_url()).status_code, 200)
        self.assertEqual(
            self.api.get(self.ticket_url(ticket=self.private_ticket)).status_code, 404
        )
        self.ticket.assigned_to = self.colleague
        self.ticket.save()
        self.assertEqual(self.api.get(self.ticket_url()).status_code, 404)
        self.ticket.assigned_to = self.employee
        self.ticket.department = self.billing
        self.ticket.save()
        self.assertEqual(self.api.get(self.ticket_url()).status_code, 200)

    def test_customer_cannot_see_ai_or_internal_notes(self):
        self.ticket.ai_summary = "Private AI summary"
        self.ticket.ai_suggested_reply = "Private AI draft"
        self.ticket.save()
        TicketReply.objects.create(
            ticket=self.ticket,
            author=self.employee,
            message="Private staff note",
            is_internal_note=True,
        )
        TicketReply.objects.create(
            ticket=self.ticket, author=self.employee, message="Public reply"
        )
        self.authenticate(self.customer)
        response = self.api.get(self.ticket_url())
        self.assertNotIn("ai_summary", response.data)
        self.assertNotIn("events", response.data)
        self.assertEqual(len(response.data["replies"]), 1)
        self.assertEqual(response.data["replies"][0]["message"], "Public reply")
        self.client.force_login(self.customer)
        response = self.client.get(self.ticket.get_absolute_url())
        self.assertNotContains(response, "Private staff note")
        self.assertNotContains(response, "Private AI draft")

    def test_internal_note_does_not_notify_customer(self):
        self.authenticate(self.employee)
        response = self.api.post(
            self.ticket_url("reply/"),
            {"message": "Escalating internally", "is_internal_note": True},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertFalse(Notification.objects.filter(recipient=self.customer).exists())
        self.authenticate(self.customer)
        self.assertEqual(
            self.api.post(
                self.ticket_url("reply/"),
                {"message": "Trying private", "is_internal_note": True},
                format="json",
            ).status_code,
            403,
        )

    def test_reply_creates_notification_and_closed_ticket_blocks_reply(self):
        self.authenticate(self.employee)
        self.assertEqual(
            self.api.post(
                self.ticket_url("reply/"), {"message": "We are investigating"}
            ).status_code,
            201,
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.customer, ticket=self.ticket
            ).exists()
        )
        self.api.post(self.ticket_url("status/"), {"status": "closed"})
        self.assertEqual(
            self.api.post(
                self.ticket_url("reply/"), {"message": "Too late"}
            ).status_code,
            400,
        )

    def test_status_changes_set_and_clear_lifecycle_timestamps(self):
        self.authenticate(self.employee)
        for next_status in ["in_progress", "waiting", "resolved", "closed", "open"]:
            self.assertEqual(
                self.api.post(
                    self.ticket_url("status/"), {"status": next_status}
                ).status_code,
                200,
            )
            self.ticket.refresh_from_db()
            self.assertEqual(self.ticket.status, next_status)
            if next_status == "resolved":
                self.assertIsNotNone(self.ticket.resolved_at)
            if next_status == "closed":
                self.assertIsNotNone(self.ticket.closed_at)
            if next_status == "open":
                self.assertIsNone(self.ticket.resolved_at)
                self.assertIsNone(self.ticket.closed_at)

    def test_customer_may_close_but_not_resolve_or_reopen(self):
        self.authenticate(self.customer)
        self.assertEqual(
            self.api.post(
                self.ticket_url("status/"), {"status": "resolved"}
            ).status_code,
            403,
        )
        self.assertEqual(
            self.api.post(self.ticket_url("status/"), {"status": "closed"}).status_code,
            200,
        )
        self.assertEqual(
            self.api.post(self.ticket_url("status/"), {"status": "open"}).status_code,
            403,
        )

    def test_employee_can_claim_but_cannot_transfer_without_permission(self):
        self.authenticate(self.employee)
        self.assertEqual(
            self.api.post(
                self.ticket_url("assign/"), {"assigned_to": self.employee.pk}
            ).status_code,
            200,
        )
        self.assertEqual(
            self.api.post(
                self.ticket_url("assign/"), {"assigned_to": self.colleague.pk}
            ).status_code,
            403,
        )
        self.employee.user_permissions.add(
            Permission.objects.get(
                codename="assign_ticket", content_type__app_label="tickets"
            )
        )
        self.employee = type(self.employee).objects.get(pk=self.employee.pk)
        self.authenticate(self.employee)
        self.assertEqual(
            self.api.post(
                self.ticket_url("assign/"), {"assigned_to": self.colleague.pk}
            ).status_code,
            200,
        )

    def test_customer_cannot_probe_employee_ids_through_assignment_validation(self):
        self.authenticate(self.customer)
        for employee_id in [self.employee.pk, 999999]:
            self.assertEqual(
                self.api.post(
                    self.ticket_url("assign/"), {"assigned_to": employee_id}
                ).status_code,
                403,
            )

    def test_admin_assignment_rejects_wrong_team_and_inactive_employees(self):
        self.authenticate(self.admin)
        self.assertEqual(
            self.api.post(
                self.ticket_url("assign/"), {"assigned_to": self.outsider.pk}
            ).status_code,
            400,
        )
        self.employee.is_active = False
        self.employee.save()
        self.assertEqual(
            self.api.post(
                self.ticket_url("assign/"), {"assigned_to": self.employee.pk}
            ).status_code,
            400,
        )

    def test_triage_permissions_and_read_only_fields(self):
        self.authenticate(self.customer)
        self.assertEqual(
            self.api.patch(self.ticket_url(), {"priority": "urgent"}).status_code, 403
        )
        self.authenticate(self.employee)
        response = self.api.patch(
            self.ticket_url(),
            {"priority": "urgent", "category": "technical", "ai_summary": "tampered"},
        )
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.priority, "urgent")
        self.assertEqual(self.ticket.triage_version, 1)
        self.assertEqual(self.ticket.ai_summary, "")
        self.assertEqual(
            self.api.patch(
                self.ticket_url(), {"department": self.billing.pk}
            ).status_code,
            403,
        )

    def test_priority_ordering_is_semantic_instead_of_alphabetic(self):
        self.authenticate(self.admin)
        self.private_ticket.priority = "urgent"
        self.private_ticket.save()
        response = self.api.get("/api/tickets/", {"ordering": "-priority"})
        self.assertEqual(response.data["results"][0]["id"], self.private_ticket.pk)

    def test_employee_can_read_a_ticket_they_submitted(self):
        self.authenticate(self.employee)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api.post(
                "/api/tickets/",
                {
                    "subject": "My support request",
                    "description": "A request without a department",
                },
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self.api.get(f"/api/tickets/{response.data['id']}/").status_code, 200
        )

    def test_search_filter_date_and_pagination(self):
        self.authenticate(self.admin)
        response = self.api.get(
            "/api/tickets/",
            {
                "search": self.ticket.ticket_number,
                "department": self.tech.pk,
                "status": "open",
                "created_after": timezone.now().date().isoformat(),
            },
        )
        self.assertEqual(response.data["count"], 1)
        self.assertIn("next", response.data)
        self.assertEqual(response.data["results"][0]["id"], self.ticket.pk)
        self.assertEqual(
            self.api.get("/api/tickets/", {"created_after": "invalid"}).status_code, 400
        )

    def test_only_administrator_can_delete(self):
        self.authenticate(self.employee)
        self.assertEqual(self.api.delete(self.ticket_url()).status_code, 403)
        self.authenticate(self.admin)
        self.assertEqual(self.api.delete(self.ticket_url()).status_code, 204)

    def test_notification_access_is_scoped_after_reassignment(self):
        item = Notification.objects.create(
            recipient=self.employee, ticket=self.ticket, message="Assigned"
        )
        self.authenticate(self.employee)
        self.assertEqual(self.api.get("/api/notifications/").data["count"], 1)
        self.ticket.assigned_to = self.colleague
        self.ticket.save()
        self.assertEqual(self.api.get("/api/notifications/").data["count"], 0)
        self.assertEqual(
            self.api.patch(
                f"/api/notifications/{item.pk}/", {"is_read": True}
            ).status_code,
            404,
        )

    def test_department_management_is_admin_only_and_delete_archives(self):
        self.authenticate(self.customer)
        self.assertEqual(self.api.get("/api/departments/").status_code, 200)
        self.assertEqual(
            self.api.post("/api/departments/", {"name": "Unauthorized"}).status_code,
            403,
        )
        self.authenticate(self.admin)
        self.assertEqual(
            self.api.delete(f"/api/departments/{self.tech.pk}/").status_code, 204
        )
        self.tech.refresh_from_db()
        self.assertFalse(self.tech.is_active)
        self.authenticate(self.customer)
        self.assertEqual(
            self.api.post(
                "/api/tickets/",
                {
                    "subject": "Test",
                    "description": "Description",
                    "department": self.tech.pk,
                },
            ).status_code,
            400,
        )

    def test_html_employee_filter_does_not_leak_other_usernames(self):
        self.client.force_login(self.customer)
        response = self.client.get("/tickets/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.outsider.username)
        employee_choices = (
            response.context["filter"].form.fields["assigned_to"].queryset
        )
        self.assertNotIn(self.other, employee_choices)
        self.assertNotIn(self.outsider, employee_choices)

    def test_analytics_uses_actual_resolution_duration(self):
        now = timezone.now()
        Ticket.objects.filter(pk=self.ticket.pk).update(
            created_at=now - timedelta(hours=3), resolved_at=now, status="resolved"
        )
        self.authenticate(self.customer)
        data = self.api.get("/api/dashboard/").data
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["resolved"], 1)
        self.assertEqual(data["average_resolution_hours"], 3.0)

    def test_session_api_does_not_bypass_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.customer)
        self.assertEqual(
            client.post(
                "/api/tickets/", {"subject": "No token", "description": "Should fail"}
            ).status_code,
            403,
        )

    def test_xss_content_is_escaped_in_ticket_view(self):
        self.ticket.description = '<script>alert("xss")</script>'
        self.ticket.save()
        self.client.force_login(self.customer)
        response = self.client.get(self.ticket.get_absolute_url())
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, '<script>alert("xss")</script>')


class AttachmentTests(SupportTestCase):
    def image(self):
        buffer = BytesIO()
        Image.new("RGB", (5, 5)).save(buffer, format="PNG")
        return SimpleUploadedFile(
            "sample.png", buffer.getvalue(), content_type="image/png"
        )

    def test_private_download_and_upload_validation(self):
        self.authenticate(self.customer)
        response = self.api.post(
            self.ticket_url("attachments/"), {"file": self.image()}, format="multipart"
        )
        self.assertEqual(response.status_code, 201)
        download = response.data["download_url"]
        response = self.api.get(download)
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertTrue(b"".join(response.streaming_content).startswith(b"\x89PNG"))
        self.authenticate(self.other)
        self.assertEqual(self.api.get(download).status_code, 404)
        self.assertNotIn("/media/", download)

    def test_unsafe_forged_and_oversized_files_are_rejected(self):
        self.authenticate(self.customer)
        files = [
            SimpleUploadedFile("payload.html", b"<script>bad()</script>"),
            SimpleUploadedFile("fake.png", b"not an image"),
            SimpleUploadedFile("fake.pdf", b"not a PDF"),
            SimpleUploadedFile("large.pdf", b"%PDF-" + b"x" * (5 * 1024 * 1024)),
        ]
        for upload in files:
            with self.subTest(filename=upload.name):
                self.assertEqual(
                    self.api.post(
                        self.ticket_url("attachments/"),
                        {"file": upload},
                        format="multipart",
                    ).status_code,
                    400,
                )
        self.assertFalse(Attachment.objects.exists())

    def test_ticket_deletion_removes_private_file_only_after_commit(self):
        self.authenticate(self.customer)
        response = self.api.post(
            self.ticket_url("attachments/"), {"file": self.image()}, format="multipart"
        )
        item = Attachment.objects.get(pk=response.data["id"])
        storage, name = item.file.storage, item.file.name
        self.assertTrue(storage.exists(name))
        self.authenticate(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.api.delete(self.ticket_url()).status_code, 204)
            self.assertTrue(storage.exists(name))
        self.assertFalse(storage.exists(name))
