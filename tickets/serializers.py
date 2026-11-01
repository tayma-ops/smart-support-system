from rest_framework import serializers

from accounts.models import User
from .models import (
    Attachment,
    Department,
    Notification,
    Ticket,
    TicketEvent,
    TicketReply,
)
from .validators import validate_attachment


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "description", "is_active"]


class TicketCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=180)
    description = serializers.CharField(max_length=15000)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True),
        allow_null=True,
        required=False,
    )
    attachment = serializers.FileField(required=False, validators=[validate_attachment])


class TicketTriageSerializer(serializers.Serializer):
    priority = serializers.ChoiceField(choices=Ticket.Priority.choices, required=False)
    category = serializers.ChoiceField(choices=Ticket.Category.choices, required=False)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True),
        allow_null=True,
        required=False,
    )


class TicketStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Ticket.Status.choices)


class TicketAssignmentSerializer(serializers.Serializer):
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role="employee", is_active=True), allow_null=True
    )


class ReplySerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.display_name", read_only=True)

    class Meta:
        model = TicketReply
        fields = [
            "id",
            "author_name",
            "message",
            "is_internal_note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "author_name", "created_at", "updated_at"]


class AttachmentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ["id", "original_name", "download_url", "created_at"]

    def get_download_url(self, obj) -> str:
        from django.urls import reverse

        return reverse("attachment_download", args=[obj.pk])


class AttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(validators=[validate_attachment])


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketEvent
        fields = ["id", "message", "created_at"]


class TicketSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.display_name", read_only=True
    )
    assigned_to_name = serializers.CharField(
        source="assigned_to.display_name", default=None, read_only=True
    )
    department_name = serializers.CharField(
        source="department.name", default=None, read_only=True
    )

    class Meta:
        model = Ticket
        fields = [
            "id",
            "ticket_number",
            "customer_name",
            "assigned_to",
            "assigned_to_name",
            "department",
            "department_name",
            "subject",
            "description",
            "category",
            "priority",
            "status",
            "sentiment",
            "ai_status",
            "ai_summary",
            "ai_suggested_reply",
            "ai_provider",
            "ai_model",
            "ai_analyzed_at",
            "created_at",
            "updated_at",
            "resolved_at",
            "closed_at",
        ]
        read_only_fields = fields

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if (
            request
            and not getattr(request.user, "is_support", False)
            and not getattr(self.context.get("view"), "swagger_fake_view", False)
        ):
            for name in [
                "sentiment",
                "ai_status",
                "ai_summary",
                "ai_suggested_reply",
                "ai_provider",
                "ai_model",
                "ai_analyzed_at",
            ]:
                fields.pop(name, None)
        return fields


class TicketDetailSerializer(TicketSerializer):
    replies = serializers.SerializerMethodField()
    attachments = AttachmentSerializer(many=True, read_only=True)
    events = serializers.SerializerMethodField()

    class Meta(TicketSerializer.Meta):
        fields = TicketSerializer.Meta.fields + ["replies", "attachments", "events"]

    def get_replies(self, obj) -> list[dict]:
        replies = obj.replies.select_related("author")
        if not self.context["request"].user.is_support:
            replies = replies.filter(is_internal_note=False)
        return ReplySerializer(replies, many=True).data

    def get_events(self, obj) -> list[dict]:
        return EventSerializer(obj.events.all(), many=True).data

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if (
            request
            and not getattr(request.user, "is_support", False)
            and not getattr(self.context.get("view"), "swagger_fake_view", False)
        ):
            fields.pop("events", None)
        return fields


class NotificationSerializer(serializers.ModelSerializer):
    ticket_number = serializers.CharField(source="ticket.ticket_number", read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "ticket", "ticket_number", "message", "is_read", "created_at"]
        read_only_fields = ["id", "ticket", "ticket_number", "message", "created_at"]
