"""Las fórmulas sembradas reproducen los valores **reales** de las hojas de Excel del
laboratorio de referencia (celdas leídas en la Fase 08). Cada caso cita la hoja."""
from decimal import Decimal

from django_tenants.test.cases import TenantTestCase

from apps.catalog.models import Parameter
from apps.catalog.services.formula_engine import (
    evaluate_calculated_parameters,
    quantize_for_display,
)
from apps.catalog.services.seeding import seed_uroanalisis
from apps.catalog.services.seeding_formulas import (
    FORMULA_CODES_04_HALLAZGOS,
    FORMULA_CODES_ADICIONALES,
)
from apps.catalog.services.seeding_reference_ranges import seed_reference_ranges

D = Decimal


class FormulasContraHojasTests(TenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        seed_uroanalisis()
        seed_reference_ranges()

    def _calc(self, values, context=None):
        formulas = dict(
            Parameter.objects.filter(value_type=Parameter.ValueType.NUMERIC_CALCULATED)
            .values_list("code", "formula")
        )
        results = evaluate_calculated_parameters(
            formulas=formulas, values=values, context=context or {}
        )
        return {code: r.value for code, r in results.items()}

    def test_estan_las_17_formulas(self):
        codigos = set(FORMULA_CODES_04_HALLAZGOS + FORMULA_CODES_ADICIONALES)
        assert Parameter.objects.filter(
            code__in=codigos, value_type=Parameter.ValueType.NUMERIC_CALCULATED
        ).count() == 17

    def test_hoja_hc_chcm(self):
        r = self._calc({"HEM_HEMOGLOBINA": D("12.6"), "HEM_HEMATOCRITO": D("40")})
        assert r["HEM_CHCM"] == D("31.5")

    def test_hoja_quim_lipidos_proteinas_y_bilirrubinas(self):
        r = self._calc({
            "LIP_COLESTEROL_TOTAL": D("212"), "LIP_TRIGLICERIDOS": D("158"),
            "LIP_HDL": D("50.5"), "QUIM_PROTEINAS_TOTALES": D("6.9"),
            "QUIM_ALBUMINA": D("4.6"), "QUIM_BILIRRUBINA_TOTAL": D("0.5"),
            "QUIM_BILIRRUBINA_DIRECTA": D("0.21"),
        })
        assert r["LIP_VLDL"] == D("31.6")
        assert r["LIP_LDL"] == D("129.9")
        assert r["QUIM_GLOBULINAS"] == D("2.3")  # Excel: 2.3000000000000007 (float)
        assert r["QUIM_REL_ALB_GLO"] == D("2")  # Excel: 1.9999999999999993
        assert r["QUIM_BILIRRUBINA_INDIRECTA"] == D("0.29")

    def test_hoja_perfil_20_indices_de_castelli(self):
        r = self._calc({"LIP_COLESTEROL_TOTAL": D("155"), "LIP_TRIGLICERIDOS": D("85"),
                        "LIP_HDL": D("66")})
        assert r["LIP_LDL"] == D("72")
        assert r["LIP_VLDL"] == D("17")
        assert quantize_for_display(r["LIP_CASTELLI_I"], decimals=10) == D("2.3484848485")
        assert quantize_for_display(r["LIP_CASTELLI_II"], decimals=10) == D("1.0909090909")

    def test_hoja_coagul_pt_y_ptt(self):
        r = self._calc(
            {"COAG_PT_PACIENTE": D("13.2"), "COAG_PT_CONTROL": D("13.3"),
             "COAG_PTT_PACIENTE": D("25.5"), "COAG_PTT_CONTROL": D("31.6")},
            {"isi": D("1.0")},  # ISI supuesto: en la hoja la celda está vacía
        )
        assert quantize_for_display(r["COAG_PT_RAZON"], decimals=10) == D("0.9924812030")
        assert r["COAG_INR"] == r["COAG_PT_RAZON"]
        assert r["COAG_PTT_DIFERENCIA"] == D("-6.1")  # Excel: -6.100000000000001

    def test_inr_sin_isi_queda_vacio_no_en_1_como_la_hoja(self):
        # En la hoja, ISI vacío hace RAZÓN^0 = 1: el INR impreso es siempre 1.
        r = self._calc({"COAG_PT_PACIENTE": D("15.3"), "COAG_PT_CONTROL": D("12.8")})
        assert r["COAG_INR"] is None

    def test_hoja_p_glicemico_homa_ir(self):
        r = self._calc({"QUIM_GLICEMIA": D("72"), "HOR_INSULINA_BASAL": D("8")})
        assert quantize_for_display(r["HOR_HOMA_IR"], decimals=10) == D("1.4222222222")

    def test_hoja_depuracion_valores_reales(self):
        r = self._calc(
            {"DEP_CREAT_SERICA": D("0.79"), "DEP_CREAT_ORINA": D("14.9")},
            {"talla": D("165"), "peso": D("62"), "volumen_orina_24h": D("5030")},
        )
        # Valores de las celdas de la hoja DEPURACIÓN (Excel, 15-16 cifras).
        esperados = {
            "DEP_SUPERFICIE_CORPORAL": "1.6857243744653712",
            "DEP_DEPURACION_SIN_CORR": "65.88168073136427",
            "DEP_DEPURACION_CORREGIDA": "67.61206600065182",
            "DEP_VOLUMEN_MINUTO": "3.4930555555555554",
            "DEP_CREAT_URINARIA_24H": "0.74947",
        }
        for code, excel in esperados.items():
            assert quantize_for_display(r[code], decimals=12) == quantize_for_display(
                D(excel), decimals=12
            ), code
