"""Evolución de los resultados de un paciente (Fase 11e, ADR-032).

Sólo valores **validados** y numéricos. La fecha de cada punto es la de la orden; la
banda de referencia sale del rango que se usó al validar (puede cambiar con la edad).
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from apps.results.models import Result, ResultValue
from apps.results.services.value_parsing import format_value

VALIDATED = (Result.Status.VALIDADO, Result.Status.RECTIFICADO)
BAND_TYPES = {"CLOSED": ("low", "high"), "UPPER_BOUND": (None, "high"),
              "LOWER_BOUND": ("low", None)}


@dataclass
class SeriesPoint:
    when: datetime.date
    value: Decimal
    text: str
    flag: str
    reference_text: str
    low: Decimal | None
    high: Decimal | None
    order_id: object
    order_number: str
    delta_pct: float | None = None  # contra el punto anterior

    @property
    def direction(self) -> str:
        if self.delta_pct is None or abs(self.delta_pct) < 0.05:
            return ""
        return "up" if self.delta_pct > 0 else "down"


def _numeric_values(*, patient, parameter_ids=None):
    values = ResultValue.objects.filter(
        result__order_item__order__patient=patient, result__status__in=VALIDATED,
        value_numeric__isnull=False, parameter__is_active=True,
    )
    if parameter_ids is not None:
        values = values.filter(parameter_id__in=list(parameter_ids))
    return values.select_related(
        "parameter", "parameter__test", "parameter__unit", "reference_range",
        "result__order_item__order",
    ).order_by("result__order_item__order__ordered_at", "created_at")


def _band(value: ResultValue) -> tuple[Decimal | None, Decimal | None]:
    rng = value.reference_range
    if rng is None or rng.range_type not in BAND_TYPES:
        return None, None
    low_attr, high_attr = BAND_TYPES[rng.range_type]
    return (getattr(rng, low_attr) if low_attr else None,
            getattr(rng, high_attr) if high_attr else None)


def _point(value: ResultValue) -> SeriesPoint:
    order = value.result.order_item.order
    low, high = _band(value)
    return SeriesPoint(
        when=timezone.localdate(order.ordered_at), value=value.value_numeric,
        text=format_value(value), flag=value.flag, reference_text=value.reference_text,
        low=low, high=high, order_id=order.pk, order_number=order.number,
    )


def _with_deltas(points: list[SeriesPoint]) -> list[SeriesPoint]:
    for previous, point in zip(points, points[1:], strict=False):
        if previous.value:
            point.delta_pct = float((point.value - previous.value) / abs(previous.value)
                                    * 100)
    return points


def _grouped(values) -> dict:
    series: dict = {}
    for value in values:
        entry = series.setdefault(str(value.parameter_id),
                                  {"parameter": value.parameter, "points": []})
        entry["points"].append(_point(value))
    for entry in series.values():
        _with_deltas(entry["points"])
    return series


def _report_order(entry) -> tuple:
    parameter = entry["parameter"]
    return (parameter.test.name, parameter.order_index)


def parameter_series(*, patient, parameter_id) -> dict | None:
    """{"parameter", "points"} de un parámetro, o None si no tiene valores."""
    return _grouped(_numeric_values(patient=patient, parameter_ids=[parameter_id])).get(
        str(parameter_id))


def series_for(*, patient, parameter_ids) -> list[dict]:
    """Varias series (PDF), en el orden pedido."""
    ids = [str(pid) for pid in parameter_ids]
    grouped = _grouped(_numeric_values(patient=patient, parameter_ids=ids))
    return [grouped[pid] for pid in dict.fromkeys(ids) if pid in grouped]


def evolution_series(*, patient) -> list[dict]:
    """Todas las series numéricas validadas del paciente, ordenadas por examen."""
    return sorted(_grouped(_numeric_values(patient=patient)).values(), key=_report_order)
