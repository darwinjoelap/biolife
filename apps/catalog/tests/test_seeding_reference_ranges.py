import pytest
from django_tenants.test.cases import TenantTestCase

from apps.catalog.models import ReferenceRange
from apps.catalog.services.seeding import seed_uroanalisis
from apps.catalog.services.seeding_reference_ranges import seed_reference_ranges
from apps.core.exceptions import ApplicationError


class SeedReferenceRangesTests(TenantTestCase):
    def test_requiere_uroanalisis_sembrado_primero(self):
        # Sin seed_uroanalisis(), URO_NITRITOS no existe: seed_reference_ranges() debe
        # fallar con un mensaje claro, no con un DoesNotExist crudo.
        with pytest.raises(ApplicationError):
            seed_reference_ranges()

    def test_cubre_los_6_range_type(self):
        seed_uroanalisis()
        seed_reference_ranges()

        tipos_presentes = set(ReferenceRange.objects.values_list("range_type", flat=True))
        tipos_esperados = {choice.value for choice in ReferenceRange.RangeType}
        assert tipos_presentes == tipos_esperados

    def test_es_idempotente(self):
        seed_uroanalisis()
        seed_reference_ranges()
        cantidad_antes = ReferenceRange.objects.count()

        seed_reference_ranges()
        cantidad_despues = ReferenceRange.objects.count()

        assert cantidad_antes == cantidad_despues
