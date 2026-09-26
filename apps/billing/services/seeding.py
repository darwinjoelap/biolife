"""Valores iniciales de precios por tenant (Fase 08): monedas USD (base) y VES, y una
lista GENERAL vacía en USD. **No se siembran precios**: los del laboratorio de referencia
no se conocen (pregunta abierta en docs/ESTADO.md) y no se inventan."""
from apps.billing.models import Currency, PriceList


def seed_billing_defaults() -> PriceList:
    """Idempotente. Debe correr dentro del `schema_context()` del tenant."""
    usd, _ = Currency.objects.get_or_create(
        code="USD",
        defaults={"name": "Dólar estadounidense", "symbol": "$", "is_base": True,
                  "order_index": 1},
    )
    Currency.objects.get_or_create(
        code="VES", defaults={"name": "Bolívar", "symbol": "Bs.", "order_index": 2}
    )
    price_list, _ = PriceList.objects.get_or_create(
        code="GENERAL",
        defaults={
            "name": "Lista general", "currency": usd,
            "is_default": not PriceList.objects.filter(is_default=True).exists(),
        },
    )
    return price_list
