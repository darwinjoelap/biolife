"""Cotización: cuánto cuesta un conjunto de exámenes y perfiles con una lista de precios,
descuentos y (opcionalmente) su equivalente en otra moneda. La orden (Fase 09) llama a
`quote()` y congela el resultado; aquí no se guarda nada.

Reglas (ADR-019):
1. **Perfiles.** `FIXED` → `price`. `SUM_WITH_DISCOUNT` → suma de los precios
   individuales de sus exámenes en la misma lista, menos `profile_discount_percent`.
2. **Un examen se cobra una vez.** Si un examen pedido suelto ya viene en un perfil pedido,
   no se cobra aparte (queda como aviso). Si dos perfiles comparten exámenes, el segundo
   recibe un crédito por el precio individual de los compartidos (sin quedar negativo).
3. **Descuentos por ítem** (`scope=ITEM`): aplican a las líneas de sus exámenes/perfiles
   (o a todas si no tienen ninguno asignado). Por línea: el mejor no acumulable + todos los
   acumulables, con tope en el monto de la línea.
4. **Descuentos de orden** (`scope=ORDER`): mismo criterio sobre el subtotal que queda
   después de los descuentos por ítem.
5. Montos fijos en otra moneda se convierten con la tasa del día. Todo se calcula con
   precisión completa y se redondea a los decimales de la moneda por línea.
"""
from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

from django.utils import timezone

from apps.billing.models import Currency, Discount, PriceList, PriceListItem
from apps.billing.services.exchange import convert_amount, get_exchange_rate, round_money
from apps.catalog.selectors.catalog_queries import profile_tests
from apps.core.exceptions import ApplicationError

if TYPE_CHECKING:  # sólo para anotaciones: billing no importa modelos de catálogo
    from apps.catalog.models import Profile, Test

ZERO = Decimal(0)
HUNDRED = Decimal(100)


@dataclass
class QuoteLine:
    kind: str  # "PROFILE" | "TEST"
    code: str
    name: str
    base_amount: Decimal
    discount_amount: Decimal = ZERO
    included_tests: tuple[str, ...] = ()
    notes: list[str] = field(default_factory=list)

    @property
    def amount(self) -> Decimal:
        return self.base_amount - self.discount_amount


@dataclass
class AppliedDiscount:
    code: str
    name: str
    scope: str
    amount: Decimal
    line_code: str = ""


@dataclass
class Quote:
    price_list_code: str
    currency: Currency
    on_date: datetime.date
    lines: list[QuoteLine]
    applied_discounts: list[AppliedDiscount]
    order_discount: Decimal
    warnings: list[str]
    converted_currency: Currency | None = None
    exchange_rate: Decimal | None = None

    @property
    def subtotal(self) -> Decimal:
        return sum((line.base_amount for line in self.lines), ZERO)

    @property
    def discount_total(self) -> Decimal:
        return sum((line.discount_amount for line in self.lines), ZERO) + self.order_discount

    @property
    def total(self) -> Decimal:
        return self.subtotal - self.discount_total

    @property
    def converted_total(self) -> Decimal | None:
        if self.converted_currency is None or self.exchange_rate is None:
            return None
        return round_money(self.total * self.exchange_rate, currency=self.converted_currency)


def quote(
    *,
    price_list: PriceList,
    tests: Sequence[Test] = (),
    profiles: Sequence[Profile] = (),
    discounts: Sequence[Discount] = (),
    on_date: datetime.date | None = None,
    target_currency: Currency | None = None,
    authorized: bool = False,
) -> Quote:
    """Cotiza. Lanza `ApplicationError` si falta un precio, la lista no está vigente o un
    descuento no aplica (vencido, requiere autorización, moneda sin tasa)."""
    on_date = on_date or timezone.localdate()
    _check_price_list(price_list, on_date)
    currency = price_list.currency
    items = list(price_list.items.filter(is_active=True))
    test_items = {i.test_id: i for i in items if i.test_id}
    profile_items = {i.profile_id: i for i in items if i.profile_id}

    lines: list[QuoteLine] = []
    warnings: list[str] = []
    missing: list[str] = []
    covered: dict = {}  # test_id -> código del perfil que lo cubre

    for profile in _unique(profiles):
        line = _profile_line(
            profile=profile, item=profile_items.get(profile.id), test_items=test_items,
            covered=covered, currency=currency, missing=missing, warnings=warnings,
        )
        if line:
            lines.append(line)

    for test in _unique(tests):
        if test.id in covered:
            warnings.append(
                f"{test.name} ya está incluido en {covered[test.id]}: no se cobra aparte."
            )
            continue
        item = test_items.get(test.id)
        if item is None or item.price is None:
            missing.append(test.code)
            continue
        covered[test.id] = test.code
        lines.append(QuoteLine(kind="TEST", code=test.code, name=test.name,
                               base_amount=round_money(item.price, currency=currency),
                               included_tests=(test.code,)))

    if missing:
        raise ApplicationError(
            f"La lista {price_list.code} no tiene precio para: " + ", ".join(missing),
            extra={"missing": missing},
        )

    applied = _apply_item_discounts(
        lines=lines, discounts=discounts, currency=currency, on_date=on_date,
        authorized=authorized,
    )
    order_discount, order_applied = _apply_order_discounts(
        lines=lines, discounts=discounts, currency=currency, on_date=on_date,
        authorized=authorized,
    )

    result = Quote(
        price_list_code=price_list.code, currency=currency, on_date=on_date, lines=lines,
        applied_discounts=applied + order_applied, order_discount=order_discount,
        warnings=warnings,
    )
    if target_currency is not None and target_currency.pk != currency.pk:
        result.converted_currency = target_currency
        result.exchange_rate = get_exchange_rate(
            from_currency=currency, to_currency=target_currency, on_date=on_date
        )
    return result


