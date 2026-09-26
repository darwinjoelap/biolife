from django_tenants.test.cases import TenantTestCase

from apps.catalog.models import Parameter, Section, Test
from apps.catalog.selectors.catalog_queries import calculation_input_tests, profile_tests
from apps.catalog.services.formula_validation import set_parameter_formula
from apps.catalog.services.profiles import create_profile, set_profile_tests
from apps.core.exceptions import ApplicationError


class ProfileServiceTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.section = Section.objects.create(code="QS", name="QS")
        self.col = self._test("COL", [("COL_V", Parameter.ValueType.NUMERIC, "")])
        self.hdl = self._test("HDL_T", [("HDL_V", Parameter.ValueType.NUMERIC, "")])
        self.tg = self._test("TG", [("TG_V", Parameter.ValueType.NUMERIC, "")])
        self.vldl = self._test("VLDL_T", [("VLDL_V", Parameter.ValueType.NUMERIC_CALCULATED,
                                           "{TG_V} / 5")])
        self.ldl = self._test("LDL_T", [("LDL_V", Parameter.ValueType.NUMERIC_CALCULATED,
                                         "{COL_V} - {HDL_V} - {VLDL_V}")])

    def _test(self, code, params):
        test = Test.objects.create(code=code, name=code, section=self.section,
                                   sample_type=Test.SampleType.SUERO)
        for p_code, vt, formula in params:
            parameter = Parameter.objects.create(test=test, code=p_code, name=p_code,
                                                 value_type=vt, formula=formula or "")
            if formula:
                set_parameter_formula(parameter=parameter, formula=formula)
        return test

    def test_crea_perfil_respetando_el_orden(self):
        perfil = create_profile(code="LIP", name="LIPÍDICO",
                                tests=[self.tg, self.col, self.hdl])

        assert [t.code for t in profile_tests(profile=perfil)] == ["TG", "COL", "HDL_T"]

    def test_insumos_de_calculo_transitivos(self):
        # LDL necesita COL, HDL y VLDL; VLDL a su vez necesita TG.
        faltan = calculation_input_tests(tests=[self.ldl])

        assert {t.code for t in faltan} == {"COL", "HDL_T", "VLDL_T", "TG"}
        assert {t.code for t in calculation_input_tests(tests=[self.ldl, self.vldl])} == {
            "COL", "HDL_T", "TG",
        }

    def test_perfil_incompleto_se_rechaza_salvo_que_se_permita(self):
        with self.assertRaisesMessage(ApplicationError, "le faltan exámenes"):
            create_profile(code="X", name="X", tests=[self.ldl])

        perfil = create_profile(code="X", name="X", tests=[self.ldl], allow_incomplete=True)
        assert perfil.profile_tests.count() == 1

    def test_repetidos_vacio_e_inactivos_se_rechazan(self):
        perfil = create_profile(code="P", name="P", tests=[self.col])
        self.hdl.is_active = False
        self.hdl.save()

        with self.assertRaisesMessage(ApplicationError, "repetidos"):
            set_profile_tests(profile=perfil, tests=[self.col, self.col])
        with self.assertRaisesMessage(ApplicationError, "al menos un examen"):
            set_profile_tests(profile=perfil, tests=[])
        with self.assertRaisesMessage(ApplicationError, "inactivos"):
            set_profile_tests(profile=perfil, tests=[self.hdl])

    def test_codigo_duplicado_se_rechaza(self):
        create_profile(code="P", name="P", tests=[self.col])

        with self.assertRaisesMessage(ApplicationError, "Ya existe"):
            create_profile(code="P", name="P2", tests=[self.tg])
