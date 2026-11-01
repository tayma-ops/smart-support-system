from django.contrib.admin import AdminSite
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from accounts.throttling import auth_rate_limited


class SupportAdminSite(AdminSite):
    @method_decorator(never_cache)
    def login(self, request, extra_context=None):
        if request.method == "POST" and auth_rate_limited(request, "admin-login"):
            return render(request, "registration/rate_limited.html", status=429)
        return super().login(request, extra_context)
