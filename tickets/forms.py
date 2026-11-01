from django.utils.translation import gettext_lazy as _
from django import forms

from accounts.models import User
from .models import Department, Ticket
from .validators import validate_attachment


class TicketForm(forms.Form):
    subject = forms.CharField(
        label=_("Subject"),
        max_length=180,
        widget=forms.TextInput(
            attrs={"placeholder": _("A short, clear description of the issue")}
        ),
    )
    department = forms.ModelChoiceField(
        label=_("Department"),
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label=_("Let support route my ticket"),
    )
    description = forms.CharField(
        label=_("Description"),
        max_length=15000,
        widget=forms.Textarea(
            attrs={
                "rows": 7,
                "placeholder": _(
                    "What happened? Include any steps, error messages and the impact."
                ),
            }
        ),
    )
    attachment = forms.FileField(
        label=_("Attachment"),
        required=False,
        validators=[validate_attachment],
        help_text=_("PNG, JPEG or PDF. Maximum 5 MB."),
    )


class ReplyForm(forms.Form):
    message = forms.CharField(
        label=_("Message"),
        max_length=15000,
        widget=forms.Textarea(
            attrs={"rows": 5, "placeholder": _("Write a thoughtful reply…")}
        ),
    )
    is_internal_note = forms.BooleanField(
        required=False, label=_("Internal note · visible to support staff only")
    )

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        if not user.is_support:
            del self.fields["is_internal_note"]


class StatusForm(forms.Form):
    status = forms.ChoiceField(label=_("Status"), choices=Ticket.Status.choices)


class AssignmentForm(forms.Form):
    assigned_to = forms.ModelChoiceField(
        label=_("Assigned to"),
        queryset=User.objects.filter(role="employee", is_active=True),
        required=False,
        empty_label=_("Unassigned"),
    )

    def __init__(self, *args, ticket, **kwargs):
        super().__init__(*args, **kwargs)
        if ticket.department_id:
            self.fields["assigned_to"].queryset = self.fields[
                "assigned_to"
            ].queryset.filter(departments=ticket.department)


class TriageForm(forms.Form):
    priority = forms.ChoiceField(label=_("Priority"), choices=Ticket.Priority.choices)
    category = forms.ChoiceField(label=_("Category"), choices=Ticket.Category.choices)


class AttachmentForm(forms.Form):
    file = forms.FileField(
        validators=[validate_attachment],
        label=_("Add a file"),
        help_text=_("PNG, JPEG or PDF · 5 MB maximum"),
    )
