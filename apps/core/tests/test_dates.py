from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest

from apps.core.utils.dates import age_in_days, format_time_12h


def test_age_in_days_calcula_dias_completos():
    assert age_in_days(date(2020, 1, 1), date(2020, 1, 11)) == 10


def test_age_in_days_fecha_futura_lanza_error():
    with pytest.raises(ValueError):
        age_in_days(date(2030, 1, 1), date(2020, 1, 1))


def test_format_time_12h_manana():
    # settings.TIME_ZONE es America/Caracas: se construye el dt ya en esa zona
    # para que la conversión a "hora local" del reporte no dependa de la zona activa.
    caracas = ZoneInfo("America/Caracas")
    dt = datetime(2026, 1, 1, 6, 0, tzinfo=caracas)
    assert format_time_12h(dt) == "6:00 A.M."


def test_format_time_12h_convierte_utc_a_hora_local():
    # 10:00 UTC = 6:00 A.M. en America/Caracas (UTC-4).
    dt = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    assert format_time_12h(dt) == "6:00 A.M."
