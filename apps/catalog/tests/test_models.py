import pytest
from django.db import IntegrityError, transaction
from django_tenants.test.cases import TenantTestCase

from apps.catalog.models import CodedOptionSet, Parameter, Section, Test


class ParameterConstraintTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.section = Section.objects.create(code="ORINA", name="ORINA")
        self.test_obj = Test.objects.create(
            code="URO", name="UROANÁLISIS", section=self.section,
            sample_type=Test.SampleType.ORINA,
        )
        self.option_set = CodedOptionSet.objects.create(code="NEG_POS", name="Negativo/Positivo")

    def test_coded_sin_option_set_falla(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            Parameter.objects.create(
                test=self.test_obj, code="URO_X", name="X",
                value_type=Parameter.ValueType.CODED,
            )

    def test_coded_con_option_set_se_crea(self):
        parameter = Parameter.objects.create(
            test=self.test_obj, code="URO_X", name="X",
            value_type=Parameter.ValueType.CODED, option_set=self.option_set,
        )
        assert parameter.pk is not None

    def test_numeric_calculated_sin_formula_falla(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            Parameter.objects.create(
                test=self.test_obj, code="URO_CALC", name="Calculado",
                value_type=Parameter.ValueType.NUMERIC_CALCULATED,
            )

    def test_numeric_calculated_con_formula_se_crea(self):
        parameter = Parameter.objects.create(
            test=self.test_obj, code="URO_CALC", name="Calculado",
            value_type=Parameter.ValueType.NUMERIC_CALCULATED, formula="A / B",
        )
        assert parameter.pk is not None

    def test_numeric_sin_option_set_ni_formula_se_crea(self):
        parameter = Parameter.objects.create(
            test=self.test_obj, code="URO_NUM", name="Numérico",
            value_type=Parameter.ValueType.NUMERIC,
        )
        assert parameter.pk is not None
