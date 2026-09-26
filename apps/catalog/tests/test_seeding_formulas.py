"""Criterio de salida de la Fase 07: las 16 fórmulas de 04_HALLAZGOS_FORMATOS.md
reproducen los valores.

- DEPURACIÓN: datos **reales** de la hoja `DEPURACIÓN` de Angelus (únicos valores de
  ejemplo que trae el documento de hallazgos).
- Resto: valores de entrada plausibles con el resultado calculado a mano. No hay datos
  reales de ejemplo para ellas en 04_HALLAZGOS_FORMATOS.md.
- INR: ISI = 1,2 es un valor SUPUESTO para la prueba — el real no está confirmado.
"""
from decimal import Decimal

from django_tenants.test.cases import TenantTestCase

from apps.catalog.models import Parameter
from apps.catalog.services.formula_engine import (
    evaluate_calculated_parameters,
    quantize_for_display,
)
from apps.catalog.services.seeding import seed_uroanalisis
from apps.catalog.services.seeding_formulas import FORMULA_CODES_04_HALLAZGOS, seed_formulas
from apps.catalog.services.seeding_reference_ranges import seed_reference_ranges

D = Decimal

VALORES_MEDIDOS = {
    "HEM_HEMOGLOBINA": D("14.0"), "HEM_HEMATOCRITO": D("43"),
    "QUIM_PROTEINAS_TOTALES": D("7.0"), "QUIM_ALBUMINA": D("4.2"),
    "QUIM_BILIRRUBINA_TOTAL": D("0.90"), "QUIM_BILIRRUBINA_DIRECTA": D("0.25"),
    "LIP_COLESTEROL_TOTAL": D("210"), "LIP_HDL": D("45"), "LIP_TRIGLICERIDOS": D("155"),
    "COAG_PT_PACIENTE": D("13.5"), "COAG_PT_CONTROL": D("12.0"),
    "COAG_PTT_PACIENTE": D("35.0"), "COAG_PTT_CONTROL": D("30.0"),
    # Hoja DEPURACIÓN (real)
    "DEP_CREAT_SERICA": D("0.79"), "DEP_CREAT_ORINA": D("14.9"),
}
CONTEXTO_ORDEN = {
    "talla": D("165"), "peso": D("62"), "volumen_orina_24h": D("5030"),
    "isi": D("1.2"),  # SUPUESTO — ISI real no confirmado por Angelus
}
ESPERADOS = {
    "HEM_CHCM": D("32.6"),
    "QUIM_GLOBULINAS": D("2.8"),
    "QUIM_REL_ALB_GLO": D("1.50"),
    "QUIM_BILIRRUBINA_INDIRECTA": D("0.65"),
    "LIP_VLDL": D("31"),
    "LIP_LDL": D("134"),
    "LIP_CASTELLI_I": D("4.67"),
    "LIP_CASTELLI_II": D("2.98"),
    "COAG_PT_RAZON": D("1.13"),
    "COAG_INR": D("1.15"),
    "COAG_PTT_DIFERENCIA": D("5.0"),
    # Reales, hoja DEPURACIÓN
    "DEP_SUPERFICIE_CORPORAL": D("1.6857"),
    "DEP_DEPURACION_SIN_CORR": D("65.88"),
    "DEP_DEPURACION_CORREGIDA": D("67.61"),
    # Derivados de los mismos datos reales (la hoja no los imprime en el doc de hallazgos)
    "DEP_VOLUMEN_MINUTO": D("3.49"),
    "DEP_CREAT_URINARIA_24H": D("0.75"),
}


class SeedFormulasTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        seed_uroanalisis()
        seed_reference_ranges()
        seed_formulas()

    def _calcular(self, valores=VALORES_MEDIDOS, contexto=CONTEXTO_ORDEN):
        calculados = Parameter.objects.filter(
            value_type=Parameter.ValueType.NUMERIC_CALCULATED
        )
        formulas = dict(calculados.values_list("code", "formula"))
        decimales = dict(calculados.values_list("code", "decimals"))
        resultados = evaluate_calculated_parameters(
            formulas=formulas, values=valores, context=contexto
        )
        return resultados, decimales

    def test_existen_las_16_formulas_como_calculados(self):
        codigos = set(
            Parameter.objects.filter(
                code__in=FORMULA_CODES_04_HALLAZGOS,
                value_type=Parameter.ValueType.NUMERIC_CALCULATED,
            ).values_list("code", flat=True)
        )

        assert len(FORMULA_CODES_04_HALLAZGOS) == 16
        assert codigos == set(FORMULA_CODES_04_HALLAZGOS)

    def test_las_16_formulas_reproducen_los_valores(self):
        resultados, decimales = self._calcular()

        obtenidos = {
            code: quantize_for_display(resultados[code].value, decimals=decimales[code])
            for code in FORMULA_CODES_04_HALLAZGOS
        }
        assert obtenidos == ESPERADOS

    def test_depuracion_corregida_usa_superficie_sin_redondear(self):
        resultados, _ = self._calcular()

        # Precisión completa (ADR-017): la SC entra con todos sus decimales.
        superficie = resultados["DEP_SUPERFICIE_CORPORAL"].value
        assert superficie != D("1.6857")
        assert quantize_for_display(superficie, decimals=4) == D("1.6857")

    def test_sin_isi_el_inr_queda_vacio_con_motivo_y_el_resto_se_calcula(self):
        contexto = {k: v for k, v in CONTEXTO_ORDEN.items() if k != "isi"}

        resultados, _ = self._calcular(contexto=contexto)

        assert resultados["COAG_INR"].value is None
        assert resultados["COAG_INR"].missing == ("@isi",)
        assert resultados["COAG_PT_RAZON"].value is not None

    def test_depends_on_poblado_desde_la_formula(self):
        ldl = Parameter.objects.get(code="LIP_LDL")
        indice_orina = Parameter.objects.get(code="URO_INDICE_PROT_CREAT")

        assert set(ldl.depends_on.values_list("code", flat=True)) == {
            "LIP_COLESTEROL_TOTAL", "LIP_HDL", "LIP_VLDL",
        }
        assert set(indice_orina.depends_on.values_list("code", flat=True)) == {
            "URO_PROT_ORINA", "URO_CREAT_ORINA",
        }

    def test_formulas_de_contexto_puro_no_tienen_depends_on(self):
        superficie = Parameter.objects.get(code="DEP_SUPERFICIE_CORPORAL")

        assert superficie.depends_on.count() == 0

    def test_es_idempotente(self):
        cantidad_antes = Parameter.objects.count()

        seed_formulas()

        assert Parameter.objects.count() == cantidad_antes
