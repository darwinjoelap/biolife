import datetime
from decimal import Decimal

import pytest
from django_tenants.test.cases import TenantTestCase

from apps.accounts.models import User
from apps.catalog.models import CodedOption, Parameter, ReagentLot, Test
from apps.catalog.services.reagent_lots import set_current_lot
from apps.catalog.services.seeding import seed_uroanalisis
from apps.catalog.services.seeding_containers import seed_containers
from apps.catalog.services.seeding_critical_values import seed_critical_values
from apps.catalog.services.seeding_reference_ranges import seed_reference_ranges
from apps.core.exceptions import ApplicationError
from apps.orders.models import Order, OrderItem
from apps.orders.services.order_creation import create_order
from apps.orders.services.sample_collection import collect_all
from apps.orders.tests.factories import paciente
from apps.results.models import Result, ResultValue
from apps.results.services.result_capture import build_sheet, save_sheet
from apps.results.services.validation import notify_critical, validate_results
from apps.settings_lab.models import TenantSettings

D = Decimal


class ResultsTestBase(TenantTestCase):
    def setUp(self):
        super().setUp()
        seed_uroanalisis()
        seed_reference_ranges()
        seed_containers()
        seed_critical_values()
        self.patient = paciente(sex="F", birth_date=datetime.date(1990, 5, 4))
        self.tech = User.objects.create_user(username="tec", email="t@lab.test", password="x")
        self.bio = User.objects.create_user(username="bio", email="b@lab.test", password="x")

    def order(self, *codes) -> Order:
        tests = list(Test.objects.filter(code__in=codes))
        order, _ = create_order(patient=self.patient, tests=tests)
        collect_all(order=order)
        return order

    @staticmethod
    def entries(**values) -> dict:
        params = {p.code: p for p in Parameter.objects.filter(code__in=values)}
        return {str(params[code].pk): raw for code, raw in values.items()}

    @staticmethod
    def rows(sheet) -> dict:
        return {row.parameter.code: row for block in sheet.blocks for row in block.rows}


class CaptureTests(ResultsTestBase):
    def test_marca_normal_bajo_y_critico_por_sexo(self):
        order = self.order("HEM_COMP")
        for raw, flag in (("13,4", "NORMAL"), ("11", "BAJO"), ("6,5", "CRITICO_BAJO")):
            row = self.rows(build_sheet(order, entries=self.entries(HEM_HEMOGLOBINA=raw)))[
                "HEM_HEMOGLOBINA"]
            assert row.assessment.flag == flag
            assert row.reference_text == "12,0 - 16,0 g/dL"  # rango femenino

    def test_calculo_en_vivo_de_lipidos_sin_guardar(self):
        order = self.order("COLESTEROL_TOTAL", "TRIGLICERIDOS", "HDL", "LDL_VLDL")
        sheet = build_sheet(order, entries=self.entries(
            LIP_COLESTEROL_TOTAL="210", LIP_TRIGLICERIDOS="155", LIP_HDL="45"))
        rows = self.rows(sheet)
        assert rows["LIP_VLDL"].display == "31,0"
        assert rows["LIP_LDL"].display == "134,0"
        assert rows["LIP_COLESTEROL_TOTAL"].assessment.flag == "ALTO"
        assert not ResultValue.objects.exists()

    def test_inr_usa_el_isi_del_lote_vigente(self):
        order = self.order("PT")
        entries = self.entries(COAG_PT_PACIENTE="13,5", COAG_PT_CONTROL="12,0")
        assert "isi" in self.rows(build_sheet(order, entries=entries))["COAG_INR"].calc_note

        set_current_lot(lot=ReagentLot.objects.create(
            reagent="TROMBOPLASTINA", lot_number="L-77", isi=D("1.2")))
        sheet = save_sheet(order, entries=entries, user=self.tech)

        assert self.rows(sheet)["COAG_INR"].display == "1,15"
        result = Result.objects.get(order_item__test__code="PT")
        assert result.calculation_context["isi"] == "1.200"
        assert result.calculation_context["lote_tromboplastina"] == "L-77"

    def test_banda_interpretativa_homa(self):
        order = self.order("GLICEMIA", "INSULINA_BASAL", "HOMA_IR")
        row = self.rows(build_sheet(order, entries=self.entries(
            QUIM_GLICEMIA="100", HOR_INSULINA_BASAL="12")))["HOR_HOMA_IR"]
        assert row.display == "2,96"
        assert (row.assessment.flag, row.assessment.interpretation) == (
            "ANORMAL", "RESISTENCIA A LA INSULINA")

    def test_cualitativo_distinto_al_esperado_es_anormal(self):
        order = self.order("HIV")
        hiv = Parameter.objects.get(code="SERO_HIV")
        positivo = CodedOption.objects.get(option_set=hiv.option_set, value="REACTIVO")
        row = self.rows(build_sheet(order, entries={str(hiv.pk): str(positivo.pk)}))[
            "SERO_HIV"]
        assert row.assessment.flag == "ANORMAL"

    def test_conteo_por_campo_y_valor_invalido(self):
        order = self.order("URO")
        row = self.rows(build_sheet(order, entries=self.entries(URO_HEMATIES="0 - 2")))[
            "URO_HEMATIES"]
        assert row.display == "0 - 2"
        with pytest.raises(ApplicationError, match="no es un número"):
            save_sheet(order, entries=self.entries(URO_PROT_ORINA="abc"))

    def test_estados_de_examen_y_orden(self):
        order = self.order("COLESTEROL_TOTAL", "HDL")
        save_sheet(order, entries=self.entries(LIP_COLESTEROL_TOTAL="180"), user=self.tech)
        order.refresh_from_db()
        assert order.status == Order.Status.EN_PROCESO
        item = OrderItem.objects.get(order=order, test__code="COLESTEROL_TOTAL")
        assert item.status == "CARGADO" and item.result.entered_by == self.tech

        save_sheet(order, entries=self.entries(LIP_HDL="50"), user=self.tech)
        order.refresh_from_db()
        assert order.status == Order.Status.RESULTADOS_CARGADOS

        validate_results(order=order, user=self.bio)
        order.refresh_from_db()
        assert order.status == Order.Status.VALIDADA
        value = ResultValue.objects.get(parameter__code="LIP_HDL")
        assert value.reference_text and value.reference_range is not None

    def test_carga_sin_tubo_tomado_avisa(self):
        test = Test.objects.get(code="HDL")
        order, _ = create_order(patient=self.patient, tests=[test])
        sheet = save_sheet(order, entries=self.entries(LIP_HDL="50"))
        assert any("sin tubo" in w for w in sheet.warnings)


