"""Consultas de resultados (Fase 10)."""
from __future__ import annotations

from apps.results.models import Result, ResultValue
from apps.results.services.value_parsing import format_value


def previous_values(*, patient, parameters, exclude_order) -> dict:
    """{parameter_id: {"text", "flag", "date"}} con el último valor VALIDADO del paciente
    en otra orden (para comparar al cargar)."""
    values = (
        ResultValue.objects.filter(
            parameter__in=parameters, result__status=Result.Status.VALIDADO,
            result__order_item__order__patient=patient,
        )
        .exclude(result__order_item__order=exclude_order)
        .select_related("parameter", "coded_option", "result")
        .order_by("parameter_id", "-result__validated_at")
    )
    found: dict = {}
    for value in values:
        if value.parameter_id not in found:
            found[value.parameter_id] = {"text": format_value(value), "flag": value.flag,
                                         "date": value.result.validated_at}
    return found


def result_value_of_order(*, order, pk) -> ResultValue:
    return ResultValue.objects.select_related("parameter", "result", "coded_option").get(
        pk=pk, result__order_item__order=order)


def result_of_order(*, order, pk) -> Result:
    return Result.objects.select_related("order_item__test", "entered_by").get(
        pk=pk, order_item__order=order)
