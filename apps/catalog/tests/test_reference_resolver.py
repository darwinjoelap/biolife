from decimal import Decimal

from django_tenants.test.cases import TenantTestCase

from apps.catalog.models import Parameter, ReferenceRange, Section, Test
from apps.catalog.services.reference_resolver import resolve_reference_range


class ReferenceResolverTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        section = Section.objects.create(code="HEM", name="HEMATOLOGÍA")
        test_obj = Test.objects.create(
            code="HEM", name="HEMATOLOGÍA", section=section,
            sample_type=Test.SampleType.SANGRE_TOTAL,
        )
        self.parameter = Parameter.objects.create(
            test=test_obj, code="HEM_X", name="X", value_type=Parameter.ValueType.NUMERIC,
        )

    def test_resuelve_por_sexo(self):
        rango_m = ReferenceRange.objects.create(
            parameter=self.parameter, range_type=ReferenceRange.RangeType.CLOSED,
            display_text="M", sex=ReferenceRange.Sex.M,
            low=Decimal("13"), high=Decimal("15"),
        )
        rango_f = ReferenceRange.objects.create(
            parameter=self.parameter, range_type=ReferenceRange.RangeType.CLOSED,
            display_text="F", sex=ReferenceRange.Sex.F,
            low=Decimal("12"), high=Decimal("16"),
        )

        resultado_m = resolve_reference_range(
            parameter=self.parameter, sex="M", age_days=10000,
        )
        resultado_f = resolve_reference_range(
            parameter=self.parameter, sex="F", age_days=10000,
        )

        assert resultado_m == rango_m
        assert resultado_f == rango_f

    def test_resuelve_por_edad(self):
        rango_neonato = ReferenceRange.objects.create(
            parameter=self.parameter, range_type=ReferenceRange.RangeType.CLOSED,
            display_text="neonato", age_min_days=0, age_max_days=28,
            low=Decimal("9000"), high=Decimal("30000"),
        )
        rango_resto = ReferenceRange.objects.create(
            parameter=self.parameter, range_type=ReferenceRange.RangeType.CLOSED,
            display_text="resto", age_min_days=29, age_max_days=54750,
            low=Decimal("4500"), high=Decimal("10000"),
        )

        resultado_neonato = resolve_reference_range(
            parameter=self.parameter, sex="M", age_days=5,
        )
        resultado_adulto = resolve_reference_range(
            parameter=self.parameter, sex="M", age_days=10000,
        )

        assert resultado_neonato == rango_neonato
        assert resultado_adulto == rango_resto

    def test_sex_any_hace_de_respaldo_pero_priority_desempata(self):
        rango_any = ReferenceRange.objects.create(
            parameter=self.parameter, range_type=ReferenceRange.RangeType.CLOSED,
            display_text="any", sex=ReferenceRange.Sex.ANY,
            low=Decimal("1"), high=Decimal("10"), priority=0,
        )
        rango_f_especifico = ReferenceRange.objects.create(
            parameter=self.parameter, range_type=ReferenceRange.RangeType.CLOSED,
            display_text="f", sex=ReferenceRange.Sex.F,
            low=Decimal("2"), high=Decimal("9"), priority=1,
        )

        resultado_f = resolve_reference_range(parameter=self.parameter, sex="F", age_days=100)
        resultado_m = resolve_reference_range(parameter=self.parameter, sex="M", age_days=100)

        assert resultado_f == rango_f_especifico
        assert resultado_m == rango_any

    def test_sin_coincidencia_devuelve_none(self):
        ReferenceRange.objects.create(
            parameter=self.parameter, range_type=ReferenceRange.RangeType.CLOSED,
            display_text="x", sex=ReferenceRange.Sex.M,
            low=Decimal("1"), high=Decimal("10"), age_min_days=0, age_max_days=100,
        )

        resultado = resolve_reference_range(parameter=self.parameter, sex="F", age_days=50)

        assert resultado is None
