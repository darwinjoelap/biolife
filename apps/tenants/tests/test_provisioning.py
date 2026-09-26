import pytest
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

from apps.core.exceptions import ApplicationError
from apps.tenants.models import Domain, Subscription, Tenant
from apps.tenants.services.provisioning import provision_tenant


@pytest.mark.django_db(transaction=True)
def test_provision_tenant_crea_esquema_dominio_y_suscripcion(plan_basico):
    tenant, admin_password = provision_tenant(
        name="Laboratorio de Prueba",
        schema_name="lab_prueba_1",
        subdomain="labprueba1",
        admin_email="admin@labprueba1.test",
        plan=plan_basico,
    )
    assert admin_password  # se generó una temporal

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
        provision_tenant(
            name="X", schema_name="PUBLIC-INVALIDO!", subdomain="x",
            admin_email="admin@x.test",
        )


@pytest.mark.django_db(transaction=True)
def test_provision_tenant_schema_duplicado_no_deja_huerfano():
    tenant, _ = provision_tenant(
        name="Original", schema_name="lab_dup", subdomain="labdup",
        admin_email="admin@labdup.test",
    )

    with pytest.raises(ApplicationError):
        provision_tenant(
            name="Duplicado", schema_name="lab_dup", subdomain="labdup2",
            admin_email="admin@labdup2.test",
        )

    assert Tenant.objects.filter(schema_name="lab_dup").count() == 1

    with schema_context(get_public_schema_name()):
        tenant.delete(force_drop=True)


@pytest.mark.django_db(transaction=True)
def test_provision_tenant_nace_con_catalogo_perfiles_y_monedas():
    # ADR-021: un laboratorio nuevo queda listo para trabajar.
    from apps.billing.models import PriceList
    from apps.catalog.models import Profile, Test

    tenant, _ = provision_tenant(
        name="Con catálogo", schema_name="lab_catalogo", subdomain="labcatalogo",
        admin_email="admin@labcatalogo.test",
    )
    try:
        with schema_context("lab_catalogo"):
            assert Test.objects.filter(is_active=True).count() >= 50
            assert Profile.objects.filter(code="PERFIL_LIPIDICO").exists()
            assert PriceList.objects.filter(code="GENERAL", is_default=True).exists()
    finally:
        with schema_context(get_public_schema_name()):
            tenant.delete(force_drop=True)


@pytest.mark.django_db(transaction=True)
def test_provision_tenant_sin_catalogo_nace_vacio():
    from apps.catalog.models import Test

    tenant, _ = provision_tenant(
        name="Vacío", schema_name="lab_vacio", subdomain="labvacio",
        admin_email="admin@labvacio.test", seed_catalog=False,
    )
    try:
        with schema_context("lab_vacio"):
            assert not Test.objects.exists()
    finally:
        with schema_context(get_public_schema_name()):
            tenant.delete(force_drop=True)
