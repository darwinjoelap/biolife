"""Marcas visuales de resultados."""
from django import template
from django.utils.html import format_html

from apps.results.services.evolution_chart import delta_text

register = template.Library()

FLAGS = {
    "ALTO": ("flag flag--alto", "↑ ALTO"),
    "BAJO": ("flag flag--bajo", "↓ BAJO"),
    "CRITICO_ALTO": ("flag flag--critico", "CRÍTICO ↑"),
    "CRITICO_BAJO": ("flag flag--critico", "CRÍTICO ↓"),
    "ANORMAL": ("flag flag--anormal", "ANORMAL"),
}


@register.filter
def flag_badge(flag: str):
    if flag not in FLAGS:
        return ""
    css, text = FLAGS[flag]
    return format_html('<span class="{}">{}</span>', css, text)


@register.filter
def value_class(flag: str) -> str:
    return {"ALTO": "value-alto", "BAJO": "value-bajo", "CRITICO_ALTO": "value-critico",
            "CRITICO_BAJO": "value-critico"}.get(flag, "")


@register.filter
def delta(value):
    """Variación en % con flecha (evolución y valor anterior, Fase 11e)."""
    if value is None or abs(value) < 0.05:
        return ""
    name, css = ("arrow-up", "delta--up") if value > 0 else ("arrow-down", "delta--down")
    return format_html('<span class="delta {}"><svg class="icon" aria-hidden="true">'
                       '<use href="#i-{}"></use></svg> {}</span>', css, name, delta_text(value))
