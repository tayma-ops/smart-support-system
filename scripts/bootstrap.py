"""Create a local development environment without committing credentials."""

import argparse
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sqlite",
        action="store_true",
        help="Use SQLite and synchronous tasks for a broker-free local demo",
    )
    parser.add_argument(
        "--configure-only",
        action="store_true",
        help="Create .env without connecting to a database (e.g. before Compose)",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Create explicitly labeled synthetic demo records",
    )
    args = parser.parse_args()
    env_file = ROOT / ".env"
    if not env_file.exists():
        content = (ROOT / ".env.example").read_text(encoding="utf-8")
        replacements = {
            "SECRET_KEY=": f"SECRET_KEY={secrets.token_urlsafe(64)}",
            "DB_PASSWORD=": f"DB_PASSWORD={secrets.token_urlsafe(32)}",
            "DJANGO_DEBUG=True": "DJANGO_DEBUG=True",
            "SECURE_SSL_REDIRECT=True": "SECURE_SSL_REDIRECT=False",
            "SESSION_COOKIE_SECURE=True": "SESSION_COOKIE_SECURE=False",
            "CSRF_COOKIE_SECURE=True": "CSRF_COOKIE_SECURE=False",
        }
        if args.sqlite:
            replacements.update(
                {
                    "USE_SQLITE=False": "USE_SQLITE=True",
                    "CELERY_TASK_ALWAYS_EAGER=False": "CELERY_TASK_ALWAYS_EAGER=True",
                }
            )
        lines = [replacements.get(line, line) for line in content.splitlines()]
        env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(
            "Created ignored .env with unique local credentials. DEBUG=True: development only."
        )
    else:
        print(
            "Preserving existing .env. Flags do not overwrite an existing configuration."
        )
    if args.configure_only:
        print("Configuration ready. No database commands were run.")
        return
    for command in [["check"], ["migrate", "--noinput"]] + (
        [["seed_demo"]] if args.seed else []
    ):
        subprocess.run(
            [sys.executable, "manage.py", *command],
            cwd=ROOT,
            check=True,
            env=os.environ.copy(),
        )
    print("Ready. Start with: python manage.py runserver")


if __name__ == "__main__":
    main()
