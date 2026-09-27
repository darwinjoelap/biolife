"""Lectura y formato de valores de resultado según `Parameter.value_type` (Fase 10).

Números como los escribe un laboratorio venezolano: coma decimal (`13,4`), punto de miles
(`150.000`), y también punto decimal (`13.4`). Un calificador `<`/`>` (`< 0,5`) se
conserva en el texto y el número se usa para marcar alto/bajo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from apps.core.exceptions import ApplicationError

VT_NUMERIC = "NUMERIC"
VT_CALCULATED = "NUMERIC_CALCULATED"
VT_OPTIONS = ("CODED", "SEMIQUANTITATIVE", "QUALITATIVE", "TITER")
VT_COUNT_RANGE = "COUNT_RANGE"
VT_NARRATIVE = "NARRATIVE"
VT_MULTI = "MULTI_CATALOG"

_THOUSANDS = re.compile(r"^-?\d{1,3}(\.\d{3})+$")
_QUALIFIED = re.compile(r"^\s*([<>]=?)\s*(.+)$")
_RANGE = re.compile(r"^\s*(\S+)\s*[-–a]\s*(\S+)\s*$")


@dataclass
class ParsedValue:
    numeric: Decimal | None = None
    text: str | None = None
    low: Decimal | None = None
    high: Decimal | None = None
    option: object = None  # catalog.CodedOption
    options: list = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return (self.numeric is None and not self.text and self.low is None
                and self.option is None and not self.options)

    @property
    def comparable(self) -> Decimal | None:
        """Número con el que se marca alto/bajo (en un conteo, el extremo superior)."""
        if self.numeric is not None:
            return self.numeric
        if self.high is not None:
            return self.high
        if self.option is not None and self.option.numeric_equivalent is not None:
            return self.option.numeric_equivalent
        return None


def parse_number(raw: str) -> Decimal:
    """'13,4' · '13.4' · '150.000' · '1.234,5' → Decimal. Lanza ValueError si no es número."""
    text = raw.strip().replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    elif _THOUSANDS.match(text):
        text = text.replace(".", "")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(raw) from exc
    if not value.is_finite():
        raise ValueError(raw)
    return value


def parse_input(parameter, raw, *, options: dict | None = None) -> ParsedValue:
    """Convierte lo que llegó del formulario en un `ParsedValue`.

    `raw`: texto (numérico, conteo, narrativo), id de opción, o lista de ids (multi).
    `options`: {str(id): CodedOption} del conjunto del parámetro."""
    vt = parameter.value_type
    options = options or {}
    if vt == VT_MULTI:
        ids = [r for r in (raw or []) if r]
        chosen = [options[i] for i in ids if i in options]
        if len(chosen) != len(ids):
            raise ApplicationError(f"{parameter.name}: opción no válida.")
        return ParsedValue(options=chosen, text=", ".join(o.value for o in chosen) or None)
    raw = (raw or "").strip()
    if not raw:
        return ParsedValue()
    if vt in VT_OPTIONS:
        if raw not in options:
            raise ApplicationError(f"{parameter.name}: opción no válida.")
        return ParsedValue(option=options[raw])
    if vt == VT_NARRATIVE:
        return ParsedValue(text=raw)
    if vt == VT_COUNT_RANGE:
        return _parse_count(parameter, raw)
    if vt == VT_NUMERIC:
        return _parse_numeric(parameter, raw)
    raise ApplicationError(f"{parameter.name}: se calcula, no se escribe.")


def _parse_numeric(parameter, raw: str) -> ParsedValue:
    qualifier = _QUALIFIED.match(raw)
    number = qualifier.group(2) if qualifier else raw
    try:
        value = parse_number(number)
    except ValueError as exc:
        raise ApplicationError(f"{parameter.name}: «{raw}» no es un número.") from exc
    text = f"{qualifier.group(1)} {number.strip()}" if qualifier else None
    return ParsedValue(numeric=value, text=text)


def _parse_count(parameter, raw: str) -> ParsedValue:
    match = _RANGE.match(raw)
    try:
        if match:
            low, high = parse_number(match.group(1)), parse_number(match.group(2))
            if low > high:
                low, high = high, low
            return ParsedValue(low=low, high=high)
        value = parse_number(raw)
        return ParsedValue(low=value, high=value)
    except ValueError:
        return ParsedValue(text=raw.upper())  # "INCONTABLES", "ESCASOS"...


def format_number(value: Decimal | None, *, decimals: int) -> str:
    """Formato de informe: coma decimal y punto de miles (150.000 · 13,4)."""
    if value is None:
        return ""
    quantized = value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    text = f"{quantized:,.{decimals}f}"
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def format_value(value) -> str:
    """Texto de un `ResultValue` tal como se muestra/imprime."""
    parameter = value.parameter
    vt = parameter.value_type
    if vt in VT_OPTIONS:
        return value.coded_option.value if value.coded_option else ""
    if vt in (VT_MULTI, VT_NARRATIVE):
        return value.value_text or ""
    if vt == VT_COUNT_RANGE:
        if value.value_low is None:
            return value.value_text or ""
        low = format_number(value.value_low, decimals=0)
        high = format_number(value.value_high, decimals=0)
        return low if low == high else f"{low} - {high}"
    if value.value_text:  # "< 0,5"
        return value.value_text
    return format_number(value.value_numeric, decimals=parameter.decimals)


def input_text(value) -> str:
    """Lo que se vuelve a mostrar en el campo de captura."""
    if value is None:
        return ""
    vt = value.parameter.value_type
    if vt in VT_OPTIONS:
        return str(value.coded_option_id or "")
    if vt == VT_NUMERIC and value.value_numeric is not None and not value.value_text:
        text = format_number(value.value_numeric, decimals=value.parameter.decimals)
        return text
    return format_value(value)
