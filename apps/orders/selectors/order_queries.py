"""Consultas de órdenes y muestras."""
from __future__ import annotations

import datetime

from django.db.models import Count, Prefetch, Q, QuerySet
from django.utils import timezone

from apps.orders.models import Order, OrderItem, Sample


def _day_bounds(day: datetime.date):
    start = timezone.make_aware(datetime.datetime.combine(day, datetime.time.min))
    return start, start + datetime.timedelta(days=1)


def order_list(*, day: datetime.date | None = None, status: str = "", query: str = "",
               pending_only: bool = False) -> QuerySet[Order]:
    """Órdenes del día, más recientes primero. Con búsqueda, o con `pending_only`
    (muestras por tomar, lista de trabajo de la toma), de cualquier día."""
    orders = Order.objects.select_related("patient").annotate(
        pending_samples=Count("samples", filter=Q(samples__status=Sample.Status.PENDIENTE),
                              distinct=True),
        item_count=Count("items", distinct=True),
    )
    query = query.strip()
    if query:
        digits = query.replace("-", "")
        orders = orders.filter(
            Q(number__icontains=query) | Q(samples__barcode=digits)
            | Q(patient__document_number__icontains=query)
            | Q(patient__first_name__icontains=query)
            | Q(patient__last_name__icontains=query)
            | Q(patient__internal_code__icontains=query)
        ).distinct()
    elif pending_only:
        orders = orders.filter(samples__status=Sample.Status.PENDIENTE).exclude(
            status=Order.Status.ANULADA).distinct()
    elif day is not None:
        start, end = _day_bounds(day)
        orders = orders.filter(ordered_at__gte=start, ordered_at__lt=end)
    if status:
        orders = orders.filter(status=status)
    return orders.order_by("-ordered_at")


def order_detail(*, pk) -> Order:
    return (
        Order.objects.select_related("patient", "created_by", "paid_by", "cancelled_by")
        .prefetch_related(
            Prefetch("items", queryset=OrderItem.objects.select_related(
                "test", "test__section", "profile").order_by("order_index")),
            Prefetch("samples", queryset=Sample.objects.select_related(
                "container_type", "collected_by", "rejected_by", "replaces")
                .prefetch_related(Prefetch("order_items", queryset=OrderItem.objects
                                           .select_related("test")))
                .order_by("sequence")),
        )
        .get(pk=pk)
    )


def samples_for_labels(*, order: Order, sample_ids=None) -> list[Sample]:
    """Muestras a imprimir: las indicadas, o todas las no rechazadas."""
    samples = Sample.objects.filter(order=order).select_related(
        "container_type", "order", "order__patient").prefetch_related(
        Prefetch("order_items", queryset=OrderItem.objects.select_related("test"))
    ).order_by("sequence")
    if sample_ids:
        return list(samples.filter(id__in=sample_ids))
    return list(samples.exclude(status=Sample.Status.RECHAZADA))


def sample_of_order(*, order: Order, pk) -> Sample:
    return order.samples.select_related("order", "container_type").get(pk=pk)


def find_order_by_code(*, code: str) -> Order | None:
    """Número de orden o de muestra, con o sin guiones (lo que teclea un lector)."""
    digits = code.strip().replace("-", "")
    if not digits:
        return None
    sample = Sample.objects.select_related("order").filter(barcode=digits).first()
    if sample:
        return sample.order
    if len(digits) == 10:
        return Order.objects.filter(number=f"{digits[:6]}-{digits[6:]}").first()
    return None


def day_summary(*, day: datetime.date) -> dict:
    start, end = _day_bounds(day)
    orders = Order.objects.filter(ordered_at__gte=start, ordered_at__lt=end).exclude(
        status=Order.Status.ANULADA
    )
    return {
        "orders": orders.count(),
        "pending_samples": Sample.objects.filter(
            order__in=orders, status=Sample.Status.PENDIENTE
        ).count(),
        "urgent": orders.filter(priority=Order.Priority.URGENTE).count(),
        "unpaid": orders.filter(is_paid=False).count(),
    }


def items_for_results(*, order: Order) -> list[OrderItem]:
    """Exámenes vigentes de la orden con sus tubos (captura de resultados, Fase 10)."""
    return list(
        order.items.exclude(status=OrderItem.Status.ANULADO)
        .select_related("test", "test__section", "profile")
        .prefetch_related("samples")
        .order_by("test__section__order_index", "order_index")
    )


def get_order(*, pk) -> Order:
    return Order.objects.select_related("patient").get(pk=pk)


WORKLIST_STATUSES = {
    "por_cargar": (OrderItem.Status.PENDIENTE, OrderItem.Status.EN_PROCESO),
    "por_validar": (OrderItem.Status.CARGADO,),
    "validados": (OrderItem.Status.VALIDADO,),
}


def results_worklist(*, status: str = "por_cargar", section_id: str = "",
                     query: str = "") -> QuerySet[OrderItem]:
    """Bandeja de resultados (Fase 10): exámenes por cargar, por validar o validados;
    urgentes y más antiguos primero. Excluye órdenes anuladas."""
    items = (
        OrderItem.objects.filter(status__in=WORKLIST_STATUSES.get(
            status, WORKLIST_STATUSES["por_cargar"]))
        .exclude(order__status=Order.Status.ANULADA)
        .select_related("order__patient", "test__section")
        .prefetch_related("samples")
    )
    if section_id:
        items = items.filter(test__section_id=section_id)
    query = query.strip()
    if query:
        items = items.filter(
            Q(order__number__icontains=query) | Q(order__patient__last_name__icontains=query)
            | Q(order__patient__first_name__icontains=query)
            | Q(order__patient__document_number__icontains=query)
        )
    if status == "validados":
        return items.order_by("-updated_at")[:200]
    return items.order_by("-order__priority", "order__ordered_at", "order_index")


def results_worklist_counts() -> dict:
    items = OrderItem.objects.exclude(order__status=Order.Status.ANULADA)
    return {key: items.filter(status__in=statuses).count()
            for key, statuses in WORKLIST_STATUSES.items() if key != "validados"}
