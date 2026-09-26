from django_tenants.test.cases import TenantTestCase
from django_tenants.utils import get_public_schema_name, schema_context

from apps.accounts.models import User
from apps.tenants.services.provisioning import provision_tenant


class TenantIsolationTests(TenantTestCase):
    """
    TenantTestCase (django_tenants.test.cases) crea un tenant de prueba (self.tenant)
    y ejecuta cada test dentro de su esquema automáticamente.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_tenant, _ = provision_tenant(
            name="Otro Tenant de Prueba", schema_name="test_otro", subdomain="testotro",
            admin_email="admin@testotro.test",
        )

    @classmethod
    def tearDownClass(cls):
        with schema_context(get_public_schema_name()):
            cls.other_tenant.delete(force_drop=True)
        super().tearDownClass()

    def test_objeto_no_visible_desde_otro_tenant(self):
        User.objects.create_user(username="usuario_tenant_actual", password="x")

        with schema_context(self.other_tenant.schema_name):
            self.assertFalse(
                User.objects.filter(username="usuario_tenant_actual").exists()
            )

    def test_objeto_no_visible_desde_public(self):
        User.objects.create_user(username="usuario_tenant_actual_2", password="x")

        with schema_context(get_public_schema_name()):
            try:
                visible = User.objects.filter(username="usuario_tenant_actual_2").exists()
            except Exception:
                visible = False
            self.assertFalse(visible)
