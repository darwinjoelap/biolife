import pytest
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

from apps.core.exceptions import ApplicationError
from apps.tenants.models import Domain, Subscription, Tenant
from apps.tenants.services.provisioning import provision_tenant


@pytest.mark.django_db(transaction=True)
def test_provision_tenant_crea_esquema_dominio_y_suscripcion(plan_basico):
    tenant = provision_tenant(
        name="Laboratorio de Prueba",
        schema_name="lab_prueba_1",
        subdomain="labprueba1",
        plan=plan_basico,
    )

    assert Tenant.objects.filter(schema_name="lab_prueba_1").exists()
    assert Domain.objects.filter(tenant=tenant, domain="labprueba1.localhost").exists()
    assert Subscription.objects.filter(tenant=tenant, plan=plan_basico).exists()

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
            [tenant.schema_name],
        )
        assert cursor.fetchone() is not None

    with schema_context(get_public_schema_name()):
        tenant.delete(force_drop=True)


@pytest.mark.django_db
def test_provision_tenant_schema_invalido_lanza_error():
    with pytest.raises(ApplicationError):
        provision_tenant(name="X", schema_name="PUBLIC-INVALIDO!", subdomain="x")


@pytest.mark.django_db(transaction=True)
def test_provision_tenant_schema_duplicado_no_deja_huerfano():
    tenant = provision_tenant(name="Original", schema_name="lab_dup", subdomain="labdup")

    with pytest.raises(ApplicationError):
        provision_tenant(name="Duplicado", schema_name="lab_dup", subdomain="labdup2")

    assert Tenant.objects.filter(schema_name="lab_dup").count() == 1

    with schema_context(get_public_schema_name()):
        tenant.delete(force_drop=True)
