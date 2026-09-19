from django.conf import settings
from django.utils import timezone


class TenantTimezoneMiddleware:
    """Activa la zona horaria del tenant en cada request.

    En esta fase usa settings.TIME_ZONE para todos los tenants.
    # FASE 03: leer la zona horaria desde TenantSettings del tenant activo.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        timezone.activate(settings.TIME_ZONE)
        response = self.get_response(request)
        timezone.deactivate()
        return response
