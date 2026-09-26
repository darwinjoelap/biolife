import importlib

from django.apps import apps as django_apps
from django_tenants.test.cases import TenantTestCase

from apps.catalog.models import Parameter, Section, Test
from apps.catalog.services.formula_engine import FormulaSyntaxError
from apps.catalog.services.formula_validation import set_parameter_formula, validate_formula

migracion_0004 = importlib.import_module("apps.catalog.migrations.0004_formula_sintaxis_llaves")


class FormulaValidationTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        section = Section.objects.create(code="S", name="S")
        self.test_obj = Test.objects.create(
            code="T", name="T", section=section, sample_type=Test.SampleType.SUERO,
        )
        self.a = self._param("A", Parameter.ValueType.NUMERIC)
        self.b = self._param("B", Parameter.ValueType.NUMERIC)
        self.c = self._param("C", Parameter.ValueType.NUMERIC_CALCULATED, "{A} + {B}")
        self.d = self._param("D", Parameter.ValueType.NUMERIC_CALCULATED, "{C} * 2")

    def _param(self, code, value_type, formula=""):
        return Parameter.objects.create(
            test=self.test_obj, code=code, name=code, value_type=value_type, formula=formula,
        )

    def test_set_formula_sincroniza_depends_on(self):
        set_parameter_formula(parameter=self.c, formula="{A} * {B} / {@peso}")

        assert set(self.c.depends_on.values_list("code", flat=True)) == {"A", "B"}

    def test_cambiar_formula_reemplaza_depends_on(self):
        set_parameter_formula(parameter=self.c, formula="{A} + {B}")
        set_parameter_formula(parameter=self.c, formula="{A} * 3")

        assert list(self.c.depends_on.values_list("code", flat=True)) == ["A"]

    def test_codigo_inexistente_falla(self):
        with self.assertRaisesMessage(FormulaSyntaxError, "no existen: NOEXISTE"):
            validate_formula(code="C", formula="{A} + {NOEXISTE}")

    def test_autorreferencia_falla(self):
        with self.assertRaisesMessage(FormulaSyntaxError, "a sí misma"):
            validate_formula(code="C", formula="{C} + 1")

    def test_ciclo_se_detecta_al_guardar(self):
        # D depende de C; poner C en función de D cierra el ciclo C → D → C.
        with self.assertRaisesMessage(FormulaSyntaxError, "circular"):
            set_parameter_formula(parameter=self.c, formula="{D} + 1")

        self.c.refresh_from_db()
        assert self.c.formula == "{A} + {B}"

    def test_parametro_no_numerico_no_se_puede_usar(self):
        from apps.catalog.models import CodedOptionSet

        opciones = CodedOptionSet.objects.create(code="NEG_POS_X", name="x")
        Parameter.objects.create(
            test=self.test_obj, code="Q", name="Q",
            value_type=Parameter.ValueType.QUALITATIVE, option_set=opciones,
        )

        with self.assertRaisesMessage(FormulaSyntaxError, "numéricos"):
            validate_formula(code="C", formula="{Q} + 1")

    def test_parametro_no_calculado_no_admite_formula(self):
        with self.assertRaises(FormulaSyntaxError):
            set_parameter_formula(parameter=self.a, formula="{B} + 1")

    def test_migracion_0004_convierte_codigos_sueltos_a_llaves(self):
        Parameter.objects.filter(code="C").update(formula="A + B")
        Parameter.objects.filter(code="D").update(formula="C * 2")

        migracion_0004.a_llaves(django_apps, None)

        self.c.refresh_from_db()
        self.d.refresh_from_db()
        assert self.c.formula == "{A} + {B}"
        assert self.d.formula == "{C} * 2"
        assert set(self.c.depends_on.values_list("code", flat=True)) == {"A", "B"}

    def test_migracion_0004_es_idempotente_sobre_formulas_con_llaves(self):
        migracion_0004.a_llaves(django_apps, None)

        self.c.refresh_from_db()
        assert self.c.formula == "{A} + {B}"
