"""Etiquetas de plantilla del sistema visual (Fase 08d, ADR-022).

- `{% icon "house" %}`: ícono del sprite `components/icons.html`.
- `{% field form.campo "col-3" %}`: campo con etiqueta, ayuda y error, en la grilla densa.
- `{{ user|initials }}`, `{% nav_active request "prefijo/" %}`.
"""
from django import template
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def icon(name: str, extra_class: str = "") -> str:
    classes = f"icon {extra_class}".strip()
    return format_html(
        '<svg class="{}" aria-hidden="true" focusable="false"><use href="#i-{}"></use></svg>',
        classes, name,
    )


@register.inclusion_tag("components/field.html")
def field(bound_field, col: str = "col-3"):
    return {"field": bound_field, "col": col}


@register.filter
def initials(user) -> str:
    full_name = (user.get_full_name() or "").strip() if user else ""
    source = full_name or getattr(user, "email", "") or getattr(user, "username", "") or "?"
    parts = [p for p in source.replace("@", " ").replace(".", " ").split() if p]
    return "".join(p[0] for p in parts[:2]).upper() or "?"


@register.simple_tag
def nav_active(request, prefix: str) -> str:
    """'is-active' si la ruta actual empieza por `prefix` ("/" sólo coincide exacto)."""
    path = getattr(request, "path", "")
    if prefix == "/":
        return "is-active" if path == "/" else ""
    return "is-active" if path.startswith(prefix) else ""
