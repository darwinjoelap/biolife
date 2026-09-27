"""Avance analítico de la orden (Fase 10): lo mueven los resultados, vía este service.

REGISTRADA/MUESTRA_TOMADA → EN_PROCESO (hay algún resultado cargado) →
RESULTADOS_CARGADOS (todos cargados) → VALIDADA (todos validados)."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.core.exceptions import ApplicationError
from apps.orders.models import Order, OrderItem
from apps.orders.services.sample_collection import refresh_order_status

ANALYTIC = (Order.Status.EN_PROCESO, Order.Status.RESULTADOS_CARGADOS, Order.Status.VALIDADA)


def set_item_status(*, item: OrderItem, status: str) -> OrderItem:
    if item.status != status:
        item.status = status
        item.save(update_fields=["status", "updated_at"])
    return item


def refresh_order_progress(order: Order) -> Order:
    if order.is_cancelled or order.status == Order.Status.ENTREGADA:
        return order
    statuses = list(order.items.exclude(status=OrderItem.Status.ANULADO)
                    .values_list("status", flat=True))
    done = {OrderItem.Status.CARGADO, OrderItem.Status.VALIDADO}
    if statuses and all(s == OrderItem.Status.VALIDADO for s in statuses):
        target = Order.Status.VALIDADA
    elif statuses and all(s in done for s in statuses):
        target = Order.Status.RESULTADOS_CARGADOS
    elif any(s != OrderItem.Status.PENDIENTE for s in statuses):
        target = Order.Status.EN_PROCESO
    else:
        if order.status in ANALYTIC:
            order.status = Order.Status.REGISTRADA
            order.save(update_fields=["status", "updated_at"])
        return refresh_order_status(order)
    if order.status != target:
        order.status = target
        order.save(update_fields=["status", "updated_at"])
    return order


@transaction.atomic
def update_clinical_data(*, order: Order, weight_kg: Decimal | None, height_cm: Decimal | None,
                         urine_volume_24h_ml: Decimal | None, patient_condition: str) -> Order:
    """Datos del episodio que usan los cálculos y los rangos (se cargan en la captura)."""
    if order.is_cancelled:
        raise ApplicationError(f"La orden {order.number} está anulada.")
    if patient_condition not in Order.Condition.values:
        raise ApplicationError("Condición del paciente no válida.")
    order.weight_kg = weight_kg
    order.height_cm = height_cm
    order.urine_volume_24h_ml = urine_volume_24h_ml
    order.patient_condition = patient_condition
    order.save(update_fields=["weight_kg", "height_cm", "urine_volume_24h_ml",
                              "patient_condition", "updated_at"])
    return order
