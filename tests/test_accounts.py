from django.core import mail
from django.core.cache import cache
from django.test import Client, RequestFactory
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from unittest.mock import patch

from accounts.models import User
from accounts.throttling import auth_rate_limited
from .base import SupportTestCase


class AccountTests(SupportTestCase):
    def test_superuser_has_administrator_role_and_admin_access(self):
        user = User.objects.create_superuser(
            username="superadmin",
            email="super@example.com",
            password="Strong-admin-password-982",
        )
        self.assertEqual(user.role, "admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.has_perm("tickets.change_ticket"))

    def test_registration_cannot_choose_privileged_role(self):
        response = self.api.post(
            "/api/auth/register/",
            {
                "username": "newcustomer",
                "email": "new@example.com",
                "password": "Fresh-passphrase-9823",
                "role": "admin",
                "is_superuser": True,
            },
        )
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="newcustomer")
        self.assertEqual(user.role, "customer")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password("Fresh-passphrase-9823"))

    def test_weak_password_is_rejected(self):
        response = self.api.post(
            "/api/auth/register/",
            {"username": "newcustomer", "email": "new@example.com", "password": "123"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

    def test_email_is_case_insensitively_unique(self):
        response = self.api.post(
            "/api/auth/register/",
            {
                "username": "duplicate",
                "email": self.customer.email.upper(),
                "password": "Fresh-passphrase-9823",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_login_refresh_and_logout_blacklist(self):
        response = self.api.post(
            "/api/auth/token/",
            {"username": "customer", "password": "Test-pass-strong-982"},
        )
        self.assertEqual(response.status_code, 200)
        refresh = response.data["refresh"]
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(self.api.get("/api/auth/me/").status_code, 200)
        self.assertEqual(
            self.api.post("/api/auth/logout/", {"refresh": refresh}).status_code, 204
        )
        self.api.credentials()
        self.assertEqual(
            self.api.post("/api/auth/token/refresh/", {"refresh": refresh}).status_code,
            401,
        )

    def test_refresh_rotation_invalidates_old_refresh(self):
        token = self.api.post(
            "/api/auth/token/",
            {"username": "customer", "password": "Test-pass-strong-982"},
        ).data["refresh"]
        response = self.api.post("/api/auth/token/refresh/", {"refresh": token})
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data["refresh"], token)
        self.assertEqual(
            self.api.post("/api/auth/token/refresh/", {"refresh": token}).status_code,
            401,
        )

    def test_profile_cannot_escalate_privileges(self):
        self.authenticate(self.customer)
        response = self.api.patch(
            "/api/auth/me/",
            {"first_name": "Updated", "role": "admin", "departments": [self.tech.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.first_name, "Updated")
        self.assertEqual(self.customer.role, "customer")
        self.assertFalse(self.customer.departments.exists())

    def test_wrong_credentials_and_inactive_user_cannot_log_in(self):
        self.assertEqual(
            self.api.post(
                "/api/auth/token/", {"username": "customer", "password": "wrong"}
            ).status_code,
            401,
        )
        self.customer.is_active = False
        self.customer.save()
        self.assertEqual(
            self.api.post(
                "/api/auth/token/",
                {"username": "customer", "password": "Test-pass-strong-982"},
            ).status_code,
            401,
        )

    def test_password_change_revokes_existing_jwt(self):
        tokens = self.api.post(
            "/api/auth/token/",
            {"username": "customer", "password": "Test-pass-strong-982"},
        ).data
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = self.api.post(
            "/api/auth/password/change/",
            {
                "old_password": "Test-pass-strong-982",
                "new_password": "Changed-password-8932",
            },
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.api.get("/api/auth/me/").status_code, 401)
        self.api.credentials()
        self.assertEqual(
            self.api.post(
                "/api/auth/token/refresh/", {"refresh": tokens["refresh"]}
            ).status_code,
            401,
        )

    def test_password_reset_sends_real_reset_link(self):
        response = self.client.post(
            "/accounts/password_reset/", {"email": self.customer.email}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/reset/", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, [self.customer.email])

    def test_session_login_and_logout_require_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(
            client.post(
                "/accounts/login/",
                {"username": "customer", "password": "Test-pass-strong-982"},
            ).status_code,
            403,
        )
        client.force_login(self.customer)
        self.assertEqual(client.post("/accounts/logout/").status_code, 403)

    def test_password_reset_rate_limit(self):
        for _ in range(15):
            self.assertEqual(
                self.client.post(
                    "/accounts/password_reset/", {"email": "unknown@example.com"}
                ).status_code,
                302,
            )
        self.assertEqual(
            self.client.post(
                "/accounts/password_reset/", {"email": "unknown@example.com"}
            ).status_code,
            429,
        )

    def test_browser_login_admin_and_registration_are_rate_limited(self):
        for url, limit in [
            ("/accounts/login/", 15),
            ("/admin/login/", 15),
            ("/accounts/register/", 5),
        ]:
            cache.clear()
            with self.subTest(url=url):
                for _ in range(limit):
                    self.assertEqual(self.client.post(url, {}).status_code, 200)
                self.assertEqual(self.client.post(url, {}).status_code, 429)
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_auth_budget_recovers_from_eviction_and_fails_closed_on_repeated_race(self):
        with patch("accounts.throttling.cache.add", side_effect=[False, True]):
            with patch("accounts.throttling.cache.incr", side_effect=ValueError):
                self.assertFalse(auth_rate_limited(RequestFactory().get("/"), "test"))
        with patch("accounts.throttling.cache.add", return_value=False):
            with patch("accounts.throttling.cache.incr", side_effect=ValueError):
                self.assertTrue(auth_rate_limited(RequestFactory().get("/"), "test"))

    def test_admin_login_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/admin/login/", {}).status_code, 403)

    def test_web_password_change_revokes_access_and_refresh(self):
        tokens = self.api.post(
            "/api/auth/token/",
            {"username": "customer", "password": "Test-pass-strong-982"},
        ).data
        self.client.force_login(self.customer)
        response = self.client.post(
            "/accounts/password_change/",
            {
                "old_password": "Test-pass-strong-982",
                "new_password1": "Changed-password-8932",
                "new_password2": "Changed-password-8932",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.assertEqual(self.api.get("/api/auth/me/").status_code, 401)
        self.api.credentials()
        self.assertEqual(
            self.api.post(
                "/api/auth/token/refresh/", {"refresh": tokens["refresh"]}
            ).status_code,
            401,
        )

    def test_password_reset_revokes_refresh_token(self):
        tokens = self.api.post(
            "/api/auth/token/",
            {"username": "customer", "password": "Test-pass-strong-982"},
        ).data
        uid = urlsafe_base64_encode(force_bytes(self.customer.pk))
        token = default_token_generator.make_token(self.customer)
        response = self.client.get(f"/accounts/reset/{uid}/{token}/")
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
            response.url,
            {
                "new_password1": "Reset-password-8932",
                "new_password2": "Reset-password-8932",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password("Reset-password-8932"))
        self.assertEqual(
            self.api.post(
                "/api/auth/token/refresh/", {"refresh": tokens["refresh"]}
            ).status_code,
            401,
        )

    def test_refresh_for_deleted_account_is_unauthorized(self):
        user = User.objects.create_user(
            username="temporary",
            email="temporary@example.com",
            password="Test-pass-strong-982",
        )
        tokens = self.api.post(
            "/api/auth/token/",
            {"username": user.username, "password": "Test-pass-strong-982"},
        ).data
        user.delete()
        self.assertEqual(
            self.api.post(
                "/api/auth/token/refresh/", {"refresh": tokens["refresh"]}
            ).status_code,
            401,
        )

    def test_employee_cannot_list_users(self):
        self.authenticate(self.employee)
        self.assertEqual(self.api.get("/api/users/").status_code, 403)
        self.authenticate(self.admin)
        self.assertEqual(self.api.get("/api/users/").status_code, 200)

    def test_admin_can_manage_roles_without_granting_superuser_flag(self):
        self.authenticate(self.admin)
        response = self.api.patch(
            f"/api/users/{self.other.pk}/",
            {"role": "employee", "departments": [self.tech.pk], "is_superuser": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.other.refresh_from_db()
        self.assertEqual(self.other.role, "employee")
        self.assertFalse(self.other.is_superuser)
        self.assertFalse(self.other.is_staff)

    def test_html_registration_and_profile(self):
        response = self.client.post(
            "/accounts/register/",
            {
                "username": "webcustomer",
                "email": "web@example.com",
                "password1": "Different-password-3849",
                "password2": "Different-password-3849",
            },
        )
        self.assertRedirects(response, "/dashboard/")
        self.assertContains(self.client.get("/accounts/profile/"), "webcustomer")

    def tearDown(self):
        cache.clear()
