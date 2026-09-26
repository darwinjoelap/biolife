import datetime

from django.db.models import Q, QuerySet

from apps.billing.models import PriceList, PriceListItem


def valid_price_lists(*, on_date: datetime.date) -> QuerySet[PriceList]:
    """Listas activas y vigentes en `on_date`, en el orden definido por el laboratorio."""
    return (
        PriceList.objects.filter(is_active=True)
        .filter(Q(valid_from__isnull=True) | Q(valid_from__lte=on_date))
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=on_date))
        .select_related("currency")
    )


def default_price_list(*, on_date: datetime.date) -> PriceList | None:
    return valid_price_lists(on_date=on_date).filter(is_default=True).first()


def price_list_items(*, price_list: PriceList) -> QuerySet[PriceListItem]:
    """Precios de una lista en el orden de presentación (`order_index`)."""
    return (
        price_list.items.filter(is_active=True)
        .select_related("test", "test__section", "profile")
        .order_by("order_index", "test__name", "profile__name")
    )
