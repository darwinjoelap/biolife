"""Motor de fórmulas de parámetros calculados (`Parameter.value_type = NUMERIC_CALCULATED`).

Puro: no toca el ORM. Recibe textos de fórmula y valores, devuelve `Decimal`. La
validación contra el catálogo del tenant (códigos existentes, ciclos, `depends_on`) vive
en `services/formula_validation.py`, que sí usa el ORM.

**Sintaxis** (ver ADR-017):
- `{CODIGO}` → valor de otro parámetro del mismo tenant (`{HEM_HEMOGLOBINA}`).
- `{@variable}` → dato de la orden, no del catálogo (`{@peso}`, `{@talla}`). Sólo los
  nombres de `CONTEXT_VARIABLES` son válidos.
- Operadores: `+ - * / **` y signo unario. Paréntesis.
- Funciones: `round(x, n)`, `sqrt(x)`, `min(...)`, `max(...)`, `abs(x)`.
- Literales numéricos (`1440`, `0.007184`). Nada más.

**Nunca `eval()`.** La fórmula es entrada de usuario del tenant: se parsea con `ast` y se
recorre con una lista blanca de nodos; cualquier otro nodo (atributos, subíndices,
comparaciones, lambdas, nombres sueltos) se rechaza al parsear.

**Precisión:** todo se calcula en `Decimal` con precisión completa; los parámetros
calculados que alimentan a otros (VLDL → LDL, superficie corporal → depuración corregida)
pasan su valor sin redondear, igual que Excel. El redondeo a `Parameter.decimals` es sólo
para mostrar (`quantize_for_display`).
"""
from __future__ import annotations

import ast
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, DivisionByZero, InvalidOperation, localcontext
from graphlib import CycleError, TopologicalSorter

from apps.core.exceptions import ApplicationError

MAX_FORMULA_LENGTH = 500
MAX_EXPONENT = Decimal("10")
CALCULATION_PRECISION = 28

# Variables que no vienen del catálogo sino de la orden/contexto (docs/01_MODELO_DATOS.md,
# sección E). Quien evalúa (Fase 10) arma el diccionario con estos nombres.
CONTEXT_VARIABLES: dict[str, str] = {
    "peso": "Peso del paciente en kg (Order.weight_kg)",
    "talla": "Talla del paciente en cm (Order.height_cm)",
    "volumen_orina_24h": "Volumen de orina de 24 h en mL (Order.urine_volume_24h_ml)",
    # ISI del lote de tromboplastina: Angelus no lo ha confirmado y su origen (TenantSettings,
    # lote, etc.) se decide en la Fase 10 — ver ADR-017.
    "isi": "ISI del lote de tromboplastina (INR)",
}

_PARAMETER_REF = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")
_CONTEXT_REF = re.compile(r"\{@([a-z][a-z0-9_]*)\}")
_PARAM_PREFIX = "p__"
_CONTEXT_PREFIX = "c__"

_ALLOWED_BINOPS = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)
_ALLOWED_UNARYOPS = (ast.UAdd, ast.USub)
_ALLOWED_FUNCTIONS = {"round", "sqrt", "min", "max", "abs"}


class FormulaSyntaxError(ApplicationError):
    """La fórmula no es válida (sintaxis, nodo prohibido, variable desconocida)."""


class FormulaEvaluationError(ApplicationError):
    """La fórmula es válida pero no se pudo calcular con estos valores (división por
    cero, raíz de negativo, potencia inválida)."""


class MissingInputError(ApplicationError):
    """Falta uno o más insumos para calcular la fórmula."""

    def __init__(self, missing: tuple[str, ...]):
        super().__init__(
            "Faltan valores para calcular: " + ", ".join(missing), extra={"missing": missing}
        )
        self.missing = missing


@dataclass(frozen=True)
class ParsedFormula:
    source: str
    tree: ast.Expression
    parameter_codes: frozenset[str]
    context_variables: frozenset[str]


@dataclass(frozen=True)
class CalculationResult:
    """Resultado de un parámetro calculado. `value` es `None` si no se pudo calcular; en
    ese caso `reason` explica por qué (se registra, no bloquea el resto del informe)."""

    value: Decimal | None
    reason: str = ""
    missing: tuple[str, ...] = field(default_factory=tuple)


