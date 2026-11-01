from rest_framework.permissions import BasePermission

from .selectors import visible_tickets


class IsAdministrator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_admin


class TicketAccess(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_active

    def has_object_permission(self, request, view, obj):
        return visible_tickets(request.user).filter(pk=obj.pk).exists()


def can_transfer(user):
    return user.is_admin or (user.is_support and user.has_perm("tickets.assign_ticket"))


def can_claim(user, ticket):
    """Eligibility for the claim control; services still lock and validate writes."""
    return (
        user.is_authenticated
        and user.is_active
        and user.role == user.Role.EMPLOYEE
        and ticket.assigned_to_id is None
        and (
            ticket.department_id is None
            or user.departments.filter(pk=ticket.department_id).exists()
        )
    )
