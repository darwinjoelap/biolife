from django_tenants.test.cases import TenantTestCase

from apps.catalog.models import Parameter, Test
from apps.catalog.services.seeding import seed_uroanalisis


class SeedUroanalisisTests(TenantTestCase):
    def test_crea_exactamente_un_test_uro(self):
        seed_uroanalisis()

        assert Test.objects.filter(code="URO").count() == 1

    def test_crea_los_tres_grupos(self):
        test = seed_uroanalisis()

        nombres = set(test.parameter_groups.values_list("name", flat=True))
        assert nombres == {"EXAMEN FÍSICO", "EXAMEN QUÍMICO", "EXAMEN MICROSCÓPICO"}

    def test_cubre_los_9_tipos_de_valor(self):
        test = seed_uroanalisis()

        tipos_presentes = set(test.parameters.values_list("value_type", flat=True))
        tipos_esperados = {choice.value for choice in Parameter.ValueType}
        assert tipos_presentes == tipos_esperados

    def test_es_idempotente(self):
        seed_uroanalisis()
        cantidad_antes = Parameter.objects.filter(test__code="URO").count()

        seed_uroanalisis()
        cantidad_despues = Parameter.objects.filter(test__code="URO").count()

        assert cantidad_antes == cantidad_despues
        assert Test.objects.filter(code="URO").count() == 1
