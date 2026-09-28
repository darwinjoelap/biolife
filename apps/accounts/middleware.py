"""Clave temporal (Fase 11b): quien entra con una clave puesta por el administrador del
laboratorio debe cambiarla antes de usar el sistema."""
from django.shortcuts import redirect
from django.urls import reverse

ALLOWED_PREFIXES = ("/cuenta/", "/static/", "/media/", "/__debug__/", "/verificar/")


class ForcePasswordChangeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (user is not None and user.is_authenticated
                and getattr(user, "must_change_password", False)
                and not request.path.startswith(ALLOWED_PREFIXES)):
            return redirect(reverse("accounts:password") + "?obligatorio=1")
        return self.get_response(request)
