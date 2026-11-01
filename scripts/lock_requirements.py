"""Record runtime versions from a fresh environment containing only requirements.in."""

from importlib.metadata import distributions

from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
installed_names = {item.metadata["Name"].lower() for item in distributions()}
if installed_names & {"black", "djlint", "polib", "aiosmtpd", "ruff"}:
    raise SystemExit(
        "Generate the runtime lock in a fresh virtual environment with only requirements.in installed; development tools must not enter requirements.txt."
    )
result = subprocess.run(
    [sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=True
)
lines = [
    line
    for line in result.stdout.splitlines()
    if not line.lower().startswith("gunicorn==")
]
lines.append("gunicorn==26.2.0; sys_platform != 'win32'")
(root / "requirements.txt").write_text(
    "\n".join(sorted(lines, key=str.lower)) + "\n", encoding="utf-8"
)
