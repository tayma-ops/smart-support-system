"""Check a real PostgreSQL/Redis development stack with an isolated Celery queue and a local SMTP sink."""

import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import uuid

from dotenv import dotenv_values

try:
    from aiosmtpd.controller import Controller
except ImportError:
    raise SystemExit(
        "Install development tools: python -m pip install -r requirements-dev.txt"
    ) from None

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--with-ai",
        action="store_true",
        help="Run the configured real AI model; cloud usage may incur provider costs",
    )
    args = parser.parse_args()
    environment = os.environ.copy()
    for key, value in dotenv_values(ROOT / ".env").items():
        if value is not None:
            environment.setdefault(key, value)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    queue = "supportdesk_check_" + uuid.uuid4().hex
    environment.update(
        CELERY_TASK_ALWAYS_EAGER="False",
        CELERY_TASK_DEFAULT_QUEUE=queue,
        PYTHONUTF8="1",
        EMAIL_NOTIFICATIONS="True",
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        EMAIL_HOST="127.0.0.1",
        EMAIL_PORT=str(port),
        EMAIL_USE_TLS="False",
        EMAIL_USE_SSL="False",
        EMAIL_HOST_USER="",
        EMAIL_HOST_PASSWORD="",
    )
    if not args.with_ai:
        environment.update(
            AI_PROVIDER="ai_service.providers.OpenAIProvider",
            AI_API_KEY="",
            AI_MODEL="",
        )
    messages = []

    class Capture:
        async def handle_DATA(self, server, session, envelope):
            messages.append(envelope)
            return "250 Synthetic integration message accepted"

    controller = Controller(Capture(), hostname="127.0.0.1", port=port)
    controller.start()
    (ROOT / ".local").mkdir(exist_ok=True)
    log = (ROOT / ".local/worker-stack.log").open("wb")
    worker = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "celery",
            "-A",
            "config",
            "worker",
            "--pool=solo",
            "--loglevel=WARNING",
            "--queues",
            queue,
        ],
        cwd=ROOT,
        env=environment,
        stdout=log,
        stderr=log,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    try:
        command = [
            sys.executable,
            "-X",
            "utf8",
            "scripts/verify_worker.py",
            "--check-email",
        ]
        if args.with_ai:
            command.append("--expect-analysis")
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        (ROOT / ".local/worker-stack-result.log").write_text(
            result.stdout + result.stderr, encoding="utf-8"
        )
        print(result.stdout, end="")
        if result.returncode:
            print(result.stderr)
            raise SystemExit(result.returncode)
        assert messages, "No SMTP message was received"
        assert all(
            address.endswith("@example.invalid")
            for message in messages
            for address in message.rcpt_tos
        )
        print(
            "PASS: real local SMTP accepted a synthetic notification; no external email was sent"
        )
    finally:
        worker.terminate()
        worker.wait(timeout=10)
        controller.stop()
        log.close()


if __name__ == "__main__":
    main()