def parse_formula(formula: str) -> ParsedFormula:
    """Parsea y valida la sintaxis de una fórmula. No consulta el catálogo."""
    source = (formula or "").strip()
    if not source:
        raise FormulaSyntaxError("La fórmula está vacía.")
    if len(source) > MAX_FORMULA_LENGTH:
        raise FormulaSyntaxError(
            f"La fórmula excede {MAX_FORMULA_LENGTH} caracteres."
        )

    parameter_codes = frozenset(_PARAMETER_REF.findall(source))
    context_variables = frozenset(_CONTEXT_REF.findall(source))
    unknown = sorted(context_variables - CONTEXT_VARIABLES.keys())
    if unknown:
        raise FormulaSyntaxError(
            "Variable de la orden desconocida: "
            + ", ".join(f"{{@{name}}}" for name in unknown)
            + ". Válidas: " + ", ".join(f"{{@{n}}}" for n in sorted(CONTEXT_VARIABLES))
        )

    translated = _PARAMETER_REF.sub(lambda m: _PARAM_PREFIX + m.group(1), source)
    translated = _CONTEXT_REF.sub(lambda m: _CONTEXT_PREFIX + m.group(1), translated)
    if "{" in translated or "}" in translated:
        raise FormulaSyntaxError(
            "Referencia mal escrita: use {CODIGO} para parámetros (mayúsculas) y "
            "{@variable} para datos de la orden (minúsculas)."
        )

    try:
        tree = ast.parse(translated, mode="eval")
    except SyntaxError as exc:
        raise FormulaSyntaxError(f"Sintaxis inválida en la fórmula: {source}") from exc

    _check_nodes(tree)
    return ParsedFormula(
        source=source, tree=tree,
        parameter_codes=parameter_codes, context_variables=context_variables,
    )


def _check_nodes(tree: ast.Expression) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Expression | ast.Load):
            continue
        if isinstance(node, ast.BinOp):
            if not isinstance(node.op, _ALLOWED_BINOPS):
                raise FormulaSyntaxError("Operador no permitido en la fórmula.")
        elif isinstance(node, ast.UnaryOp):
            if not isinstance(node.op, _ALLOWED_UNARYOPS):
                raise FormulaSyntaxError("Operador no permitido en la fórmula.")
        elif isinstance(node, ast.operator | ast.unaryop):
            continue
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, int | float):
                raise FormulaSyntaxError("Sólo se permiten literales numéricos.")
        elif isinstance(node, ast.Name):
            if not node.id.startswith((_PARAM_PREFIX, _CONTEXT_PREFIX)) and (
                node.id not in _ALLOWED_FUNCTIONS
            ):
                raise FormulaSyntaxError(
                    f"Nombre no reconocido '{node.id}': los parámetros van entre llaves, "
                    "p. ej. {HEM_HEMOGLOBINA}."
                )
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCTIONS:
                raise FormulaSyntaxError(
                    "Función no permitida. Válidas: " + ", ".join(sorted(_ALLOWED_FUNCTIONS))
                )
            if node.keywords:
                raise FormulaSyntaxError("Las funciones no aceptan argumentos con nombre.")
        else:
            raise FormulaSyntaxError(
                f"Elemento no permitido en la fórmula: {type(node).__name__}."
            )
    # Un nombre de función usado como valor (`{A} + sqrt`) no es un Call: rechazarlo.
    call_funcs = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id in _ALLOWED_FUNCTIONS
            and id(node) not in call_funcs
        ):
            raise FormulaSyntaxError(f"'{node.id}' es una función y debe llamarse con ().")


def evaluate_formula(
    *,
    formula: str | ParsedFormula,
    values: Mapping[str, Decimal | None],
    context: Mapping[str, Decimal | None] | None = None,
) -> Decimal:
    """Evalúa una fórmula con precisión completa. Lanza `MissingInputError` si falta un
    insumo y `FormulaEvaluationError` si la operación no es válida con esos valores."""
    parsed = formula if isinstance(formula, ParsedFormula) else parse_formula(formula)
    context = context or {}

    missing = tuple(
        sorted(code for code in parsed.parameter_codes if values.get(code) is None)
        + sorted(f"@{name}" for name in parsed.context_variables if context.get(name) is None)
    )
    if missing:
        raise MissingInputError(missing)

    names = {_PARAM_PREFIX + code: _to_decimal(values[code]) for code in parsed.parameter_codes}
    names.update(
        {_CONTEXT_PREFIX + n: _to_decimal(context[n]) for n in parsed.context_variables}
    )

    with localcontext() as ctx:
        ctx.prec = CALCULATION_PRECISION
        ctx.traps[DivisionByZero] = True
        ctx.traps[InvalidOperation] = True
        try:
            return _eval(parsed.tree.body, names)
        except (DivisionByZero, ZeroDivisionError) as exc:
            raise FormulaEvaluationError("División por cero al calcular la fórmula.") from exc
        except InvalidOperation as exc:
            raise FormulaEvaluationError(
                "Operación inválida al calcular la fórmula (p. ej. raíz o potencia de un "
                "valor negativo)."
            ) from exc


