from decimal import Decimal

import pytest

from apps.results.services.value_parsing import format_number, parse_number


@pytest.mark.parametrize("raw, expected", [
    ("13,4", "13.4"), ("13.4", "13.4"), ("150.000", "150000"), ("1.234,5", "1234.5"),
    ("0,80", "0.80"), ("  6,8 ", "6.8"), ("-2", "-2"),
])
def test_parse_number(raw, expected):
    assert parse_number(raw) == Decimal(expected)


@pytest.mark.parametrize("raw", ["abc", "1,2,3", "", "NaN"])
def test_parse_number_invalido(raw):
    with pytest.raises(ValueError):
        parse_number(raw)


def test_formato_de_informe():
    assert format_number(Decimal("150000"), decimals=0) == "150.000"
    assert format_number(Decimal("13.45"), decimals=1) == "13,5"
    assert format_number(Decimal("0.8"), decimals=2) == "0,80"
