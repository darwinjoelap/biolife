"""Marcas visuales de resultados."""
from django import template
from django.utils.html import format_html

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
