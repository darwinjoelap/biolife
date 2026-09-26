"""Mantenimiento de listas de precios: fijar precios, ajuste masivo, copia entre listas
(incluso a otra moneda) y orden de presentación."""
import datetime
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from apps.billing.models import Currency, PriceList, PriceListItem
from apps.billing.services.exchange import get_exchange_rate, round_money
from apps.core.exceptions import ApplicationError

HUNDRED = Decimal(100)


def _round(amount: Decimal, *, currency: Currency, round_to: Decimal | None) -> Decimal:
    """Redondea a los decimales de la moneda o, si se pide, al múltiplo `round_to` más
    cercano (0.50, 1, 5, 100...) — útil para precios "redondos" en bolívares."""
    if round_to:
        if round_to <= 0:
            raise ApplicationError("El redondeo debe ser mayor que cero.")
        steps = (amount / round_to).quantize(Decimal(1), rounding=ROUND_HALF_UP)
        return round_money(steps * round_to, currency=currency)
    return round_money(amount, currency=currency)


@transaction.atomic
def set_price(
    *,
    price_list: PriceList,
    test=None,
    profile=None,
    price: Decimal | None = None,
    pricing_mode: str = PriceListItem.PricingMode.FIXED,
    profile_discount_percent: Decimal | None = None,
    order_index: int | None = None,
) -> PriceListItem:
    """Crea o actualiza el precio de un examen o de un perfil en la lista."""
    if (test is None) == (profile is None):
        raise ApplicationError("Indique un examen o un perfil, no ambos.")
    if pricing_mode == PriceListItem.PricingMode.FIXED and price is None:
        raise ApplicationError("El precio fijo requiere un monto.")
    if pricing_mode == PriceListItem.PricingMode.SUM_WITH_DISCOUNT:
        if profile is None:
            raise ApplicationError("Sólo un perfil puede calcularse como suma de exámenes.")
        if profile_discount_percent is None or not (0 <= profile_discount_percent <= 100):
            raise ApplicationError("El % de descuento del perfil debe estar entre 0 y 100.")
    if price is not None and price < 0:
        raise ApplicationError("El precio no puede ser negativo.")

    lookup = {"test": test} if test is not None else {"profile": profile}
    defaults = {
        "pricing_mode": pricing_mode,
        "price": _round(price, currency=price_list.currency, round_to=None)
        if price is not None else None,
        "profile_discount_percent": profile_discount_percent,
        "is_active": True,
    }
    if order_index is not None:
        defaults["order_index"] = order_index
    item, created = PriceListItem.objects.update_or_create(
        price_list=price_list, **lookup, defaults=defaults
    )
    if created and order_index is None:
        item.order_index = price_list.items.count()
        item.save(update_fields=["order_index", "updated_at"])
    return item


@transaction.atomic
def adjust_prices(
    *,
    price_list: PriceList,
    percent: Decimal,
    round_to: Decimal | None = None,
    include_profiles: bool = True,
) -> int:
    """Ajuste masivo (+/- %) de los precios fijos de la lista. Los perfiles en modo
    suma-menos-% se ajustan solos al cambiar sus exámenes. Devuelve cuántos cambió."""
    if percent <= -100:
        raise ApplicationError("El ajuste no puede dejar precios en cero o negativos.")
    factor = (HUNDRED + percent) / HUNDRED
    items = price_list.items.filter(
        is_active=True, pricing_mode=PriceListItem.PricingMode.FIXED
    ).select_for_update()
    if not include_profiles:
        items = items.filter(test__isnull=False)
    changed = 0
    for item in items:
        item.price = _round(item.price * factor, currency=price_list.currency,
                            round_to=round_to)
        item.save(update_fields=["price", "updated_at"])
        changed += 1
    return changed


@transaction.atomic
def copy_price_list(
    *,
    source: PriceList,
    code: str,
    name: str,
    currency: Currency | None = None,
    on_date: datetime.date | None = None,
    percent: Decimal = Decimal(0),
    round_to: Decimal | None = None,
) -> PriceList:
    """Copia una lista (precios, modos y orden). Si cambia la moneda, convierte los precios
    fijos con la tasa vigente en `on_date`; `percent` aplica un ajuste adicional."""
    if PriceList.objects.filter(code=code).exists():
        raise ApplicationError(f"Ya existe una lista con el código {code}.")
    currency = currency or source.currency
    rate = Decimal(1)
    if currency.pk != source.currency.pk:
        if on_date is None:
            raise ApplicationError("Para copiar a otra moneda indique la fecha de la tasa.")
        rate = get_exchange_rate(
            from_currency=source.currency, to_currency=currency, on_date=on_date
        )
    factor = rate * (HUNDRED + percent) / HUNDRED
    target = PriceList.objects.create(
        code=code, name=name, currency=currency, notes=f"Copia de {source.code}.",
    )
    PriceListItem.objects.bulk_create([
        PriceListItem(
            price_list=target, test_id=item.test_id, profile_id=item.profile_id,
            pricing_mode=item.pricing_mode, order_index=item.order_index,
            profile_discount_percent=item.profile_discount_percent,
            price=_round(item.price * factor, currency=currency, round_to=round_to)
            if item.price is not None else None,
        )
        for item in source.items.filter(is_active=True)
    ])
    return target


@transaction.atomic
def reorder_items(*, price_list: PriceList, item_ids: Sequence) -> None:
    """Fija el orden de presentación de la lista según `item_ids` (el resto va al final)."""
    items = {item.id: item for item in price_list.items.all()}
    unknown = [i for i in item_ids if i not in items]
    if unknown:
        raise ApplicationError("Hay precios que no pertenecen a esta lista.")
    ordered = [items[i] for i in item_ids] + [
        item for key, item in sorted(items.items(), key=lambda kv: kv[1].order_index)
        if key not in set(item_ids)
    ]
    for index, item in enumerate(ordered, start=1):
        if item.order_index != index:
            item.order_index = index
            item.save(update_fields=["order_index", "updated_at"])


@transaction.atomic
def set_default_price_list(*, price_list: PriceList) -> PriceList:
    PriceList.objects.filter(is_default=True).exclude(pk=price_list.pk).update(
        is_default=False
    )
    price_list.is_default = True
    price_list.save(update_fields=["is_default", "updated_at"])
    return price_list
