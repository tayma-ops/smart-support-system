from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = "customer", _("Customer")
        EMPLOYEE = "employee", _("Support employee")
        ADMIN = "admin", _("Administrator")

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.CUSTOMER)
    departments = models.ManyToManyField(
        "tickets.Department", blank=True, related_name="employees"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_user_email_ci")
        ]

    @property
    def is_admin(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_support(self):
        return self.is_admin or self.role == self.Role.EMPLOYEE

    @property
    def display_name(self):
        return self.get_full_name() or self.username

    def has_perm(self, perm, obj=None):
        return (self.is_active and self.is_admin) or super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        return (self.is_active and self.is_admin) or super().has_module_perms(app_label)

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        if self.is_superuser:
            self.role = self.Role.ADMIN
        # Django admin access is reserved for administrators, never support employees.
        self.is_staff = self.is_admin
        super().save(*args, **kwargs)
