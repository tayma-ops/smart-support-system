"""Shared fixed-window budgets for browser authentication endpoints.

Redis provides atomic increments across processes. LocMemCache is suitable only
for a single development process. REMOTE_ADDR must be set by a trusted proxy.
"""

import hashlib
import time

from django.core.cache import cache


def auth_rate_limited(request, scope, limit=15, window=3600):
    address = request.META.get("REMOTE_ADDR", "unknown")
    digest = hashlib.sha256(address.encode()).hexdigest()
    bucket = int(time.time()) // window
    key = f"browser-auth:{scope}:{digest}:{bucket}"
    for _ in range(2):
        if cache.add(key, 1, window + 1):
            return False
        try:
            return cache.incr(key) > limit
        except ValueError:
            # A cache eviction between add and incr must not turn login into 500.
            continue
    return True
