import pytest
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

from apps.core.exceptions import ApplicationError
from apps.tenants.models import Domain, Tenant
from apps.tenants.services.decommission import delete_demo_tenant
from apps.tenants.services.provisioning import provision_tenant


def _schema_exists(name: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", [name]
        )
        return cursor.fetchone() is not None


def _provision(schema_name: str) -> Tenant:
    tenant, _ = provision_tenant(
        name=f"Lab {schema_name}", schema_name=schema_name,
        subdomain=schema_name.replace("_", ""), admin_email=f"a@{schema_name}.test",
        seed_catalog=False,
    )
    return tenant


@pytest.mark.django_db(transaction=True)
def test_borra_laboratorio_demo_con_esquema_y_dominio():
    _provision("lab_baja")
    assert _schema_exists("lab_baja")

    assert delete_demo_tenant(schema_name="lab_baja", confirmation="lab_baja") == "Lab lab_baja"

    assert not Tenant.objects.filter(schema_name="lab_baja").exists()
    assert not Domain.objects.filter(domain="labbaja.localhost").exists()
    assert not _schema_exists("lab_baja")


@pytest.mark.django_db(transaction=True)
def test_no_borra_laboratorio_real_ni_con_confirmacion_distinta():
    tenant = _provision("lab_real")
    try:
        with pytest.raises(ApplicationError, match="confirmación"):
            delete_demo_tenant(schema_name="lab_real", confirmation="lab_otro")

        Tenant.objects.filter(pk=tenant.pk).update(status=Tenant.Status.ACTIVO)
        with pytest.raises(ApplicationError, match="sólo se borran"):
            delete_demo_tenant(schema_name="lab_real", confirmation="lab_real")
        assert _schema_exists("lab_real")
    finally:
        with schema_context(get_public_schema_name()):
            tenant.delete(force_drop=True)


@pytest.mark.django_db
def test_no_borra_public_ni_esquemas_inexistentes():
    with pytest.raises(ApplicationError, match="public"):
        delete_demo_tenant(schema_name="public", confirmation="public")
    with pytest.raises(ApplicationError, match="No existe"):
        delete_demo_tenant(schema_name="no_existe", confirmation="no_existe")
