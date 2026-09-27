"""Numeración de órdenes y muestras (ADR-024).

Orden: `AAMMDD-NNNN`, correlativo que reinicia cada día (hasta 9.999 órdenes diarias).
Muestra: `AAMMDD-NNNN-SS`; su código de barras son los 12 dígitos sin guiones, sólo
numérico para que lo lean también los analizadores más viejos (Fase 16).
"""
import datetime

from django.db import transaction

from apps.core.exceptions import ApplicationError
from apps.orders.models import OrderNumberSequence

MAX_ORDERS_PER_DAY = 9999
MAX_SAMPLES_PER_ORDER = 99


def next_order_number(*, on_date: datetime.date) -> str:
    """Siguiente número del día. `select_for_update` evita duplicados concurrentes."""
    with transaction.atomic():
        sequence, _ = OrderNumberSequence.objects.select_for_update().get_or_create(
            day=on_date
        )
        if sequence.last_value >= MAX_ORDERS_PER_DAY:
            raise ApplicationError(
                f"Se alcanzó el máximo de {MAX_ORDERS_PER_DAY} órdenes del día "
                f"{on_date:%d/%m/%Y}."
            )
        sequence.last_value += 1
        sequence.save(update_fields=["last_value"])
    return f"{on_date:%y%m%d}-{sequence.last_value:04d}"


def sample_identifiers(*, order_number: str, sequence: int) -> tuple[str, str]:
    """(número legible, código de barras) de la muestra `sequence` de la orden."""
    if not 1 <= sequence <= MAX_SAMPLES_PER_ORDER:
        raise ApplicationError(
            f"Una orden admite hasta {MAX_SAMPLES_PER_ORDER} muestras."
        )
    number = f"{order_number}-{sequence:02d}"
    return number, number.replace("-", "")
