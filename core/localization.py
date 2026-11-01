"""Translate system labels at display time; customer-authored content stays untouched."""

import re

from django.utils.translation import gettext as _, gettext_noop

DEPARTMENTS = {
    gettext_noop("Technical Support"),
    gettext_noop("Billing"),
    gettext_noop("Sales"),
    gettext_noop("Account Support"),
    gettext_noop("General Support"),
}
STATUS_LABELS = {
    "open": gettext_noop("Open"),
    "in_progress": gettext_noop("In progress"),
    "waiting": gettext_noop("Waiting for customer"),
    "resolved": gettext_noop("Resolved"),
    "closed": gettext_noop("Closed"),
}
EVENT_LABELS = {
    gettext_noop("Ticket created"),
    gettext_noop("Assignment updated"),
    gettext_noop("Triage details updated"),
    gettext_noop("Synthetic demo ticket created"),
}


def department_label(name):
    if not name:
        return _("General queue")
    return _(name) if name in DEPARTMENTS else name


def status_label(value):
    return _(STATUS_LABELS.get(value, value))


def event_label(message):
    match = re.fullmatch(r"Status: (.+) → (.+)", message)
    if match:
        return _("Status: %(old)s → %(new)s") % {
            "old": status_label(match[1]),
            "new": status_label(match[2]),
        }
    return _(message)


def notification_label(message):
    for pattern, template in [
        (r"(SSD-[A-F0-9]+) was created\.", gettext_noop("%(ticket)s was created.")),
        (r"New reply on (SSD-[A-F0-9]+)\.", gettext_noop("New reply on %(ticket)s.")),
        (
            r"Assignment updated for (SSD-[A-F0-9]+)\.",
            gettext_noop("Assignment updated for %(ticket)s."),
        ),
    ]:
        match = re.fullmatch(pattern, message)
        if match:
            return _(template) % {"ticket": match[1]}
    match = re.fullmatch(r"(SSD-[A-F0-9]+): (.+)\.", message)
    if match:
        return _("%(ticket)s: %(status)s.") % {
            "ticket": match[1],
            "status": status_label(match[2]),
        }
    return message
