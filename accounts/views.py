from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordResetView
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import ProfileForm, RegistrationForm
from .throttling import auth_rate_limited


class ThrottledPasswordResetView(PasswordResetView):
    def post(self, request, *args, **kwargs):
        if auth_rate_limited(request, "password-reset"):
            return render(request, "registration/rate_limited.html", status=429)
        return super().post(request, *args, **kwargs)


class ThrottledLoginView(LoginView):
    template_name = "registration/login.html"

    def post(self, request, *args, **kwargs):
        if auth_rate_limited(request, "login"):
            return render(request, "registration/rate_limited.html", status=429)
        return super().post(request, *args, **kwargs)


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    if request.method == "POST" and auth_rate_limited(request, "register", limit=5):
        return render(request, "registration/rate_limited.html", status=429)
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("dashboard")
    return render(request, "registration/register.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("profile")
    return render(request, "accounts/profile.html", {"form": form})
