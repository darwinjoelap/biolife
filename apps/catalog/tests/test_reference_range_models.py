from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django_tenants.test.cases import TenantTestCase

from apps.catalog.models import (
    CodedOption,
    CodedOptionSet,
    Parameter,
    ReferenceRange,
    Section,
    Test,
)


class ReferenceRangeConstraintTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        section = Section.objects.create(code="QUIM", name="QUÍMICA")
        test_obj = Test.objects.create(
            code="QUIM", name="QUÍMICA", section=section, sample_type=Test.SampleType.SUERO,
        )
        self.parameter = Parameter.objects.create(
            test=test_obj, code="QUIM_X", name="X", value_type=Parameter.ValueType.NUMERIC,
        )
        option_set = CodedOptionSet.objects.create(code="NEG_POS", name="Negativo/Positivo")
        self.option = CodedOption.objects.create(option_set=option_set, value="NEGATIVO")

    def test_closed_sin_low_falla(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            ReferenceRange.objects.create(
                parameter=self.parameter, range_type=ReferenceRange.RangeType.CLOSED,
                display_text="x", high=Decimal("10"),
            )

    def test_closed_con_low_y_high_se_crea(self):
        rango = ReferenceRange.objects.create(
            parameter=self.parameter, range_type=ReferenceRange.RangeType.CLOSED,
            display_text="1 - 10", low=Decimal("1"), high=Decimal("10"),
        )
        assert rango.pk is not None

    def test_tolerance_sin_center_falla(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            ReferenceRange.objects.create(
                parameter=self.parameter, range_type=ReferenceRange.RangeType.TOLERANCE,
                display_text="x", tolerance=Decimal("6"),
            )

    def test_qualitative_sin_expected_option_falla(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            ReferenceRange.objects.create(
                parameter=self.parameter, range_type=ReferenceRange.RangeType.QUALITATIVE,
                display_text="NEGATIVO",
            )

    def test_qualitative_con_expected_option_se_crea(self):
        rango = ReferenceRange.objects.create(
            parameter=self.parameter, range_type=ReferenceRange.RangeType.QUALITATIVE,
            display_text="NEGATIVO", expected_option=self.option,
        )
        assert rango.pk is not None

    def test_interpretive_sin_bands_falla(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            ReferenceRange.objects.create(
                parameter=self.parameter, range_type=ReferenceRange.RangeType.INTERPRETIVE,
                display_text="x",
            )

    def test_age_min_mayor_que_age_max_falla(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            ReferenceRange.objects.create(
                parameter=self.parameter, range_type=ReferenceRange.RangeType.CLOSED,
                display_text="x", low=Decimal("1"), high=Decimal("10"),
                age_min_days=100, age_max_days=50,
            )
