"""Marca de un resultado contra su rango de referencia (Fase 10, ADR-025). Puro: recibe el
valor y el `ReferenceRange` ya resuelto, no toca la base de datos.

- Crítico primero: por debajo de `critical_low` → CRITICO_BAJO; por encima de
  `critical_high` → CRITICO_ALTO. Nunca pasa desapercibido.
- CLOSED / UPPER_BOUND / LOWER_BOUND → BAJO / ALTO / NORMAL.
- TOLERANCE: fuera de `center ± tolerance` → BAJO / ALTO.
- QUALITATIVE: opción distinta a la esperada → ANORMAL.
- INTERPRETIVE: se elige la banda (HOMA, HbA1c, procalcitonina) y su texto va como
  interpretación; la primera banda es la normal, las demás ANORMAL.
- Sin rango: una opción marcada «patológica» en el catálogo → ANORMAL; si no, sin marca.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

NORMAL, BAJO, ALTO = "NORMAL", "BAJO", "ALTO"
CRITICO_BAJO, CRITICO_ALTO, ANORMAL = "CRITICO_BAJO", "CRITICO_ALTO", "ANORMAL"


@dataclass(frozen=True)
class Assessment:
    flag: str = ""
    interpretation: str = ""


def _band(bands: list[dict], value: Decimal) -> tuple[int, dict] | None:
    """Última banda que contiene el valor (`min` inclusivo, `max` exclusivo)."""
    found = None
    for index, band in enumerate(bands or []):
        low, high = band.get("min"), band.get("max")
        if (low is None or value >= Decimal(str(low))) and (
                high is None or value < Decimal(str(high))):
            found = (index, band)
    return found


def assess(*, number: Decimal | None, option=None, reference_range=None) -> Assessment:
    rr = reference_range
    if option is not None and number is None:
        if rr is not None and rr.range_type == "QUALITATIVE" and rr.expected_option_id:
            return Assessment(NORMAL if option.pk == rr.expected_option_id else ANORMAL)
        if option.is_pathological:
            return Assessment(ANORMAL)
        return Assessment(NORMAL if rr is not None else "")
    if number is None or rr is None:
        if option is not None and option.is_pathological:
            return Assessment(ANORMAL)
        return Assessment()

    if rr.critical_low is not None and number < rr.critical_low:
        return Assessment(CRITICO_BAJO)
    if rr.critical_high is not None and number > rr.critical_high:
        return Assessment(CRITICO_ALTO)

    kind = rr.range_type
    if kind == "INTERPRETIVE":
        band = _band(rr.bands, number)
        if band is None:
            return Assessment()
        index, data = band
        return Assessment(NORMAL if index == 0 else ANORMAL, data.get("text", ""))
    if kind == "TOLERANCE":
        if number < rr.center - rr.tolerance:
            return Assessment(BAJO)
        if number > rr.center + rr.tolerance:
            return Assessment(ALTO)
        return Assessment(NORMAL)
    if kind == "QUALITATIVE":
        if option is not None and rr.expected_option_id:
            return Assessment(NORMAL if option.pk == rr.expected_option_id else ANORMAL)
        return Assessment()
    if rr.low is not None and kind in ("CLOSED", "LOWER_BOUND") and number < rr.low:
        return Assessment(BAJO)
    if rr.high is not None and kind in ("CLOSED", "UPPER_BOUND") and number > rr.high:
        return Assessment(ALTO)
    return Assessment(NORMAL)
