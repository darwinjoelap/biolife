"""Tasas de cambio y conversión entre monedas del tenant."""
import datetime
from decimal import ROUND_HALF_UP, Decimal

from apps.billing.models import Currency, ExchangeRate
from apps.core.exceptions import ApplicationError


def get_exchange_rate(
    *, from_currency: Currency, to_currency: Currency, on_date: datetime.date
) -> Decimal:
    """Tasa vigente en `on_date` (la más reciente con fecha <= on_date). Si sólo existe
    la tasa inversa, se usa 1/tasa. Lanza `ApplicationError` si no hay ninguna."""
    if from_currency.pk == to_currency.pk:
        return Decimal(1)
    direct = (
        ExchangeRate.objects.filter(
            from_currency=from_currency, to_currency=to_currency,
            effective_date__lte=on_date, is_active=True,
        )
        .order_by("-effective_date")
        .first()
    )
    inverse = (
        ExchangeRate.objects.filter(
            from_currency=to_currency, to_currency=from_currency,
            effective_date__lte=on_date, is_active=True,
        )
        .order_by("-effective_date")
        .first()
    )
    # Si existen ambas, manda la más reciente.
    if direct and (not inverse or direct.effective_date >= inverse.effective_date):
        return direct.rate
    if inverse:
        return Decimal(1) / inverse.rate
    raise ApplicationError(
        f"No hay tasa de cambio {from_currency.code} → {to_currency.code} vigente al "
        f"{on_date:%d/%m/%Y}."
    )


def convert_amount(
    *, amount: Decimal, from_currency: Currency, to_currency: Currency,
    on_date: datetime.date,
) -> Decimal:
    """Convierte con precisión completa (el redondeo lo decide quien muestra)."""
    rate = get_exchange_rate(
        from_currency=from_currency, to_currency=to_currency, on_date=on_date
    )
    return amount * rate


def round_money(amount: Decimal, *, currency: Currency) -> Decimal:
    return amount.quantize(Decimal(1).scaleb(-currency.decimals), rounding=ROUND_HALF_UP)


def register_exchange_rate(
    *, from_currency: Currency, to_currency: Currency, rate: Decimal,
    effective_date: datetime.date, source: str = ExchangeRate.Source.MANUAL,
    notes: str = "",
) -> ExchangeRate:
    """Registra (o corrige) la tasa de una fecha. Una por par y fecha."""
    if rate <= 0:
        raise ApplicationError("La tasa de cambio debe ser mayor que cero.")
    if from_currency.pk == to_currency.pk:
        raise ApplicationError("La tasa debe ser entre dos monedas distintas.")
    exchange_rate, _ = ExchangeRate.objects.update_or_create(
        from_currency=from_currency, to_currency=to_currency, effective_date=effective_date,
        defaults={"rate": rate, "source": source, "notes": notes, "is_active": True},
    )
    return exchange_rate
