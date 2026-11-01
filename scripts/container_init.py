import subprocess
import sys

for command in [["check"], ["migrate", "--noinput"], ["collectstatic", "--noinput"]]:
    subprocess.run([sys.executable, "manage.py", *command], check=True)
