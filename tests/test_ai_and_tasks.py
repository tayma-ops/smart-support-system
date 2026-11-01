from datetime import timedelta
from unittest.mock import Mock, patch

from django.core import mail
from django.test import override_settings
from django.utils import timezone

from ai_service.providers import (
    Analysis,
    AnalysisUnavailable,
    AnalysisNotConfigured,
    OpenAIProvider,
    LocalModelProvider,
)
from ai_service.services import analyze_ticket
from tickets.models import Notification, Ticket, TicketReply
from tickets.tasks import dispatch_pending, enqueue_analysis, send_notification_email
from .base import SupportTestCase


class AIAndTaskTests(SupportTestCase):
    def test_generated_drafts_requesting_credentials_are_rejected(self):
        for reply in [
            "Please provide the correct password and login details.",
            "Send your OTP to our support agent.",
            "يرجى إرسال كلمة المرور الخاصة بحسابك.",
            "أرسل رمز التحقق لتأكيد الحساب.",
        ]:
            with self.subTest(reply=reply), self.assertRaises(AnalysisUnavailable):
                Analysis.from_payload(
                    {
                        "category": "account",
                        "priority": "medium",
                        "sentiment": "neutral",
                        "summary": "Account access issue",
                        "suggested_reply": reply,
                    }
                )

    def test_credential_safety_warnings_are_allowed(self):
        for reply in [
            "Never share your password with anyone.",
            "Please share the error message without including your password.",
            "لا تشارك كلمة المرور أو رمز التحقق.",
            "يرجى توضيح رسالة الخطأ دون مشاركة كلمة المرور.",
        ]:
            with self.subTest(reply=reply):
                result = Analysis.from_payload(
                    {
                        "category": "account",
                        "priority": "medium",
                        "sentiment": "neutral",
                        "summary": "Account access issue",
                        "suggested_reply": reply,
                    }
                )
                self.assertEqual(result.suggested_reply, reply)

    @override_settings(
        AI_MODEL="local-demo", AI_BASE_URL="http://127.0.0.1:8081/v1", AI_API_KEY=""
    )
    def test_local_model_adapter_validates_real_protocol_without_cloud_credentials(
        self,
    ):
        payload = {
            "category": "technical",
            "priority": "high",
            "sentiment": "neutral",
            "summary": "Summary",
            "suggested_reply": "A draft",
        }
        response = Mock()
        response.json.return_value = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": __import__("json").dumps(payload)},
                }
            ]
        }
        with patch("ai_service.providers.httpx.post", return_value=response) as request:
            result = LocalModelProvider().analyze(
                subject="A question", description="Untrusted input"
            )
        self.assertEqual(result.category, "technical")
        self.assertFalse(request.call_args.kwargs["trust_env"])
        self.assertNotIn("headers", request.call_args.kwargs)
        self.assertFalse(
            request.call_args.kwargs["json"]["chat_template_kwargs"]["enable_thinking"]
        )

    @override_settings(AI_MODEL="local-demo", AI_BASE_URL="https://example.com/v1")
    def test_keyless_local_provider_never_sends_ticket_data_to_a_remote_host(self):
        with patch("ai_service.providers.httpx.post") as request, self.assertRaises(
            AnalysisNotConfigured
        ):
            LocalModelProvider().analyze(
                subject="Private", description="Private content"
            )
        request.assert_not_called()

    @override_settings(AI_MODEL="local-demo", AI_BASE_URL="http://127.0.0.1:8081/v1")
    def test_truncated_local_generation_is_rejected(self):
        response = Mock()
        response.json.return_value = {
            "choices": [{"finish_reason": "length", "message": {"content": "{}"}}]
        }
        with patch(
            "ai_service.providers.httpx.post", return_value=response
        ), self.assertRaises(AnalysisUnavailable):
            LocalModelProvider().analyze(subject="Question", description="Details")

    @override_settings(AI_MODEL="local-demo", AI_BASE_URL="http://127.0.0.1:8081/v1")
    def test_arabic_ticket_rejects_a_local_draft_generated_in_another_language(self):
        payload = {
            "category": "account",
            "priority": "medium",
            "sentiment": "neutral",
            "summary": "مشكلة دخول",
            "suggested_reply": "Please describe the issue.",
        }
        response = Mock()
        response.json.return_value = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": __import__("json").dumps(payload)},
                }
            ]
        }
        with patch(
            "ai_service.providers.httpx.post", return_value=response
        ), self.assertRaises(AnalysisUnavailable):
            LocalModelProvider().analyze(
                subject="مشكلة الدخول", description="تعذر الدخول إلى حسابي"
            )

    def queue_ticket(self):
        Ticket.objects.filter(pk=self.ticket.pk).update(ai_status="pending")

    def test_missing_key_is_explicitly_disabled_without_fabricated_results(self):
        self.queue_ticket()
        with patch("ai_service.providers.httpx.post") as request:
            analyze_ticket(self.ticket.pk)
        request.assert_not_called()
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.ai_status, "disabled")
        self.assertEqual(self.ticket.ai_summary, "")
        self.assertEqual(self.ticket.ai_suggested_reply, "")
        self.assertFalse(TicketReply.objects.exists())

    def test_provider_result_is_saved_but_never_sent(self):
        self.queue_ticket()
        analysis = Analysis(
            "technical",
            "urgent",
            "negative",
            "Workspace outage",
            "Please share the incident time.",
        )
        with patch("ai_service.services.import_string") as factory:
            factory.return_value.return_value.analyze.return_value = analysis
            analyze_ticket(self.ticket.pk)
            analyze_ticket(self.ticket.pk)
            factory.return_value.return_value.analyze.assert_called_once()
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.ai_status, "complete")
        self.assertEqual(self.ticket.priority, "urgent")
        self.assertEqual(self.ticket.ai_suggested_reply, analysis.suggested_reply)
        self.assertFalse(TicketReply.objects.exists())

    def test_ai_cannot_overwrite_human_triage(self):
        self.queue_ticket()
        Ticket.objects.filter(pk=self.ticket.pk).update(
            priority="low", triage_version=1
        )
        with patch("ai_service.services.import_string") as factory:
            factory.return_value.return_value.analyze.return_value = Analysis(
                "technical", "urgent", "negative", "Summary", "Draft"
            )
            analyze_ticket(self.ticket.pk)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.priority, "low")
        self.assertEqual(self.ticket.ai_status, "complete")

    def test_provider_failure_does_not_break_ticket_or_log_private_content(self):
        self.queue_ticket()
        with patch("ai_service.services.import_string") as factory:
            factory.return_value.return_value.analyze.side_effect = AnalysisUnavailable(
                "SECRET CUSTOMER CONTENT"
            )
            with self.assertLogs("ai_service.services", level="WARNING") as captured:
                analyze_ticket(self.ticket.pk)
        self.assertNotIn("SECRET", " ".join(captured.output))
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.ai_status, "failed")
        self.assertEqual(self.ticket.status, "open")

    def test_invalid_provider_output_is_rejected(self):
        for payload in [
            {},
            {
                "category": "technical",
                "priority": "invalid",
                "sentiment": "negative",
                "summary": "S",
                "suggested_reply": "R",
            },
            {
                "category": "technical",
                "priority": "low",
                "sentiment": "negative",
                "summary": "S" * 1201,
                "suggested_reply": "R",
            },
        ]:
            with self.assertRaises(AnalysisUnavailable):
                Analysis.from_payload(payload)

    @override_settings(AI_API_KEY="test-not-a-real-key", AI_MODEL="test-model")
    def test_responses_adapter_contract_with_mock_transport(self):
        payload = {
            "category": "technical",
            "priority": "high",
            "sentiment": "neutral",
            "summary": "Summary",
            "suggested_reply": "A draft",
        }
        response = Mock()
        response.json.return_value = {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": __import__("json").dumps(payload),
                        }
                    ],
                }
            ],
        }
        with patch("ai_service.providers.httpx.post", return_value=response) as request:
            analysis = OpenAIProvider().analyze(
                subject="Question", description="Untrusted input"
            )
        self.assertEqual(analysis.priority, "high")
        params = request.call_args.kwargs["json"]
        self.assertFalse(params["store"])
        self.assertTrue(params["text"]["format"]["strict"])
        self.assertNotIn("email", params)

    def test_active_analysis_lease_prevents_duplicate_calls(self):
        Ticket.objects.filter(pk=self.ticket.pk).update(
            ai_status="processing", ai_started_at=timezone.now()
        )
        with patch("ai_service.services.import_string") as factory:
            analyze_ticket(self.ticket.pk)
        factory.assert_not_called()

    def test_broker_outage_preserves_pending_work_for_recovery(self):
        self.queue_ticket()
        with patch(
            "tickets.tasks.analyze_ticket_task.delay",
            side_effect=ConnectionError("unavailable"),
        ):
            enqueue_analysis(self.ticket.pk)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.ai_status, "pending")
        with patch("tickets.tasks.enqueue_analysis") as enqueue:
            dispatch_pending()
        enqueue.assert_called_once_with(self.ticket.pk)

    def test_stale_worker_lease_is_redispatched(self):
        Ticket.objects.filter(pk=self.ticket.pk).update(
            ai_status="processing", ai_started_at=timezone.now() - timedelta(minutes=6)
        )
        with patch("tickets.tasks.enqueue_analysis") as enqueue:
            dispatch_pending()
        enqueue.assert_called_once_with(self.ticket.pk)

    @override_settings(EMAIL_NOTIFICATIONS=True)
    def test_email_notification_sends_once_without_customer_body(self):
        notification = Notification.objects.create(
            recipient=self.customer, ticket=self.ticket, message="Private issue body"
        )
        send_notification_email(notification.pk)
        send_notification_email(notification.pk)
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("Private issue body", mail.outbox[0].body)
        notification.refresh_from_db()
        self.assertEqual(notification.email_status, "sent")

    @override_settings(EMAIL_NOTIFICATIONS=True)
    def test_email_is_not_sent_after_access_is_revoked(self):
        notification = Notification.objects.create(
            recipient=self.employee, ticket=self.ticket, message="Assigned"
        )
        self.ticket.assigned_to = self.colleague
        self.ticket.save()
        send_notification_email(notification.pk)
        self.assertEqual(len(mail.outbox), 0)
        notification.refresh_from_db()
        self.assertEqual(notification.email_status, "disabled")
