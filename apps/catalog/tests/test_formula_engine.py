"""Motor de fórmulas puro: no necesita base de datos."""
from decimal import Decimal

import pytest

from apps.catalog.services.formula_engine import (
    FormulaEvaluationError,
    FormulaSyntaxError,
    MissingInputError,
    calculation_order,
    evaluate_calculated_parameters,
    evaluate_formula,
    parse_formula,
    quantize_for_display,
)

D = Decimal


class TestParseFormula:
    def test_extrae_codigos_y_variables_de_contexto(self):
        parsed = parse_formula("({A_1} * {@volumen_orina_24h}) / ({B} * 1440)")

        assert parsed.parameter_codes == {"A_1", "B"}
        assert parsed.context_variables == {"volumen_orina_24h"}

    @pytest.mark.parametrize(
        "formula",
        [
            "__import__('os').system('dir')",
            "{A}.real",
            "{A}[0]",
            "{A} if {B} else 1",
            "{A} > {B}",
            "lambda: 1",
            "{A} % 2",
            "{A} // 2",
            "open('x')",
            "HEM_HEMOGLOBINA / 2",  # código suelto, sin llaves
            "'texto'",
            "True + 1",
            "{A} + sqrt",
            "round({A}, n=2)",
            "{a_minuscula}",
            "{A",
            "",
            "   ",
        ],
    )
    def test_rechaza_formulas_invalidas_o_peligrosas(self, formula):
        with pytest.raises(FormulaSyntaxError):
            parse_formula(formula)

    def test_rechaza_variable_de_contexto_desconocida(self):
        with pytest.raises(FormulaSyntaxError, match="desconocida"):
            parse_formula("{A} * {@edad}")

    def test_rechaza_formula_demasiado_larga(self):
        with pytest.raises(FormulaSyntaxError):
            parse_formula(" + ".join(["{A}"] * 200))


class TestEvaluateFormula:
    def test_usa_decimal_sin_error_de_float(self):
        resultado = evaluate_formula(formula="{A} + {B}", values={"A": D("0.1"), "B": D("0.2")})

        assert resultado == D("0.3")

    def test_funciones_permitidas(self):
        valores = {"A": D("-2.345"), "B": D("9")}

        assert evaluate_formula(formula="abs({A})", values=valores) == D("2.345")
        assert evaluate_formula(formula="sqrt({B})", values=valores) == D("3")
        assert evaluate_formula(formula="min({A}, {B}, 0)", values=valores) == D("-2.345")
        assert evaluate_formula(formula="max({A}, {B})", values=valores) == D("9")
        assert evaluate_formula(formula="round({A}, 2)", values=valores) == D("-2.35")
        assert evaluate_formula(formula="-{A}", values=valores) == D("2.345")

    def test_potencia_con_exponente_decimal(self):
        resultado = evaluate_formula(
            formula="{R} ** {@isi}", values={"R": D("1.5")}, context={"isi": D("1.0")}
        )

        assert resultado == D("1.5")

    def test_falta_insumo_lanza_missing_input_con_la_lista(self):
        with pytest.raises(MissingInputError) as info:
            evaluate_formula(formula="{A} * {@peso}", values={"A": None}, context={})

        assert info.value.missing == ("A", "@peso")

    def test_division_por_cero(self):
        with pytest.raises(FormulaEvaluationError, match="cero"):
            evaluate_formula(formula="{A} / {B}", values={"A": D("1"), "B": D("0")})

    def test_raiz_de_negativo(self):
        with pytest.raises(FormulaEvaluationError):
            evaluate_formula(formula="sqrt({A})", values={"A": D("-4")})

    def test_exponente_fuera_de_rango(self):
        with pytest.raises(FormulaEvaluationError, match="Exponente"):
            evaluate_formula(formula="{A} ** 1000", values={"A": D("9")})

    def test_acepta_float_en_valores_sin_arrastrar_error_binario(self):
        assert evaluate_formula(formula="{A} * 3", values={"A": 0.1}) == D("0.3")


class TestQuantize:
    def test_redondeo_mitad_hacia_arriba(self):
        assert quantize_for_display(D("2.345"), decimals=2) == D("2.35")
        assert quantize_for_display(D("2.5"), decimals=0) == D("3")
        assert quantize_for_display(D("1.68572437"), decimals=4) == D("1.6857")


class TestCalculationOrder:
    def test_orden_topologico(self):
        orden = calculation_order({"C": "{B} + 1", "B": "{A} * 2", "D": "{X} / 5"})

        assert orden.index("B") < orden.index("C")
        assert set(orden) == {"B", "C", "D"}

    def test_detecta_ciclo(self):
        with pytest.raises(FormulaSyntaxError, match="circular"):
            calculation_order({"A": "{B} + 1", "B": "{C} + 1", "C": "{A} + 1"})


class TestEvaluateCalculatedParameters:
    def test_encadena_con_precision_completa(self):
        # VLDL = 155/5 = 31 ; LDL = 210 - 45 - 31 = 134 ; CASTELLI_II = 134/45
        resultados = evaluate_calculated_parameters(
            formulas={
                "LDL": "{COL} - {HDL} - {VLDL}",
                "VLDL": "{TG} / 5",
                "C2": "{LDL} / {HDL}",
            },
            values={"COL": D("210"), "HDL": D("45"), "TG": D("155")},
        )

        assert resultados["VLDL"].value == D("31")
        assert resultados["LDL"].value == D("134")
        assert quantize_for_display(resultados["C2"].value, decimals=2) == D("2.98")

    def test_insumo_faltante_propaga_vacio_sin_bloquear_el_resto(self):
        resultados = evaluate_calculated_parameters(
            formulas={"X": "{A} * 2", "Y": "{X} + 1", "Z": "{B} + 1"},
            values={"A": None, "B": D("1")},
        )

        assert resultados["X"].value is None
        assert resultados["X"].missing == ("A",)
        assert resultados["Y"].value is None
        assert resultados["Y"].missing == ("X",)
        assert resultados["Z"].value == D("2")

    def test_error_de_evaluacion_queda_registrado(self):
        resultados = evaluate_calculated_parameters(
            formulas={"R": "{A} / {B}"}, values={"A": D("1"), "B": D("0")}
        )

        assert resultados["R"].value is None
        assert "cero" in resultados["R"].reason