class ValidationTests(ResultsTestBase):
    def test_critico_exige_aviso_confirmado_del_mismo_valor(self):
        order = self.order("ELECTROLITOS")
        save_sheet(order, entries=self.entries(
            QUIM_SODIO="140", QUIM_POTASIO="6,8", QUIM_CLORO="100"), user=self.tech)
        with pytest.raises(ApplicationError, match="valor crítico"):
            validate_results(order=order, user=self.bio)

        potasio = ResultValue.objects.get(parameter__code="QUIM_POTASIO")
        assert potasio.flag == "CRITICO_ALTO"
        with pytest.raises(ApplicationError, match="Confirme"):
            notify_critical(value=potasio, value_confirmed=False, notified_to="Dr. X",
                            method="LLAMADA")
        notify_critical(value=potasio, value_confirmed=True, notified_to="Dr. Pérez",
                        method="LLAMADA", user=self.bio)

        # Si el valor cambia, el aviso anterior no sirve.
        save_sheet(order, entries=self.entries(QUIM_POTASIO="7,1"), user=self.tech)
        with pytest.raises(ApplicationError, match="valor crítico"):
            validate_results(order=order, user=self.bio)
        notify_critical(value=ResultValue.objects.get(parameter__code="QUIM_POTASIO"),
                        value_confirmed=True, notified_to="Dr. Pérez", method="LLAMADA")
        validate_results(order=order, user=self.bio)
        assert Result.objects.get().status == Result.Status.VALIDADO

    def test_doble_validacion_exige_otra_persona(self):
        settings_obj = TenantSettings.get_solo()
        settings_obj.require_second_validation = True
        settings_obj.save()
        order = self.order("HDL")
        save_sheet(order, entries=self.entries(LIP_HDL="50"), user=self.tech)

        with pytest.raises(ApplicationError, match="doble validación"):
            validate_results(order=order, user=self.tech)
        validate_results(order=order, user=self.bio)

    def test_validado_es_inmutable_incluso_sus_insumos(self):
        order = self.order("COLESTEROL_TOTAL", "TRIGLICERIDOS", "HDL", "LDL_VLDL")
        save_sheet(order, entries=self.entries(
            LIP_COLESTEROL_TOTAL="210", LIP_TRIGLICERIDOS="155", LIP_HDL="45"), user=self.tech)
        ldl_result = Result.objects.get(order_item__test__code="LDL_VLDL")
        validate_results(order=order, result_ids=[ldl_result.pk], user=self.bio)

        with pytest.raises(ApplicationError, match="ya está validado"):
            save_sheet(order, entries=self.entries(LIP_TRIGLICERIDOS="300"))
        assert ResultValue.objects.get(parameter__code="LIP_LDL").value_numeric == 134

    def test_faltan_valores_no_valida(self):
        order = self.order("ELECTROLITOS")
        save_sheet(order, entries=self.entries(QUIM_SODIO="140"), user=self.tech)
        result = Result.objects.get()
        with pytest.raises(ApplicationError, match="faltan"):
            validate_results(order=order, result_ids=[result.pk], user=self.bio)

    def test_valor_anterior_del_paciente(self):
        first = self.order("HDL")
        save_sheet(first, entries=self.entries(LIP_HDL="38"), user=self.tech)
        validate_results(order=first, user=self.bio)

        second = self.order("HDL")
        row = self.rows(build_sheet(second))["LIP_HDL"]
        assert row.previous["text"] == "38,0"
