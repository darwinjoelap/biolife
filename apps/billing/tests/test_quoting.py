import datetime
from decimal import Decimal

from django_tenants.test.cases import TenantTestCase

from apps.billing.models import Discount, PriceListItem
from apps.billing.services.price_lists import set_price
from apps.billing.services.quoting import quote
from apps.billing.tests.factories import HOY, catalogo_y_lista
from apps.core.exceptions import ApplicationError

D = Decimal


class QuoteTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.c = catalogo_y_lista()
        self.t = self.c["tests"]
        self.lista = self.c["lista"]

    def _quote(self, **kw):
        kw.setdefault("on_date", HOY)
        return quote(price_list=self.lista, **kw)

    def _descuento(self, code, kind, value, scope, **kw):
        tests = kw.pop("tests", [])
        profiles = kw.pop("profiles", [])
        d = Discount.objects.create(code=code, name=code, kind=kind, value=D(value),
                                    scope=scope, **kw)
        d.tests.set(tests)
        d.profiles.set(profiles)
        return d

    def test_examenes_sueltos_se_suman(self):
        q = self._quote(tests=[self.t["A"], self.t["C"]])

        assert q.subtotal == D("40.00")
        assert q.total == D("40.00")

    def test_perfil_precio_fijo(self):
        set_price(price_list=self.lista, profile=self.c["p1"], price=D("25"))

        q = self._quote(profiles=[self.c["p1"]])

        assert q.total == D("25.00")
        assert q.lines[0].included_tests == ("A", "B")

    def test_perfil_suma_menos_porcentaje(self):
        set_price(price_list=self.lista, profile=self.c["p1"],
                  pricing_mode=PriceListItem.PricingMode.SUM_WITH_DISCOUNT,
                  profile_discount_percent=D("10"))

        q = self._quote(profiles=[self.c["p1"]])

        assert q.total == D("27.00")  # (10 + 20) - 10 %

    def test_examen_ya_incluido_en_perfil_no_se_cobra_dos_veces(self):
        set_price(price_list=self.lista, profile=self.c["p1"], price=D("25"))

        q = self._quote(profiles=[self.c["p1"]], tests=[self.t["A"], self.t["C"]])

        assert q.total == D("55.00")  # P1 25 + C 30; A no se cobra aparte
        assert any("ya está incluido en P1" in w for w in q.warnings)

    def test_perfiles_que_se_solapan_acreditan_el_examen_comun(self):
        set_price(price_list=self.lista, profile=self.c["p1"], price=D("25"))
        set_price(price_list=self.lista, profile=self.c["p2"], price=D("40"))

        q = self._quote(profiles=[self.c["p1"], self.c["p2"]])

        assert [line.base_amount for line in q.lines] == [D("25.00"), D("20.00")]
        assert q.total == D("45.00")

    def test_falta_precio_lista_lo_que_falta(self):
        with self.assertRaisesMessage(ApplicationError, "no tiene precio para: P2, D"):
            self._quote(tests=[self.t["D"]], profiles=[self.c["p2"]])

    def test_descuento_por_item_solo_a_sus_examenes(self):
        d = self._descuento("C10", "PERCENT", "10", "ITEM", tests=[self.t["C"]])

        q = self._quote(tests=[self.t["A"], self.t["C"]], discounts=[d])

        assert q.discount_total == D("3.00")
        assert q.total == D("37.00")

    def test_no_acumulables_gana_el_mejor_y_acumulables_se_suman(self):
        d5 = self._descuento("P5", "PERCENT", "5", "ORDER")
        d20 = self._descuento("P20", "PERCENT", "20", "ORDER")
        extra = self._descuento("F1", "FIXED_AMOUNT", "1", "ORDER",
                                currency=self.c["usd"], is_stackable=True)

        q = self._quote(tests=[self.t["A"], self.t["B"], self.t["C"]],
                        discounts=[d5, d20, extra])

        assert q.order_discount == D("13.00")  # 20 % de 60 + 1 fijo
        assert {a.code for a in q.applied_discounts} == {"P20", "F1"}
        assert q.total == D("47.00")

    def test_descuento_fijo_en_otra_moneda_se_convierte(self):
        d = self._descuento("BS365", "FIXED_AMOUNT", "365", "ORDER", currency=self.c["ves"])

        q = self._quote(tests=[self.t["C"]], discounts=[d])

        assert q.order_discount == D("10.00")  # 365 Bs / 36,50

    def test_descuento_no_supera_el_monto(self):
        d = self._descuento("F100", "FIXED_AMOUNT", "100", "ORDER", currency=self.c["usd"])

        q = self._quote(tests=[self.t["A"]], discounts=[d])

        assert q.total == D("0.00")

    def test_descuento_vencido_o_sin_autorizacion_se_rechaza(self):
        vencido = self._descuento("V", "PERCENT", "5", "ORDER",
                                  valid_until=HOY - datetime.timedelta(days=1))
        cortesia = self._descuento("CORTESIA", "PERCENT", "100", "ORDER",
                                   requires_authorization=True)

        with self.assertRaisesMessage(ApplicationError, "no está vigente"):
            self._quote(tests=[self.t["A"]], discounts=[vencido])
        with self.assertRaisesMessage(ApplicationError, "requiere autorización"):
            self._quote(tests=[self.t["A"]], discounts=[cortesia])
        assert self._quote(tests=[self.t["A"]], discounts=[cortesia],
                           authorized=True).total == D("0.00")

    def test_total_convertido_a_bolivares(self):
        q = self._quote(tests=[self.t["A"], self.t["B"]], target_currency=self.c["ves"])

        assert q.exchange_rate == D("36.50")
        assert q.converted_total == D("1095.00")

    def test_sin_tasa_para_la_fecha_falla(self):
        with self.assertRaisesMessage(ApplicationError, "No hay tasa de cambio"):
            quote(price_list=self.lista, tests=[self.t["A"]],
                  target_currency=self.c["ves"], on_date=datetime.date(2020, 1, 1))

    def test_lista_fuera_de_vigencia_falla(self):
        self.lista.valid_until = HOY - datetime.timedelta(days=1)
        self.lista.save()

        with self.assertRaisesMessage(ApplicationError, "no está vigente"):
            self._quote(tests=[self.t["A"]])
