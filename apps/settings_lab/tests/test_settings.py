import pytest
from django.conf import settings as django_settings
from django.http import HttpResponse
from django.test import RequestFactory
from django.utils import timezone
from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_public_schema_name, schema_context

from apps.settings_lab.middleware import TenantTimezoneMiddleware
from apps.settings_lab.models import TenantSettings
from apps.tenants.models import Tenant
from apps.tenants.services.provisioning import provision_tenant


class TenantSettingsSingletonTests(TenantTestCase):
    """Casos 1-3 del criterio de aceptación de la Tarea 7: comportamiento del
    singleton dentro del esquema de un tenant existente."""

    def test_get_solo_crea_la_fila_si_no_existe(self):
        assert TenantSettings.objects.count() == 0

        obj = TenantSettings.get_solo()

        assert obj.pk == 1
        assert TenantSettings.objects.count() == 1

    def test_get_solo_llamado_dos_veces_no_duplica(self):
        primero = TenantSettings.get_solo()
        segundo = TenantSettings.get_solo()

        assert primero.pk == segundo.pk == 1
        assert TenantSettings.objects.count() == 1

    def test_delete_no_borra_el_registro(self):
        obj = TenantSettings.get_solo()

        obj.delete()

        assert TenantSettings.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_provision_tenant_deja_exactamente_un_tenant_settings():
    """Caso 4: provision_tenant() crea el TenantSettings por defecto del laboratorio
    nuevo (Tarea 2), ni cero ni más de uno."""
    tenant, _ = provision_tenant(
        name="Lab Settings Test",
        schema_name="lab_settings_test",
        subdomain="labsettingstest",
        admin_email="admin@labsettingstest.test",
    )

    with schema_context(tenant.schema_name):
        assert TenantSettings.objects.count() == 1

    with schema_context(get_public_schema_name()):
        tenant.delete(force_drop=True)


class TenantTimezoneMiddlewareTests(TenantTestCase):
    """Caso 5: el middleware activa la zona horaria real del TenantSettings, no la
    fija de settings.TIME_ZONE."""

    def test_middleware_activa_la_zona_horaria_del_tenant(self):
        tenant_settings = TenantSettings.get_solo()
        tenant_settings.timezone = "America/Bogota"
        tenant_settings.save()

        captured = {}

        def get_response(request):
            captured["tz"] = timezone.get_current_timezone_name()
            return HttpResponse("ok")

        middleware = TenantTimezoneMiddleware(get_response)
        request = RequestFactory().get("/")
        request.tenant = self.tenant

        middleware(request)

        assert captured["tz"] == "America/Bogota"

    def test_middleware_usa_time_zone_por_defecto_en_public(self):
        """No incluido explícitamente en el roadmap, pero cubre la corrección hecha
        sobre la Tarea 3: en el esquema public no existe TenantSettings, así que el
        middleware debe usar settings.TIME_ZONE en vez de fallar."""
        captured = {}

        def get_response(request):
            captured["tz"] = timezone.get_current_timezone_name()
            return HttpResponse("ok")

        middleware = TenantTimezoneMiddleware(get_response)
        request = RequestFactory().get("/")
        request.tenant = Tenant(schema_name=get_public_schema_name())

        middleware(request)

        assert captured["tz"] == django_settings.TIME_ZONE
