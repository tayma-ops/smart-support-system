"""Use the real PostgreSQL CI service while isolating email and AI from external services."""

import os

os.environ["USE_SQLITE"] = "False"
os.environ["DJANGO_DEBUG"] = "True"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "True"
os.environ["AI_API_KEY"] = ""
os.environ["AI_PROVIDER"] = "ai_service.providers.OpenAIProvider"
os.environ["AI_MODEL"] = ""
os.environ["AI_BASE_URL"] = "https://api.openai.com/v1"
os.environ["EMAIL_NOTIFICATIONS"] = "False"

from .settings import *  # noqa: F403,E402
from .settings import MIDDLEWARE

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MIDDLEWARE = [
    item for item in MIDDLEWARE if item != "whitenoise.middleware.WhiteNoiseMiddleware"
]
