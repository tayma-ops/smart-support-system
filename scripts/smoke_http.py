"""Exercise the running local server with synthetic data and real CSRF/session requests."""

import argparse
from io import BytesIO
from pathlib import Path
import os
import re
import secrets
import sys
from urllib.parse import urlparse

import httpx
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()
from django.conf import settings
from accounts.models import User
from tickets.models import Ticket
from tickets.services import delete_ticket


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--language", choices=["en", "ar"], default="en")
    args = parser.parse_args()
    if not settings.DEBUG or urlparse(args.url).hostname not in {
        "localhost",
        "127.0.0.1",
    }:
        raise SystemExit(
            "This check only runs against a loopback development server with DEBUG=True."
        )
    identifier = secrets.token_hex(8)
    password = secrets.token_urlsafe(24)
    user = User.objects.create_user(
        username=f"http_check_{identifier}",
        email=f"{identifier}@example.invalid",
        password=password,
    )
    ticket = None
    image = BytesIO()
    Image.new("RGB", (3, 3)).save(image, format="PNG")

    def csrf(response):
        match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', response.text)
        if not match:
            raise AssertionError("A CSRF-protected form was not rendered")
        return match[1]

    try:
        with httpx.Client(
            base_url=args.url,
            follow_redirects=True,
            timeout=10,
            headers={"Accept-Language": args.language},
        ) as client:
            login = client.get("/accounts/login/")
            login.raise_for_status()
            response = client.post(
                "/accounts/login/",
                data={
                    "username": user.username,
                    "password": password,
                    "csrfmiddlewaretoken": csrf(login),
                },
                headers={"Referer": str(login.url)},
            )
            assert (
                response.status_code == 200 and response.url.path == "/dashboard/"
            ), "Login failed"
            assert (
                f'lang="{args.language}"' in response.text
            ), "Language selection failed"
            assert (
                'dir="rtl"' if args.language == "ar" else 'dir="ltr"'
            ) in response.text, "Text direction failed"
            form = client.get("/tickets/new/")
            response = client.post(
                "/tickets/new/",
                data={
                    "subject": "[Integration] HTTP support workflow",
                    "description": "Synthetic end-to-end support request.",
                    "csrfmiddlewaretoken": csrf(form),
                },
                files={"attachment": ("sample.png", image.getvalue(), "image/png")},
                headers={"Referer": str(form.url)},
            )
            assert response.status_code == 200 and re.fullmatch(
                r"/tickets/\d+/", response.url.path
            ), "Ticket creation failed"
            ticket = Ticket.objects.get(customer=user)
            response = client.post(
                ticket.get_absolute_url(),
                data={
                    "action": "reply",
                    "message": "One more detail from the customer.",
                    "csrfmiddlewaretoken": csrf(response),
                },
                headers={"Referer": str(response.url)},
            )
            assert (
                response.status_code == 200
                and "One more detail from the customer." in response.text
            ), "Reply failed"
            data = client.get(f"/api/tickets/{ticket.pk}/").json()
            assert (
                len(data["replies"]) == 1 and "ai_summary" not in data
            ), "API scope failed"
            download = client.get(data["attachments"][0]["download_url"])
            assert (
                download.status_code == 200 and download.content == image.getvalue()
            ), "Private download failed"
            response = client.post(
                ticket.get_absolute_url(),
                data={"action": "close", "csrfmiddlewaretoken": csrf(response)},
                headers={"Referer": str(response.url)},
            )
            ticket.refresh_from_db()
            assert ticket.status == "closed", "Close failed"
            assert client.get("/api/dashboard/").json()["closed"] == 1, "Metrics failed"
            client.post(
                "/accounts/logout/",
                data={"csrfmiddlewaretoken": csrf(response)},
                headers={"Referer": str(response.url)},
            )
            assert client.get("/api/tickets/").status_code == 401, "Logout failed"
            print(
                "PASS: real HTTP login, CSRF, create, image upload, reply, scoped API, private download, close, metrics and logout"
            )
    finally:
        if ticket:
            # Only this script's own synthetic ticket/files are removed.
            from types import SimpleNamespace

            delete_ticket(actor=SimpleNamespace(is_admin=True), ticket=ticket)
        user.delete()


if __name__ == "__main__":
    main()