def _to_decimal(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    # float → str primero: Decimal(0.1) arrastraría el error binario (regla 9).
    return Decimal(str(value))


def _eval(node: ast.AST, names: Mapping[str, Decimal]) -> Decimal:
    if isinstance(node, ast.Constant):
        return Decimal(str(node.value))
    if isinstance(node, ast.Name):
        return names[node.id]
    if isinstance(node, ast.UnaryOp):
        operand = _eval(node.operand, names)
        return -operand if isinstance(node.op, ast.USub) else +operand
    if isinstance(node, ast.BinOp):
        left = _eval(node.left, names)
        right = _eval(node.right, names)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if abs(right) > MAX_EXPONENT:
            raise FormulaEvaluationError(f"Exponente fuera de rango (máximo {MAX_EXPONENT}).")
        return left**right
    if isinstance(node, ast.Call):
        args = [_eval(arg, names) for arg in node.args]
        return _call(node.func.id, args)
    raise FormulaEvaluationError(f"Elemento no evaluable: {type(node).__name__}.")


def _call(name: str, args: list[Decimal]) -> Decimal:
    if name in ("min", "max"):
        if not args:
            raise FormulaEvaluationError(f"{name}() requiere al menos un argumento.")
        return min(args) if name == "min" else max(args)
    if name in ("sqrt", "abs"):
        if len(args) != 1:
            raise FormulaEvaluationError(f"{name}() requiere exactamente un argumento.")
        return args[0].sqrt() if name == "sqrt" else abs(args[0])
    # round(x) o round(x, n)
    if len(args) not in (1, 2):
        raise FormulaEvaluationError("round() requiere uno o dos argumentos.")
    places = int(args[1]) if len(args) == 2 else 0
    return quantize_for_display(args[0], decimals=places)


def quantize_for_display(value: Decimal, *, decimals: int) -> Decimal:
    """Redondeo clínico (mitad hacia arriba) a `decimals` posiciones. Sólo para mostrar o
    guardar el valor final; nunca para alimentar otra fórmula."""
    return value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def calculation_order(formulas: Mapping[str, str | ParsedFormula]) -> list[str]:
    """Orden topológico de los parámetros calculados. Lanza `FormulaSyntaxError` si hay un
    ciclo. Las dependencias hacia parámetros no calculados se ignoran (son insumos)."""
    parsed = {
        code: f if isinstance(f, ParsedFormula) else parse_formula(f)
        for code, f in formulas.items()
    }
    sorter = TopologicalSorter(
        {code: p.parameter_codes & parsed.keys() for code, p in parsed.items()}
    )
    try:
        return list(sorter.static_order())
    except CycleError as exc:
        cycle = " → ".join(exc.args[1]) if len(exc.args) > 1 else ""
        raise FormulaSyntaxError(f"Dependencia circular entre fórmulas: {cycle}") from exc


def evaluate_calculated_parameters(
    *,
    formulas: Mapping[str, str | ParsedFormula],
    values: Mapping[str, Decimal | None],
    context: Mapping[str, Decimal | None] | None = None,
) -> dict[str, CalculationResult]:
    """Calcula todos los parámetros de `formulas` ({código: fórmula}) en orden topológico.

    `values` trae los valores medidos ({código: Decimal | None}). Cada calculado se agrega
    a los valores disponibles para los siguientes, con precisión completa. Si falta un
    insumo o la operación falla, ese parámetro queda en `None` con su motivo — y los que
    dependen de él también — sin bloquear el resto."""
    available: dict[str, Decimal | None] = dict(values)
    results: dict[str, CalculationResult] = {}
    for code in calculation_order(formulas):
        try:
            value = evaluate_formula(formula=formulas[code], values=available, context=context)
        except MissingInputError as exc:
            results[code] = CalculationResult(
                value=None, reason=exc.message, missing=exc.missing
            )
            available[code] = None
            continue
        except FormulaEvaluationError as exc:
            results[code] = CalculationResult(value=None, reason=exc.message)
            available[code] = None
            continue
        results[code] = CalculationResult(value=value)
        available[code] = value
    return results
