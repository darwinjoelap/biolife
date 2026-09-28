"""Gráficos de evolución en SVG propio (Fase 11e, ADR-032).

`line_chart()` calcula la geometría una sola vez (en puntos, eje Y hacia abajo como en
SVG); `chart_svg()` la dibuja para la pantalla y el PDF la redibuja con ReportLab con los
mismos números, así ambos se ven iguales. Sin librerías de JS ni de gráficos.

- Eje X proporcional al tiempo (fecha de la orden).
- Banda sombreada con el rango de referencia **vigente en cada punto** (puede cambiar con
  la edad o el sexo): escalones entre puntos.
- Puntos coloreados por marca (alto, bajo, crítico) con `<title>` para el tooltip.
"""
from __future__ import annotations

import datetime
import math
from dataclasses import dataclass, field

from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe


@dataclass
class ChartPoint:
    when: datetime.date
    value: float
    flag: str = ""
    label: str = ""          # texto del tooltip
    low: float | None = None
    high: float | None = None


@dataclass
class Chart:
    width: float
    height: float
    left: float
    right: float
    top: float
    bottom: float
    points: list[tuple[float, float, ChartPoint]] = field(default_factory=list)
    bands: list[tuple[float, float, float, float]] = field(default_factory=list)  # x,y,w,h
    y_ticks: list[tuple[float, str]] = field(default_factory=list)
    x_ticks: list[tuple[float, str]] = field(default_factory=list)
    unit: str = ""


def nice_ticks(low: float, high: float, count: int = 5) -> list[float]:
    """Marcas «redondas» (1, 2, 2,5, 5 × 10ⁿ) que cubren [low, high]."""
    if math.isclose(low, high):
        low, high = low - 1, high + 1
    raw = (high - low) / max(count - 1, 1)
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    start = math.floor(low / step) * step
    ticks, value = [], start
    while value <= high + step * 0.5:
        ticks.append(round(value, 10))
        value += step
    return ticks


def fmt_number(value: float, decimals: int | None = None) -> str:
    """Número con coma decimal (es-VE)."""
    if decimals is None:
        decimals = 0 if float(value).is_integer() else (1 if abs(value) >= 10 else 2)
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def line_chart(points: list[ChartPoint], *, width: float = 720, height: float = 260,
               unit: str = "", decimals: int | None = None) -> Chart:
    chart = Chart(width=width, height=height, left=52, right=16, top=14, bottom=30,
                  unit=unit)
    if not points:
        return chart
    points = sorted(points, key=lambda p: p.when)
    candidates = [p.value for p in points]
    for p in points:
        candidates += [v for v in (p.low, p.high) if v is not None]
    ticks = nice_ticks(min(candidates), max(candidates))
    y_min, y_max = ticks[0], ticks[-1]
    plot_w = width - chart.left - chart.right
    plot_h = height - chart.top - chart.bottom

    def y_of(value: float) -> float:
        value = min(max(value, y_min), y_max)
        return chart.top + plot_h * (1 - (value - y_min) / (y_max - y_min))

    first, last = points[0].when, points[-1].when
    span = (last - first).days

    def x_of(when: datetime.date) -> float:
        if span == 0:
            return chart.left + plot_w / 2
        pad = plot_w * 0.04
        return chart.left + pad + (plot_w - 2 * pad) * (when - first).days / span

    chart.y_ticks = [(y_of(t), fmt_number(t, decimals)) for t in ticks]
    chart.points = [(x_of(p.when), y_of(p.value), p) for p in points]

    # Banda de referencia: un escalón por punto, hasta la mitad del camino al vecino.
    xs = [x for x, _, _ in chart.points]
    for index, (x, _, p) in enumerate(chart.points):
        if p.low is None and p.high is None:
            continue
        x0 = chart.left if index == 0 else (xs[index - 1] + x) / 2
        x1 = chart.left + plot_w if index == len(xs) - 1 else (x + xs[index + 1]) / 2
        top = y_of(p.high if p.high is not None else y_max)
        bottom = y_of(p.low if p.low is not None else y_min)
        chart.bands.append((x0, top, x1 - x0, bottom - top))

    # Fechas del eje X: primera, última y hasta 3 intermedias sin encimarse.
    chosen: list[tuple[float, str]] = []
    for x, _, p in chart.points:
        if not chosen or x - chosen[-1][0] >= 70:
            chosen.append((x, p.when.strftime("%d/%m/%y")))
    if chosen and chosen[-1][0] != xs[-1]:
        if xs[-1] - chosen[-1][0] < 70:
            chosen.pop()
        chosen.append((xs[-1], points[-1].when.strftime("%d/%m/%y")))
    chart.x_ticks = chosen
    return chart


