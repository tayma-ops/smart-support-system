from django.utils.translation import gettext_lazy as _
import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.urls import reverse


def ticket_number():
    return "SSD-" + uuid.uuid4().hex[:12].upper()


def attachment_path(instance, filename):
    return f"tickets/{instance.ticket_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class Department(models.Model):
    name = models.CharField(max_length=80, unique=True)
    description = models.CharField(max_length=240, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        from core.localization import department_label

        return department_label(self.name)


class Ticket(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        IN_PROGRESS = "in_progress", _("In progress")
        WAITING = "waiting", _("Waiting for customer")
        RESOLVED = "resolved", _("Resolved")
        CLOSED = "closed", _("Closed")

    class Priority(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        URGENT = "urgent", _("Urgent")

    class Category(models.TextChoices):
        TECHNICAL = "technical", _("Technical issue")
        BILLING = "billing", _("Billing")
        DELIVERY = "delivery", _("Delivery")
        ACCOUNT = "account", _("Account")
        COMPLAINT = "complaint", _("Complaint")
        GENERAL = "general", _("General inquiry")
        OTHER = "other", _("Other")

    class Sentiment(models.TextChoices):
        POSITIVE = "positive", _("Positive")
        NEUTRAL = "neutral", _("Neutral")
        NEGATIVE = "negative", _("Negative")

    class AIStatus(models.TextChoices):
        PENDING = "pending", _("Queued for analysis")
        PROCESSING = "processing", _("Analyzing")
        COMPLETE = "complete", _("Analysis ready")
        DISABLED = "disabled", _("AI not configured")
        FAILED = "failed", _("Analysis unavailable")

    ticket_number = models.CharField(
        max_length=20, unique=True, default=ticket_number, editable=False
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="tickets"
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tickets",
    )
    subject = models.CharField(max_length=180)
    description = models.TextField(max_length=15000)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.GENERAL
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    sentiment = models.CharField(max_length=10, choices=Sentiment.choices, blank=True)
    ai_status = models.CharField(
        max_length=12, choices=AIStatus.choices, default=AIStatus.PENDING
    )
    ai_summary = models.TextField(blank=True)
    ai_suggested_reply = models.TextField(blank=True)
    ai_provider = models.CharField(max_length=200, blank=True)
    ai_model = models.CharField(max_length=100, blank=True)
    ai_analyzed_at = models.DateTimeField(null=True, blank=True)
    ai_started_at = models.DateTimeField(null=True, blank=True)
    triage_version = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [("assign_ticket", "Can transfer support tickets")]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["customer", "-created_at"]),
            models.Index(fields=["department", "assigned_to"]),
            models.Index(fields=["ai_status"]),
        ]

    def __str__(self):
        return f"{self.ticket_number}: {self.subject}"

    def get_absolute_url(self):
        return reverse("ticket_detail", args=[self.pk])


class TicketReply(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ticket_replies",
    )
    message = models.TextField(max_length=15000)
    is_internal_note = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at", "pk"]


class Attachment(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="attachments"
    )
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    file = models.FileField(upload_to=attachment_path)
    original_name = models.CharField(max_length=180)
    created_at = models.DateTimeField(auto_now_add=True)


class TicketEvent(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    message = models.CharField(max_length=250)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    @property
    def display_message(self):
        from core.localization import event_label

        return event_label(self.message)


class Notification(models.Model):
    class EmailStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        SENDING = "sending", _("Sending")
        SENT = "sent", _("Sent")
        DISABLED = "disabled", _("Disabled")
        FAILED = "failed", _("Failed")

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.CharField(max_length=250)
    is_read = models.BooleanField(default=False)
    email_status = models.CharField(
        max_length=10, choices=EmailStatus.choices, default=EmailStatus.PENDING
    )
    email_started_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["email_status"]),
        ]

    @property
    def display_message(self):
        from core.localization import notification_label

        return notification_label(self.message)
