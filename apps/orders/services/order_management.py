"""Cambios sobre una orden registrada: agregar exámenes, cobrar y anular."""
from __future__ import annotations

from collections.abc import Sequence

from django.db import transaction
from django.utils import timezone

from apps.billing.selectors.price_queries import (
    currency_by_code,
    default_price_list,
    discounts_by_codes,
    price_list_by_code,
)
from apps.core.exceptions import ApplicationError
from apps.orders.models import Order, OrderItem, Sample
from apps.orders.services.order_creation import apply_draft_totals, build_draft, expand_items
from apps.orders.services.sample_collection import PRE_ANALYTIC, refresh_order_status
from apps.orders.services.sample_planning import assign_samples


def _check_editable(order: Order) -> None:
    if order.is_cancelled:
        raise ApplicationError(f"La orden {order.number} está anulada.")
    if order.status not in PRE_ANALYTIC:
        raise ApplicationError(
            f"La orden {order.number} ya está {order.get_status_display().lower()}: no se "
            "puede modificar."
        )


def _requote(order: Order, *, tests, profiles):
    """Cotización de la orden con su misma lista, descuentos y moneda de referencia."""
    snapshot = order.quote_snapshot or {}
    on_date = timezone.localdate(order.ordered_at)
    price_list = (price_list_by_code(code=order.price_list_code) if order.price_list_code
                  else default_price_list(on_date=on_date))
    return build_draft(
        tests=tests, profiles=profiles, price_list=price_list,
        discounts=discounts_by_codes(codes=[d["code"] for d in snapshot.get("discounts", [])]),
        reference_currency=(currency_by_code(code=order.converted_currency_code)
                            if order.converted_currency_code else None),
        on_date=on_date, authorized=True, weight_kg=order.weight_kg,
        height_cm=order.height_cm, urine_volume_24h_ml=order.urine_volume_24h_ml,
    )


def requote_pending(*, order: Order) -> list[str]:
    """Vuelve a cotizar una orden que quedó con **precio pendiente** (se cargaron los
    precios después de registrarla). Una orden ya cotizada no se toca: su precio está
    congelado (ADR-024)."""
    if order.is_cancelled:
        raise ApplicationError(f"La orden {order.number} está anulada.")
    if not order.pricing_pending:
        raise ApplicationError("La orden ya tiene su precio: no se recotiza.")
    items = list(order.items.exclude(status=OrderItem.Status.ANULADO)
                 .select_related("test", "profile"))
    profiles = list({i.profile.id: i.profile for i in items if i.profile}.values())
    draft = _requote(order, tests=[i.test for i in items if i.profile is None],
                     profiles=profiles)
    apply_draft_totals(order, draft)
    order.save()
    if order.pricing_pending:
        missing = ", ".join(order.quote_snapshot.get("missing_prices", []))
        raise ApplicationError(f"Siguen faltando precios en la lista: {missing}.")
    return draft.warnings


def add_to_order(*, order: Order, tests: Sequence = (), profiles: Sequence = (),
                 user=None) -> list[str]:
    """Agrega exámenes/perfiles, recotiza la orden completa y asigna tubos: los nuevos
    exámenes entran en un tubo por tomar compatible o en uno nuevo."""
    _check_editable(order)
    items = list(order.items.select_related("test", "profile"))
    present = {item.test_id for item in items}
    old_profiles = list({i.profile.id: i.profile for i in items if i.profile}.values())
    old_tests = [i.test for i in items if i.profile is None]

    candidates, warnings = expand_items(tests=tests, profiles=profiles)
    new = [(test, profile) for test, profile in candidates if test.id not in present]
    if not new:
        raise ApplicationError("Los exámenes elegidos ya están en la orden.")

    draft = _requote(order, tests=old_tests + [t for t in tests if t.id not in present],
                     profiles=old_profiles + list(profiles))
    previous_total = order.total
    with transaction.atomic():
        start = len(items)
        created = [
            OrderItem.objects.create(order=order, test=test, profile=profile,
                                     order_index=start + index, created_by=user)
            for index, (test, profile) in enumerate(new)
        ]
        warnings += assign_samples(order=order, items=created, created_by=user)
        apply_draft_totals(order, draft)
        if order.is_paid and order.total != previous_total:
            order.is_paid = False
            order.paid_at = None
            order.paid_by = None
            warnings.append("El total cambió: la orden queda con saldo por cobrar.")
        order.save()
        refresh_order_status(order)
    return warnings + [w for w in draft.warnings if w not in warnings]


def mark_paid(*, order: Order, user=None) -> Order:
    if order.is_cancelled:
        raise ApplicationError(f"La orden {order.number} está anulada.")
    if order.pricing_pending:
        raise ApplicationError(
            "La orden tiene precios pendientes: cargue los precios y recotice antes de "
            "registrar el pago."
        )
    if not order.is_paid:
        order.is_paid = True
        order.paid_at = timezone.now()
        order.paid_by = user
        order.save(update_fields=["is_paid", "paid_at", "paid_by", "updated_at"])
    return order


def cancel_order(*, order: Order, reason: str, user=None) -> Order:
    """Anula (nunca borra). Sólo antes de que haya resultados."""
    _check_editable(order)
    reason = (reason or "").strip()
    if not reason:
        raise ApplicationError("Indique el motivo de la anulación.")
    with transaction.atomic():
        order.status = Order.Status.ANULADA
        order.cancelled_at = timezone.now()
        order.cancelled_by = user
        order.cancel_reason = reason
        order.save(update_fields=["status", "cancelled_at", "cancelled_by",
                                  "cancel_reason", "updated_at"])
        order.items.update(status=OrderItem.Status.ANULADO)
        order.samples.filter(status=Sample.Status.PENDIENTE).update(
            status=Sample.Status.RECHAZADA, rejection_reason="Orden anulada",
            rejected_at=order.cancelled_at, rejected_by=user,
        )
    return order


def mark_delivered(*, order: Order, user=None) -> Order:
    """Entrega del informe final (Fase 11): sólo con todos los exámenes validados. Un
    informe parcial se puede enviar sin marcar la orden como entregada."""
    if order.is_cancelled:
        raise ApplicationError(f"La orden {order.number} está anulada.")
    if order.status == Order.Status.ENTREGADA:
        return order
    if order.status != Order.Status.VALIDADA:
        raise ApplicationError(
            "Sólo se marca entregada una orden con todos sus exámenes validados.")
    order.status = Order.Status.ENTREGADA
    order.delivered_at = timezone.now()
    order.delivered_by = user
    order.save(update_fields=["status", "delivered_at", "delivered_by", "updated_at"])
    return order
