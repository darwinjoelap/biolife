"""Gráficos de la evolución de un parámetro (Fase 11e): series → geometría de
`core.charts`, para pantalla (SVG) y para el PDF (ReportLab)."""
from __future__ import annotations

from apps.core.charts import (
    Chart,
    ChartPoint,
    chart_svg,
    fmt_number,
    line_chart,
    sparkline_svg,
)

FLAG_TEXT = {"ALTO": "alto", "BAJO": "bajo", "CRITICO_ALTO": "crítico alto",
             "CRITICO_BAJO": "crítico bajo", "ANORMAL": "anormal"}


def _f(value):
    return float(value) if value is not None else None


def _label(point, unit: str) -> str:
    flag = FLAG_TEXT.get(point.flag, "")
    text = f"{point.when:%d/%m/%Y} · {point.text} {unit}".strip()
    return f"{text} ({flag})" if flag else text


def build_chart(series: dict, *, width: float = 720, height: float = 260) -> Chart:
    parameter = series["parameter"]
    unit = parameter.unit.symbol if parameter.unit_id else ""
    points = [ChartPoint(when=p.when, value=float(p.value), flag=p.flag,
                         label=_label(p, unit), low=_f(p.low), high=_f(p.high))
              for p in series["points"]]
    return line_chart(points, width=width, height=height, unit=unit,
                      decimals=parameter.decimals if parameter.decimals <= 3 else None)


def series_svg(series: dict):
    return chart_svg(build_chart(series), label=f"Evolución de {series['parameter'].name}")


def series_sparkline(series: dict):
    points = series["points"]
    last = points[-1]
    return sparkline_svg([float(p.value) for p in points], [p.flag for p in points],
                         low=_f(last.low), high=_f(last.high))


def delta_text(delta_pct: float | None) -> str:
    if delta_pct is None:
        return ""
    sign = "+" if delta_pct > 0 else ""
    return f"{sign}{fmt_number(delta_pct, 1)} %"


def trend_cards(series_list: list[dict], *, suggested_ids: list[str],
                limit: int = 12) -> list[dict]:
    """Panel de tendencias de la ficha: primero lo que piden sus antecedentes (aunque
    tenga un solo valor), luego cualquier parámetro con 2 o más resultados."""
    cards = []
    for series in series_list:
        pid = str(series["parameter"].pk)
        suggested = pid in suggested_ids
        if not suggested and len(series["points"]) < 2:
            continue
        last = series["points"][-1]
        cards.append({"parameter": series["parameter"], "suggested": suggested,
                      "last": last, "count": len(series["points"]),
                      "delta": delta_text(last.delta_pct),
                      "spark": series_sparkline(series)})
    cards.sort(key=lambda c: (not c["suggested"],
                              suggested_ids.index(str(c["parameter"].pk))
                              if c["suggested"] else 0))
    return cards[:limit]
