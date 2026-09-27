import datetime
from decimal import Decimal

import pytest
from django_tenants.test.cases import TenantTestCase

from apps.core.exceptions import ApplicationError
from apps.orders.models import LabelPrint, Order, OrderItem, Sample
from apps.orders.services.labels import print_labels
from apps.orders.services.numbering import next_order_number, sample_identifiers
from apps.orders.services.order_creation import build_draft, create_order
from apps.orders.services.order_management import add_to_order, cancel_order, mark_paid
from apps.orders.services.sample_collection import collect_all, collect_sample, reject_sample
from apps.orders.tests.factories import catalogo, paciente

D = Decimal


def _tubes(order):
    return [
        (s.container_type.short_name, s.collection_label,
         sorted(i.test.code for i in s.order_items.all()))
        for s in order.samples.exclude(status=Sample.Status.RECHAZADA).order_by("sequence")
    ]


class NumberingTests(TenantTestCase):
    def test_correlativo_diario_que_reinicia(self):
        day = datetime.date(2026, 9, 27)
        assert next_order_number(on_date=day) == "260927-0001"
        assert next_order_number(on_date=day) == "260927-0002"
        assert next_order_number(on_date=day + datetime.timedelta(days=1)) == "260928-0001"

    def test_numero_y_barras_de_muestra(self):
        assert sample_identifiers(order_number="260927-0012", sequence=3) == (
            "260927-0012-03", "260927001203")
        with pytest.raises(ApplicationError):
            sample_identifiers(order_number="260927-0012", sequence=100)


class OrderCreationTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.c = catalogo()
        self.t = self.c["tests"]
        self.patient = paciente()

    def _order(self, tests=(), profiles=(), **kw):
        kw.setdefault("price_list", self.c["lista"])
        return create_order(patient=self.patient, tests=[self.t[c] for c in tests],
                            profiles=profiles, **kw)

    def test_ejemplo_hematologia_lipidos_y_coagulacion_da_tres_tubos(self):
        order, _ = self._order(tests=["HEM", "PT"], profiles=[self.c["lip"]])

        # Orden de extracción: azul, rojo, morado; cada tubo con su número.
        assert _tubes(order) == [("AZUL", "", ["PT"]), ("ROJO", "", ["COL", "TRI"]),
                                 ("MORADO", "", ["HEM"])]
        numbers = list(order.samples.values_list("number", "barcode"))
        assert numbers[0] == (f"{order.number}-01", order.barcode + "01")
        assert all(len(barcode) == 12 and barcode.isdigit() for _, barcode in numbers)
        # El perfil se expande y queda registrado de dónde vino cada examen.
        items = {i.test.code: i.profile for i in order.items.all()}
        assert items["COL"] == self.c["lip"] and items["HEM"] is None

    def test_congela_la_cotizacion_y_convierte_a_moneda_de_referencia(self):
        order, _ = self._order(tests=["HEM", "COL"], profiles=[self.c["lip"]],
                               reference_currency=self.c["ves"])

        # COL ya viene en el perfil: se cobra una vez (15 + 10).
        assert (order.total, order.currency_code) == (D("25.00"), "USD")
        assert (order.converted_total, order.converted_currency_code) == (D("2500.00"), "VES")
        assert [line["code"] for line in order.quote_snapshot["lines"]] == ["LIP", "HEM"]
        assert not order.pricing_pending

    def test_sin_precio_se_registra_con_monto_pendiente(self):
        order, warnings = self._order(tests=["HEM", "SIN"])

        assert order.pricing_pending and order.total is None
        assert any("Sin precio" in w for w in warnings)
        assert any("no tiene tubo asignado" in w for w in warnings)
        with pytest.raises(ApplicationError, match="precios pendientes"):
            mark_paid(order=order)

    def test_depuracion_pide_dos_tubos_y_avisa_datos_antropometricos(self):
        order, warnings = self._order(tests=["DEP", "COL"])

        assert _tubes(order) == [("ROJO", "", ["COL", "DEP"]), ("ORINA 24H", "", ["DEP"])]
        assert any("peso, talla" in w for w in warnings)

    def test_tomas_por_tiempo_y_tubo_propio_van_aparte(self):
        order, _ = self._order(tests=["COL", "GPC", "EXT"])

        assert _tubes(order) == [("ROJO", "", ["COL"]), ("ROJO", "", ["EXT"]),
                                 ("ROJO", "Post-carga 2 h", ["GPC"])]

    def test_maximo_de_examenes_por_tubo(self):
        rojo = self.c["tubos"]["ROJO_SECO"]
        rojo.max_tests = 1
        rojo.save()

        order, _ = self._order(tests=["COL", "TRI"])

        assert _tubes(order) == [("ROJO", "", ["COL"]), ("ROJO", "", ["TRI"])]

    def test_vista_previa_coincide_con_lo_que_se_guarda(self):
        draft = build_draft(tests=[self.t["HEM"], self.t["PT"]], profiles=[self.c["lip"]],
                            price_list=self.c["lista"])

        assert [(t.container_type.short_name, sorted(t.item_keys)) for t in draft.tubes] == [
            ("AZUL", ["PT"]), ("ROJO", ["COL", "TRI"]), ("MORADO", ["HEM"])]
        assert draft.quote.total == D("35.00")  # perfil 15 + HEM 10 + PT 10
        assert Order.objects.count() == 0

    def test_orden_vacia_falla(self):
        with pytest.raises(ApplicationError, match="al menos un examen"):
            self._order()


class OrderLifecycleTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.c = catalogo()
        self.t = self.c["tests"]
        self.order, _ = create_order(patient=paciente(), tests=[self.t["HEM"], self.t["COL"]],
                                     price_list=self.c["lista"])

    def test_toma_de_muestras_cambia_el_estado_de_la_orden(self):
        rojo, morado = self.order.samples.order_by("sequence")
        collect_sample(sample=rojo)
        self.order.refresh_from_db()
        assert self.order.status == Order.Status.REGISTRADA

        collect_sample(sample=morado)
        self.order.refresh_from_db()
        assert self.order.status == Order.Status.MUESTRA_TOMADA

    def test_rechazo_crea_reemplazo_con_numero_nuevo(self):
        collect_all(order=self.order)
        rojo = self.order.samples.get(sequence=1)

        nueva = reject_sample(sample=rojo, reason="Hemólisis")

        assert nueva.sequence == 3 and nueva.replaces == rojo
        assert nueva.number.endswith("-03") and nueva.status == Sample.Status.PENDIENTE
        assert list(nueva.order_items.values_list("test__code", flat=True)) == ["COL"]
        self.order.refresh_from_db()
        assert self.order.status == Order.Status.REGISTRADA  # falta tomar el reemplazo
        with pytest.raises(ApplicationError, match="motivo"):
            reject_sample(sample=nueva, reason=" ")

    def test_agregar_examen_reutiliza_tubo_por_tomar_o_crea_uno_nuevo(self):
        add_to_order(order=self.order, tests=[self.t["TRI"]])
        assert _tubes(self.order) == [("ROJO", "", ["COL", "TRI"]), ("MORADO", "", ["HEM"])]
        self.order.refresh_from_db()
        assert self.order.total == D("30.00")

        collect_all(order=self.order)
        add_to_order(order=self.order, tests=[self.t["PT"]])

        assert _tubes(self.order)[-1] == ("AZUL", "", ["PT"])  # numerado al final
        self.order.refresh_from_db()
        assert self.order.status == Order.Status.REGISTRADA
        with pytest.raises(ApplicationError, match="ya están"):
            add_to_order(order=self.order, tests=[self.t["PT"]])

    def test_agregar_a_orden_pagada_deja_saldo(self):
        mark_paid(order=self.order)
        warnings = add_to_order(order=self.order, tests=[self.t["TRI"]])

        self.order.refresh_from_db()
        assert not self.order.is_paid
        assert any("saldo" in w for w in warnings)

    def test_anular_no_borra_y_bloquea_cambios(self):
        cancel_order(order=self.order, reason="Paciente no asistió")

        self.order.refresh_from_db()
        assert self.order.status == Order.Status.ANULADA
        assert set(self.order.items.values_list("status", flat=True)) == {
            OrderItem.Status.ANULADO}
        assert not self.order.samples.filter(status=Sample.Status.PENDIENTE).exists()
        with pytest.raises(ApplicationError, match="anulada"):
            add_to_order(order=self.order, tests=[self.t["TRI"]])

    def test_etiquetas_pdf_y_registro_de_reimpresion(self):
        samples = list(self.order.samples.order_by("sequence"))

        pdf = print_labels(order=self.order, samples=samples, user=None, width_mm=50,
                           height_mm=25, include_order_label=True)
        print_labels(order=self.order, samples=samples[:1], user=None, width_mm=50,
                     height_mm=25)

        assert pdf.startswith(b"%PDF")
        assert pdf.count(b"/Type /Page") - pdf.count(b"/Type /Pages") == 3
        assert LabelPrint.objects.count() == 3
        assert LabelPrint.objects.filter(is_reprint=True).count() == 1
