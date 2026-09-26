import pytest

from apps.core.utils.dates import age_parts_to_days, days_to_age_parts, format_age_days


def test_un_ano_y_doce_meses_son_lo_mismo():
    assert age_parts_to_days(years=1) == age_parts_to_days(months=12) == 365


def test_conversion_ida_y_vuelta_exacta():
    for total in range(0, 60000):
        years, months, days = days_to_age_parts(total)
        assert months < 12
        assert age_parts_to_days(years=years, months=months, days=days) == total


def test_formato_legible():
    assert format_age_days(0) == "0 días"
    assert format_age_days(29) == "29 días"
    assert format_age_days(365) == "1 año"
    assert format_age_days(548) == "1 año 6 meses"


def test_edad_negativa_falla():
    with pytest.raises(ValueError):
        age_parts_to_days(years=-1)
