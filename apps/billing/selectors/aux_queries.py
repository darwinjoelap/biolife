"""Consultas de monedas y descuentos para sus pantallas (Fase 11d)."""
from django.db.models import Count, Q

from apps.billing.models import Currency, Discount


def _filter(qs, *, show_inactive, query, fields):
    if not show_inactive:
        qs = qs.filter(is_active=True)
    if query:
        condition = Q()
        for name in fields:
            condition |= Q(**{f"{name}__icontains": query.strip()})
        qs = qs.filter(condition)
    return qs


def currencies(*, show_inactive=False, query=""):
    qs = Currency.objects.annotate(
        list_count=Count("price_lists", filter=Q(price_lists__is_active=True)))
    return _filter(qs, show_inactive=show_inactive, query=query,
                   fields=("code", "name", "symbol")).order_by("order_index", "code")


def discounts(*, show_inactive=False, query=""):
    qs = Discount.objects.select_related("currency").annotate(
        target_count=Count("tests", distinct=True) + Count("profiles", distinct=True))
    return _filter(qs, show_inactive=show_inactive, query=query,
                   fields=("code", "name")).order_by("order_index", "name")
