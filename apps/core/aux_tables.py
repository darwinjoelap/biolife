"""Tablas auxiliares sin /admin (Fase 11d, ADR-031).

Motor genérico: cada app de dominio describe sus tablas pequeñas (secciones, unidades,
tubos, monedas...) con un `AuxTable` y lo registra en su `AppConfig.ready()`. `core`
pone las pantallas (índice, lista y ficha) sin conocer ningún modelo: todo lo específico
— consulta, formulario, detalle, permisos, guardado con bitácora — lo aporta la app.

Nada se borra: los registros se desactivan (`is_active`).
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

REGISTRY: dict[str, AuxTable] = {}


@dataclass
class AuxTable:
    key: str                      # slug en la URL: /tablas/<key>/
    title: str                    # «Unidades»
    singular: str                 # «unidad»
    icon: str
    group: str                    # agrupa las tarjetas del índice
    description: str
    form_class: type
    queryset: Callable[..., Any]  # (show_inactive: bool, query: str) -> iterable
    get: Callable[[Any], Any]     # pk -> instancia (lanza DoesNotExist/ValidationError)
    new: Callable[[], Any]        # instancia vacía para «Nuevo»
    columns: list[str]            # encabezados de la lista
    row: Callable[[Any], list]    # instancia -> celdas (texto o html seguro)
    save: Callable[..., Any]      # (form, formsets, by) -> instancia
    can_view: Callable[[Any], bool]
    can_edit: Callable[[Any], bool]
    editors: str                  # «Administrador y bioanalista», se muestra en el índice
    count: Callable[[], int] = lambda: 0
    form_kwargs: Callable[[Any], dict] = lambda instance: {}
    formsets: Callable[..., list] = lambda data, instance: []  # [(título, formset, ayuda)]
    layout: dict[str, str] = field(default_factory=dict)       # campo -> "col-3"
    note: str = ""                # aviso bajo el formulario
    allow_new: bool = True


def register(*tables: AuxTable) -> None:
    for table in tables:
        REGISTRY[table.key] = table


def get_table(key: str) -> AuxTable | None:
    return REGISTRY.get(key)


def visible_tables(user) -> list[tuple[str, list[AuxTable]]]:
    """Tablas que el usuario puede consultar, agrupadas en el orden de registro."""
    groups: dict[str, list[AuxTable]] = {}
    for table in REGISTRY.values():
        if table.can_view(user):
            groups.setdefault(table.group, []).append(table)
    return list(groups.items())
