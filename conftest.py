import pytest

from apps.tenants.models import Plan


@pytest.fixture
def plan_basico(db):
    return Plan.objects.create(
        code="basico",
        name="Básico",
        price_monthly="0.00",
        max_users=5,
        max_orders_month=500,
        max_storage_mb=1024,
    )
