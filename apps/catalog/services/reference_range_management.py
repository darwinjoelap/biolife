"""Gestión de rangos de referencia por sexo, edad y condición (Fase 08b, ADR-020).

Lógica independiente de la pantalla: la usa hoy el admin y la usará la ficha del examen
definitiva cuando exista el estilo visual.

- `find_range_issues()` (pura): solapes ambiguos, solapes que resuelve el desempate, y
  huecos de edad/sexo sin rango.
- `parameter_range_issues()`: lo mismo leyendo los rangos guardados de un parámetro.
- `explain_resolution()`: "probador" — qué rango aplicaría a un paciente y por qué se
  descartan los demás. El rango elegido es siempre el de `resolve_reference_range()`.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from apps.catalog.models import Parameter, ReferenceRange
from apps.catalog.services.reference_resolver import resolve_reference_range
from apps.core.utils.dates import format_age_days

EDAD_MAXIMA_DIAS = 54750
ERROR = "ERROR"
AVISO = "AVISO"
SEX_LABELS = dict(ReferenceRange.Sex.choices)
CONDITION_LABELS = dict(ReferenceRange.Condition.choices)


@dataclass(frozen=True)
class RangeSpec:
    """Lo mínimo de un rango para analizar cobertura (sin tocar la base de datos)."""

    sex: str
    age_min_days: int
    age_max_days: int
    condition: str = ReferenceRange.Condition.NINGUNA
    priority: int = 0
    label: str = ""

    @property
    def width(self) -> int:
        return self.age_max_days - self.age_min_days


@dataclass(frozen=True)
class RangeIssue:
    level: str  # ERROR bloquea el guardado; AVISO se informa
    message: str


def age_window_text(age_min_days: int, age_max_days: int) -> str:
    if age_max_days >= EDAD_MAXIMA_DIAS:
        return f"desde {format_age_days(age_min_days)}"
    return f"{format_age_days(age_min_days)} a {format_age_days(age_max_days)}"


def _label(spec: RangeSpec) -> str:
    base = spec.label or "rango"
    return (f"«{base}» ({SEX_LABELS.get(spec.sex, spec.sex)}, "
            f"{age_window_text(spec.age_min_days, spec.age_max_days)})")


def _sexes_overlap(a: str, b: str) -> bool:
    return a == b or ReferenceRange.Sex.ANY in (a, b)


def find_range_issues(ranges: Sequence[RangeSpec]) -> list[RangeIssue]:
    """Analiza un conjunto de rangos de UN parámetro."""
    issues: list[RangeIssue] = []
    for spec in ranges:
        if spec.age_min_days > spec.age_max_days:
            issues.append(RangeIssue(
                ERROR, f"{_label(spec)}: la edad mínima es mayor que la máxima."
            ))

    by_condition: dict[str, list[RangeSpec]] = {}
    for spec in ranges:
        by_condition.setdefault(spec.condition, []).append(spec)

    for condition, specs in by_condition.items():
        cond = CONDITION_LABELS.get(condition, condition)
        for i, a in enumerate(specs):
            for b in specs[i + 1:]:
                if not _sexes_overlap(a.sex, b.sex) or a.priority != b.priority:
                    continue  # prioridades distintas: el desempate es explícito
                start = max(a.age_min_days, b.age_min_days)
                end = min(a.age_max_days, b.age_max_days)
                if start > end:
                    continue
                if a.width == b.width:
                    issues.append(RangeIssue(ERROR, (
                        f"{_label(a)} y {_label(b)} se solapan ({age_window_text(start, end)}, "
                        f"condición {cond}) con la misma prioridad y el mismo ancho: no hay "
                        "forma de decidir cuál aplica. Suba la prioridad de uno o ajuste las "
                        "edades."
                    )))
                else:
                    winner = a if a.width < b.width else b
                    issues.append(RangeIssue(AVISO, (
                        f"{_label(a)} y {_label(b)} se solapan ({age_window_text(start, end)}, "
                        f"condición {cond}); en esas edades se usa el más estrecho: "
                        f"{_label(winner)}."
                    )))

        # Huecos: sólo para los sexos que este parámetro cubre en esta condición.
        sexes = {s.sex for s in specs}
        targets = (["M", "F"] if ReferenceRange.Sex.ANY in sexes
                   else sorted(sexes & {"M", "F"}))
        for sex in targets:
            windows = sorted(
                (s.age_min_days, s.age_max_days) for s in specs
                if s.sex in (sex, ReferenceRange.Sex.ANY)
            )
            cursor = 0
            for start, end in windows:
                if start > cursor:
                    issues.append(RangeIssue(AVISO, (
                        f"Sin rango para {SEX_LABELS[sex]} entre {format_age_days(cursor)} y "
                        f"{format_age_days(start - 1)} (condición {cond}): el informe "
                        "imprimirá la referencia vacía."
                    )))
                cursor = max(cursor, end + 1)
            if cursor <= EDAD_MAXIMA_DIAS:
                issues.append(RangeIssue(AVISO, (
                    f"Sin rango para {SEX_LABELS[sex]} desde {format_age_days(cursor)} "
                    f"(condición {cond})."
                )))
    return issues


def spec_from_range(reference_range: ReferenceRange) -> RangeSpec:
    return RangeSpec(
        sex=reference_range.sex, age_min_days=reference_range.age_min_days,
        age_max_days=reference_range.age_max_days, condition=reference_range.condition,
        priority=reference_range.priority, label=reference_range.display_text,
    )


def parameter_range_issues(*, parameter: Parameter) -> list[RangeIssue]:
    ranges = parameter.reference_ranges.filter(is_active=True)
    return find_range_issues([spec_from_range(r) for r in ranges])


@dataclass
class CandidateExplanation:
    reference_range: ReferenceRange
    applies: bool
    reason: str


@dataclass
class ResolutionExplanation:
    chosen: ReferenceRange | None
    candidates: list[CandidateExplanation] = field(default_factory=list)
    summary: str = ""


def explain_resolution(
    *, parameter: Parameter, sex: str, age_days: int,
    condition: str = ReferenceRange.Condition.NINGUNA,
) -> ResolutionExplanation:
    """Probador: qué rango aplica a (sexo, edad, condición) y por qué no los demás."""
    chosen = resolve_reference_range(
        parameter=parameter, sex=sex, age_days=age_days, condition=condition
    )
    explanation = ResolutionExplanation(chosen=chosen)
    for rr in parameter.reference_ranges.all().order_by("-priority", "age_min_days"):
        reasons = [] if rr.is_active else ["está desactivado"]
        if rr.sex not in (sex, ReferenceRange.Sex.ANY):
            reasons.append(f"es para {SEX_LABELS[rr.sex]}")
        if not rr.age_min_days <= age_days <= rr.age_max_days:
            reasons.append(f"cubre {age_window_text(rr.age_min_days, rr.age_max_days)}")
        if rr.condition != condition:
            reasons.append(f"es para la condición {CONDITION_LABELS[rr.condition]}")
        if reasons:
            explanation.candidates.append(
                CandidateExplanation(rr, False, "Descartado: " + "; ".join(reasons) + ".")
            )
        elif chosen and rr.pk == chosen.pk:
            explanation.candidates.append(CandidateExplanation(rr, True, "Aplica."))
        else:
            explanation.candidates.append(CandidateExplanation(rr, False, (
                f"También coincide, pero pierde el desempate (prioridad {rr.priority} vs "
                f"{chosen.priority}; ventana {rr.age_max_days - rr.age_min_days} vs "
                f"{chosen.age_max_days - chosen.age_min_days} días)."
            )))
    patient = (f"{SEX_LABELS.get(sex, sex)}, {format_age_days(age_days)}, "
               f"condición {CONDITION_LABELS.get(condition, condition)}")
    explanation.summary = (
        f"{patient}: se imprime «{chosen.display_text}»." if chosen
        else f"{patient}: ningún rango aplica; el informe imprimirá la referencia vacía."
    )
    return explanation
