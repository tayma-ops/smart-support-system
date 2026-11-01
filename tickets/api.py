from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from django.db.models import Case, IntegerField, Value, When
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from . import services
from .filters import TicketFilter, TicketOrderingFilter
from .models import Department, Ticket
from .permissions import IsAdministrator, TicketAccess, can_transfer
from .selectors import visible_notifications, visible_tickets
from .serializers import (
    AttachmentSerializer,
    AttachmentUploadSerializer,
    DepartmentSerializer,
    NotificationSerializer,
    ReplySerializer,
    TicketAssignmentSerializer,
    TicketCreateSerializer,
    TicketDetailSerializer,
    TicketSerializer,
    TicketStatusSerializer,
    TicketTriageSerializer,
)


class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [TicketAccess]
    queryset = Ticket.objects.none()
    filterset_class = TicketFilter
    search_fields = ["ticket_number", "subject"]
    ordering_fields = ["created_at", "updated_at", "priority", "status"]
    filter_backends = [DjangoFilterBackend, SearchFilter, TicketOrderingFilter]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        return visible_tickets(self.request.user).annotate(
            priority_rank=Case(
                When(priority="urgent", then=Value(4)),
                When(priority="high", then=Value(3)),
                When(priority="medium", then=Value(2)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )

    def get_serializer_class(self):
        return {
            "create": TicketCreateSerializer,
            "update": TicketTriageSerializer,
            "partial_update": TicketTriageSerializer,
            "retrieve": TicketDetailSerializer,
            "reply": ReplySerializer,
            "status": TicketStatusSerializer,
            "assign": TicketAssignmentSerializer,
            "attachments": AttachmentUploadSerializer,
        }.get(self.action, TicketSerializer)

    @extend_schema(responses={201: TicketDetailSerializer})
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = services.create_ticket(actor=request.user, **serializer.validated_data)
        return Response(
            TicketDetailSerializer(ticket, context=self.get_serializer_context()).data,
            status=201,
        )

    @extend_schema(responses=TicketDetailSerializer)
    def update(self, request, *args, **kwargs):
        ticket = self.get_object()
        serializer = self.get_serializer(
            data=request.data, partial=kwargs.get("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        ticket = services.update_triage(
            actor=request.user, ticket=ticket, **serializer.validated_data
        )
        return Response(
            TicketDetailSerializer(ticket, context=self.get_serializer_context()).data
        )

    def perform_destroy(self, instance):
        services.delete_ticket(actor=self.request.user, ticket=instance)

    @extend_schema(responses={201: ReplySerializer})
    @action(detail=True, methods=["post"])
    def reply(self, request, pk=None):
        ticket = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reply = services.add_reply(
            actor=request.user, ticket=ticket, **serializer.validated_data
        )
        return Response(ReplySerializer(reply).data, status=201)

    @extend_schema(responses=TicketSerializer)
    @action(detail=True, methods=["post"], url_path="status")
    def status(self, request, pk=None):
        ticket = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = services.change_status(
            actor=request.user, ticket=ticket, **serializer.validated_data
        )
        return Response(
            TicketSerializer(ticket, context=self.get_serializer_context()).data
        )

    @extend_schema(responses=TicketSerializer)
    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        if not request.user.is_support:
            raise PermissionDenied(_("Only support staff can assign tickets."))
        if not can_transfer(request.user) and (
            ticket.assigned_to_id is not None
            or str(request.data.get("assigned_to")) != str(request.user.pk)
        ):
            raise PermissionDenied(
                _("You may only claim an unassigned ticket for yourself.")
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticket = services.assign_ticket(
            actor=request.user,
            ticket=ticket,
            employee=serializer.validated_data["assigned_to"],
        )
        return Response(
            TicketSerializer(ticket, context=self.get_serializer_context()).data
        )

    @extend_schema(responses={201: AttachmentSerializer})
    @action(detail=True, methods=["post"])
    def attachments(self, request, pk=None):
        ticket = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attachment = services.add_attachment(
            actor=request.user, ticket=ticket, upload=serializer.validated_data["file"]
        )
        return Response(
            AttachmentSerializer(attachment).data, status=status.HTTP_201_CREATED
        )


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    queryset = Department.objects.all()
    search_fields = ["name"]

    def get_permissions(self):
        return (
            [IsAuthenticated()]
            if self.action in {"list", "retrieve"}
            else [IsAdministrator()]
        )

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.is_admin:
            return self.queryset
        return self.queryset.filter(is_active=True)

    def perform_destroy(self, instance):
        # Preserve historical tickets and team membership: DELETE archives a department.
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class NotificationViewSet(
    mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = NotificationSerializer
    filterset_fields = ["is_read"]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            from .models import Notification

            return Notification.objects.none()
        return visible_notifications(self.request.user)
