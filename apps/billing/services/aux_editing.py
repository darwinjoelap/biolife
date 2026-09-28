"""Guardado de monedas y descuentos (Fase 11d, ADR-031). Nada se borra; toda edición
queda en la bitácora."""
from __future__ import annotations

from django.db import transaction

from apps.accounts.services.audit import log_action
from apps.billing.models import Currency, Discount
from apps.core.exceptions import ApplicationError


def _log(obj, by, form, created: bool) -> None:
    if created or form.changed_data:
        log_action(action="TABLA_CREADA" if created else "TABLA_MODIFICADA", user=by,
                   model_name=f"billing.{type(obj).__name__}", object_id=str(obj.pk),
                   changes={"campos": form.changed_data} if form.changed_data else None)


@transaction.atomic
def save_currency(*, form, formsets=(), by=None) -> Currency:
    """Una moneda nueva nunca es la base; la base no se desactiva, ni una moneda con
    listas de precios activas."""
    created = form.instance._state.adding
    currency = form.save(commit=False)
    if created:
        currency.is_base = False
    if not currency.is_active:
        if currency.is_base:
            raise ApplicationError("La moneda base no se puede desactivar.")
        if currency.pk and currency.price_lists.filter(is_active=True).exists():
            raise ApplicationError("Hay listas de precios activas en esta moneda: "
                                   "desactívelas primero.")
    currency.save()
    _log(currency, by, form, created)
    return currency


@transaction.atomic
def save_discount(*, form, formsets=(), by=None) -> Discount:
    created = form.instance._state.adding
    discount = form.save()
    _log(discount, by, form, created)
    return discount