def _flag_class(flag: str) -> str:
    return {"ALTO": "hi", "CRITICO_ALTO": "crit", "BAJO": "lo", "CRITICO_BAJO": "crit",
            "ANORMAL": "hi"}.get(flag, "ok")


def chart_svg(chart: Chart, *, label: str = "Evolución") -> SafeString:
    """SVG accesible; colores por clases CSS (`.chart__*`) para respetar el tema."""
    w, h = chart.width, chart.height
    parts = [f'<svg class="chart" viewBox="0 0 {w:g} {h:g}" role="img" '
             f'aria-label="{escape(label)}" preserveAspectRatio="xMidYMid meet">']
    for x, y, bw, bh in chart.bands:
        parts.append(f'<rect class="chart__band" x="{x:.1f}" y="{y:.1f}" '
                     f'width="{bw:.1f}" height="{max(bh, 0.5):.1f}"/>')
    for y, text in chart.y_ticks:
        parts.append(f'<line class="chart__grid" x1="{chart.left}" x2="{w - chart.right}" '
                     f'y1="{y:.1f}" y2="{y:.1f}"/>')
        parts.append(f'<text class="chart__tick" x="{chart.left - 8}" y="{y + 4:.1f}" '
                     f'text-anchor="end">{escape(text)}</text>')
    base = h - chart.bottom
    for x, text in chart.x_ticks:
        parts.append(f'<text class="chart__tick" x="{x:.1f}" y="{base + 18:.1f}" '
                     f'text-anchor="middle">{escape(text)}</text>')
    if chart.unit:
        parts.append(f'<text class="chart__tick" x="4" y="{chart.top - 2}">'
                     f'{escape(chart.unit)}</text>')
    if len(chart.points) > 1:
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in chart.points)
        parts.append(f'<polyline class="chart__line" points="{path}"/>')
    for x, y, p in chart.points:
        parts.append(f'<circle class="chart__pt chart__pt--{_flag_class(p.flag)}" '
                     f'cx="{x:.1f}" cy="{y:.1f}" r="4.5"><title>{escape(p.label)}</title>'
                     f'</circle>')
    parts.append("</svg>")
    return mark_safe("".join(parts))  # noqa: S308 - todo texto pasa por escape()


def sparkline_svg(values: list[float], flags: list[str], *, width: int = 120,
                  height: int = 30, low: float | None = None,
                  high: float | None = None) -> SafeString:
    """Mini-gráfico sin ejes para el panel de tendencias."""
    if not values:
        return mark_safe("")
    candidates = values + [v for v in (low, high) if v is not None]
    y_min, y_max = min(candidates), max(candidates)
    if math.isclose(y_min, y_max):
        y_min, y_max = y_min - 1, y_max + 1
    pad = 3

    def y_of(value: float) -> float:
        return pad + (height - 2 * pad) * (1 - (value - y_min) / (y_max - y_min))

    step = (width - 2 * pad) / max(len(values) - 1, 1)
    coords = [(pad + i * step if len(values) > 1 else width / 2, y_of(v))
              for i, v in enumerate(values)]
    parts = [f'<svg class="spark" viewBox="0 0 {width} {height}" width="{width}" '
             f'height="{height}" aria-hidden="true">']
    if low is not None or high is not None:
        top = y_of(high if high is not None else y_max)
        bottom = y_of(low if low is not None else y_min)
        parts.append(f'<rect class="chart__band" x="0" y="{top:.1f}" width="{width}" '
                     f'height="{max(bottom - top, 0.5):.1f}"/>')
    if len(coords) > 1:
        parts.append('<polyline class="chart__line" points="'
                     + " ".join(f"{x:.1f},{y:.1f}" for x, y in coords) + '"/>')
    x, y = coords[-1]
    parts.append(f'<circle class="chart__pt chart__pt--{_flag_class(flags[-1])}" '
                 f'cx="{x:.1f}" cy="{y:.1f}" r="3"/></svg>')
    return mark_safe("".join(parts))  # noqa: S308 - sólo números

