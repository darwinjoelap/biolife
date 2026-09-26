"""Validación de fórmulas contra el catálogo del tenant y mantenimiento de
`Parameter.depends_on`. Es el único camino permitido para asignar una fórmula a un
parámetro: el ciclo se detecta **al guardar**, no al calcular (docs/00_ARQUITECTURA.md).
"""
from django.db import transaction

from apps.catalog.models import Parameter
from apps.catalog.services.formula_engine import (
    FormulaSyntaxError,
    ParsedFormula,
    calculation_order,
    parse_formula,
)


def validate_formula(*, code: str, formula: str) -> ParsedFormula:
    """Valida la fórmula que tendría el parámetro `code` (exista o no todavía).

    Verifica sintaxis, que cada `{CODIGO}` exista en el tenant y sea numérico, que no se
    referencie a sí mismo y que no cierre un ciclo con las fórmulas ya guardadas."""
    parsed = parse_formula(formula)

    if code in parsed.parameter_codes:
        raise FormulaSyntaxError(f"La fórmula de {code} no puede referenciarse a sí misma.")

    referenced = dict(
        Parameter.objects.filter(code__in=parsed.parameter_codes).values_list(
            "code", "value_type"
        )
    )
    missing = sorted(parsed.parameter_codes - referenced.keys())
    if missing:
        raise FormulaSyntaxError(
            "La fórmula referencia parámetros que no existen: " + ", ".join(missing)
        )
    numeric_types = {Parameter.ValueType.NUMERIC, Parameter.ValueType.NUMERIC_CALCULATED}
    not_numeric = sorted(c for c, vt in referenced.items() if vt not in numeric_types)
    if not_numeric:
        raise FormulaSyntaxError(
            "Sólo se pueden usar parámetros numéricos en una fórmula: " + ", ".join(not_numeric)
        )

    formulas: dict[str, str | ParsedFormula] = dict(
        Parameter.objects.filter(value_type=Parameter.ValueType.NUMERIC_CALCULATED)
        .exclude(code=code)
        .exclude(formula="")
        .values_list("code", "formula")
    )
    formulas[code] = parsed
    calculation_order(formulas)  # lanza FormulaSyntaxError si hay ciclo
    return parsed


@transaction.atomic
def set_parameter_formula(*, parameter: Parameter, formula: str) -> Parameter:
    """Asigna la fórmula a un parámetro calculado y sincroniza `depends_on`."""
    if parameter.value_type != Parameter.ValueType.NUMERIC_CALCULATED:
        raise FormulaSyntaxError(
            f"{parameter.code} no es NUMERIC_CALCULATED; no admite fórmula."
        )
    parsed = validate_formula(code=parameter.code, formula=formula)
    parameter.formula = parsed.source
    parameter.save(update_fields=["formula", "updated_at"])
    sync_parameter_dependencies(parameter=parameter, parsed=parsed)
    return parameter


def sync_parameter_dependencies(
    *, parameter: Parameter, parsed: ParsedFormula | None = None
) -> None:
    """Recalcula `depends_on` desde el texto de la fórmula (nunca se edita a mano)."""
    if not parameter.formula:
        parameter.depends_on.clear()
        return
    parsed = parsed or parse_formula(parameter.formula)
    parameter.depends_on.set(Parameter.objects.filter(code__in=parsed.parameter_codes))
