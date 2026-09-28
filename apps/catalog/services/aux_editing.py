"""Guardado de las tablas auxiliares del catálogo (Fase 11d, ADR-031).

Nada se borra (hay exámenes, resultados e informes que las referencian): se desactiva.
Toda edición queda en la bitácora con los campos que cambiaron.
"""
from __future__ import annotations

from django.db import transaction

from apps.accounts.services.audit import log_action
from apps.catalog.models import ReagentLot
from apps.core.exceptions import ApplicationError


def _changed(form, formsets) -> dict:
    changes = {}
    if form.changed_data:
        changes["campos"] = form.changed_data
    if any(f.has_changed() for fs in formsets for f in fs.forms):
        changes["detalle"] = True
    return changes


def _log(obj, by, changes, created: bool) -> None:
    if created or changes:
        log_action(action="TABLA_CREADA" if created else "TABLA_MODIFICADA", user=by,
                   model_name=f"catalog.{type(obj).__name__}", object_id=str(obj.pk),
                   changes=changes or None)


@transaction.atomic
def save_record(*, form, formsets=(), by=None):
    """Registro simple (sección, unidad, método, observación, tubo) y sus filas hijas."""
    created = form.instance._state.adding
    obj = form.save()
    for formset in formsets:
        formset.instance = obj
        formset.save()
    _log(obj, by, _changed(form, formsets), created)
    return obj


@transaction.atomic
def save_option_set(*, form, formsets=(), by=None):
    """Lista de opciones con sus opciones; debe quedar al menos una activa."""
    obj = save_record(form=form, formsets=formsets, by=by)
    if obj.is_active and not obj.options.filter(is_active=True).exists():
        raise ApplicationError("Agregue al menos una opción activa a la lista.")
    return obj


@transaction.atomic
def save_lot(*, form, formsets=(), by=None) -> ReagentLot:
    """Lote de reactivo. Si queda vigente, el vigente anterior del mismo reactivo deja de
    serlo (los resultados ya guardados conservan el lote y el ISI con que se calcularon)."""
    created = form.instance._state.adding
    lot = form.save(commit=False)
    if lot.is_current:
        (ReagentLot.objects.filter(reagent=lot.reagent, is_current=True)
         .exclude(pk=lot.pk).update(is_current=False))
    lot.save()
    _log(lot, by, _changed(form, formsets), created)
    return lot
