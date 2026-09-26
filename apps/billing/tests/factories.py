"""Catálogo mínimo para probar precios sin sembrar el catálogo completo."""
import datetime
from decimal import Decimal

from apps.billing.models import Currency, PriceList
from apps.billing.services.exchange import register_exchange_rate
from apps.billing.services.price_lists import set_price
from apps.catalog.models import Section, Test
from apps.catalog.services.profiles import create_profile

HOY = datetime.date(2026, 9, 26)


def catalogo_y_lista():
    usd = Currency.objects.create(code="USD", name="Dólar", symbol="$", is_base=True)
    ves = Currency.objects.create(code="VES", name="Bolívar", symbol="Bs.")
    register_exchange_rate(from_currency=usd, to_currency=ves, rate=Decimal("36.50"),
                           effective_date=HOY - datetime.timedelta(days=1))
    seccion = Section.objects.create(code="S", name="S")
    tests = {
        code: Test.objects.create(code=code, name=code, section=seccion,
                                  sample_type=Test.SampleType.SUERO)
        for code in ("A", "B", "C", "D")
    }
    p1 = create_profile(code="P1", name="P1", tests=[tests["A"], tests["B"]])
    p2 = create_profile(code="P2", name="P2", tests=[tests["B"], tests["C"]])
    lista = PriceList.objects.create(code="GENERAL", name="General", currency=usd,
                                     is_default=True)
    for code, price in (("A", "10"), ("B", "20"), ("C", "30")):
        set_price(price_list=lista, test=tests[code], price=Decimal(price))
    return {"usd": usd, "ves": ves, "tests": tests, "p1": p1, "p2": p2, "lista": lista}
