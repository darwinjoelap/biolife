import datetime
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django_tenants.test.cases import TenantTestCase

from apps.billing.models import PriceList
from apps.billing.selectors.price_queries import default_price_list, price_list_items
from apps.billing.services.exchange import get_exchange_rate, register_exchange_rate
from apps.billing.services.price_lists import (
    adjust_prices,
    copy_price_list,
    reorder_items,
    set_default_price_list,
    set_price,
)
from apps.billing.services.seeding import seed_billing_defaults
from apps.billing.tests.factories import HOY, catalogo_y_lista
from apps.core.exceptions import ApplicationError

D = Decimal


class PriceListTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.c = catalogo_y_lista()
        self.lista = self.c["lista"]

    def _precios(self, lista):
        return {i.test.code: i.price for i in price_list_items(price_list=lista) if i.test}

    def test_ajuste_masivo_con_redondeo(self):
        cambiados = adjust_prices(price_list=self.lista, percent=D("12.5"), round_to=D("0.5"))

        assert cambiados == 3
        assert self._precios(self.lista) == {"A": D("11.50"), "B": D("22.50"),
                                             "C": D("34.00")}

    def test_ajuste_negativo_total_se_rechaza(self):
        with pytest.raises(ApplicationError):
            adjust_prices(price_list=self.lista, percent=D("-100"))

    def test_copia_a_otra_moneda_con_tasa_del_dia(self):
        copia = copy_price_list(source=self.lista, code="GENERAL_BS", name="General Bs",
                                currency=self.c["ves"], on_date=HOY, round_to=D("5"))

        assert copia.currency.code == "VES"
        assert self._precios(copia) == {"A": D("365.00"), "B": D("730.00"),
                                        "C": D("1095.00")}

    def test_reordenar(self):
        items = list(price_list_items(price_list=self.lista))
        reorder_items(price_list=self.lista, item_ids=[items[2].id])

        assert [i.test.code for i in price_list_items(price_list=self.lista)] == [
            "C", "A", "B",
        ]

    def test_set_price_valida_examen_xor_perfil(self):
        with pytest.raises(ApplicationError):
            set_price(price_list=self.lista, price=D("1"))
        with pytest.raises(ApplicationError):
            set_price(price_list=self.lista, test=self.c["tests"]["D"], price=D("-1"))

    def test_una_sola_lista_predeterminada(self):
        otra = PriceList.objects.create(code="CONVENIO", name="Convenio",
                                        currency=self.c["usd"])
        with pytest.raises(IntegrityError), transaction.atomic():
            PriceList.objects.create(code="X", name="X", currency=self.c["usd"],
                                     is_default=True)

        set_default_price_list(price_list=otra)

        assert default_price_list(on_date=HOY) == otra

    def test_tasa_inversa_y_la_mas_reciente(self):
        usd, ves = self.c["usd"], self.c["ves"]
        register_exchange_rate(from_currency=usd, to_currency=ves, rate=D("40"),
                               effective_date=HOY)

        assert get_exchange_rate(from_currency=usd, to_currency=ves, on_date=HOY) == D("40")
        assert get_exchange_rate(
            from_currency=usd, to_currency=ves, on_date=HOY - datetime.timedelta(days=1)
        ) == D("36.50")
        assert get_exchange_rate(from_currency=ves, to_currency=usd,
                                 on_date=HOY) == D(1) / D(40)


class SeedBillingTests(TenantTestCase):
    def test_monedas_y_lista_general_idempotente_y_sin_precios(self):
        lista = seed_billing_defaults()
        seed_billing_defaults()

        assert lista.currency.code == "USD" and lista.is_default
        assert PriceList.objects.count() == 1
        assert not lista.items.exists()