# --------------------------------------------------------------------------- ayudantes
def _unique(objects):
    seen, result = set(), []
    for obj in objects:
        if obj.id not in seen:
            seen.add(obj.id)
            result.append(obj)
    return result


def _check_price_list(price_list: PriceList, on_date: datetime.date) -> None:
    if not price_list.is_active:
        raise ApplicationError(f"La lista de precios {price_list.code} está inactiva.")
    if (price_list.valid_from and on_date < price_list.valid_from) or (
        price_list.valid_until and on_date > price_list.valid_until
    ):
        raise ApplicationError(
            f"La lista de precios {price_list.code} no está vigente al {on_date:%d/%m/%Y}."
        )


def _profile_line(
    *, profile, item: PriceListItem | None, test_items, covered, currency, missing, warnings
) -> QuoteLine | None:
    tests = profile_tests(profile=profile)
    if item is None:
        missing.append(profile.code)
        return None

    if item.pricing_mode == PriceListItem.PricingMode.FIXED:
        base = item.price
    else:
        without_price = [
            t.code for t in tests
            if test_items.get(t.id) is None or test_items[t.id].price is None
        ]
        if without_price:
            missing.extend(f"{c} (para calcular {profile.code})" for c in without_price)
            return None
        total = sum((test_items[t.id].price for t in tests), ZERO)
        base = total * (HUNDRED - item.profile_discount_percent) / HUNDRED

    line = QuoteLine(kind="PROFILE", code=profile.code, name=profile.name,
                     base_amount=ZERO, included_tests=tuple(t.code for t in tests))

    # Exámenes que ya cubre un perfil anterior: crédito por su precio individual.
    credit = ZERO
    for test in tests:
        if test.id not in covered:
            covered[test.id] = profile.code
            continue
        individual = test_items.get(test.id)
        if individual is None or individual.price is None:
            warnings.append(
                f"{test.name} se repite en {covered[test.id]} y {profile.code}, pero no "
                "tiene precio individual para descontarlo."
            )
            continue
        credit += individual.price
        line.notes.append(f"{test.name} ya incluido en {covered[test.id]}")
    line.base_amount = round_money(max(base - credit, ZERO), currency=currency)
    return line


def _discount_amount_in(
    *, discount: Discount, base: Decimal, currency: Currency, on_date: datetime.date
) -> Decimal:
    if discount.kind == Discount.Kind.PERCENT:
        return base * discount.value / HUNDRED
    return convert_amount(
        amount=discount.value, from_currency=discount.currency, to_currency=currency,
        on_date=on_date,
    )


def _check_discount(discount: Discount, *, on_date, authorized: bool) -> None:
    if not discount.is_active:
        raise ApplicationError(f"El descuento {discount.code} está inactivo.")
    if (discount.valid_from and on_date < discount.valid_from) or (
        discount.valid_until and on_date > discount.valid_until
    ):
        raise ApplicationError(
            f"El descuento {discount.code} no está vigente al {on_date:%d/%m/%Y}."
        )
    if discount.requires_authorization and not authorized:
        raise ApplicationError(f"El descuento {discount.code} requiere autorización.")


def _combine(candidates: list[tuple[Discount, Decimal]], cap: Decimal):
    """Mejor no acumulable + todos los acumulables, con tope `cap`."""
    stackable = [(d, a) for d, a in candidates if d.is_stackable]
    exclusive = [(d, a) for d, a in candidates if not d.is_stackable]
    chosen = stackable + ([max(exclusive, key=lambda da: da[1])] if exclusive else [])
    result, remaining = [], cap
    for discount, amount in sorted(chosen, key=lambda da: da[0].order_index):
        amount = min(amount, remaining)
        if amount > 0:
            result.append((discount, amount))
            remaining -= amount
    return result


def _apply_item_discounts(*, lines, discounts, currency, on_date, authorized):
    applied: list[AppliedDiscount] = []
    item_discounts = [d for d in discounts if d.scope == Discount.Scope.ITEM]
    for discount in item_discounts:
        _check_discount(discount, on_date=on_date, authorized=authorized)
    targets = {
        d.id: (
            set(d.tests.values_list("code", flat=True)),
            set(d.profiles.values_list("code", flat=True)),
        )
        for d in item_discounts
    }
    for line in lines:
        candidates = []
        for discount in item_discounts:
            test_codes, profile_codes = targets[discount.id]
            applies = (not test_codes and not profile_codes) or (
                line.code in (profile_codes if line.kind == "PROFILE" else test_codes)
            )
            if applies:
                candidates.append((discount, _discount_amount_in(
                    discount=discount, base=line.base_amount, currency=currency,
                    on_date=on_date,
                )))
        for discount, amount in _combine(candidates, line.base_amount):
            amount = round_money(amount, currency=currency)
            line.discount_amount += amount
            applied.append(AppliedDiscount(discount.code, discount.name, discount.scope,
                                           amount, line.code))
    return applied


def _apply_order_discounts(*, lines, discounts, currency, on_date, authorized):
    order_discounts = [d for d in discounts if d.scope == Discount.Scope.ORDER]
    for discount in order_discounts:
        _check_discount(discount, on_date=on_date, authorized=authorized)
    base = sum((line.amount for line in lines), ZERO)
    candidates = [
        (d, _discount_amount_in(discount=d, base=base, currency=currency, on_date=on_date))
        for d in order_discounts
    ]
    applied, total = [], ZERO
    for discount, amount in _combine(candidates, base):
        amount = round_money(amount, currency=currency)
        total += amount
        applied.append(AppliedDiscount(discount.code, discount.name, discount.scope, amount))
    return total, applied
