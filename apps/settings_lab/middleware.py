from django.conf import settings
from django.utils import timezone
from django_tenants.utils import get_public_schema_name

from apps.settings_lab.models import TenantSettings


class TenantTimezoneMiddleware:
    """Activa la zona horaria real del tenant en cada request.

    En el esquema public no existe `TenantSettings` (`apps.settings_lab` es
    TENANT_APP, no SHARED_APP): ahí se usa `settings.TIME_ZONE` como
    respaldo, para no fallar con "relation does not exist" en requests de
    plataforma (ej. /admin/ en localhost).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = getattr(request, "tenant", None)
        if tenant is not None and tenant.schema_name != get_public_schema_name():
            tz = TenantSettings.get_solo().timezone
        else:
            tz = settings.TIME_ZONE
        timezone.activate(tz)
        response = self.get_response(request)
        timezone.deactivate()
        return response
