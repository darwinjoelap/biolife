from django_tenants.test.cases import TenantTestCase

from apps.catalog.models import Parameter, Profile, ReferenceRange, Section, Test
from apps.catalog.selectors.catalog_queries import calculation_input_tests, profile_tests
from apps.catalog.services.seeding import seed_uroanalisis
from apps.catalog.services.seeding_base_catalog import TESTS, seed_base_catalog
from apps.catalog.services.seeding_profiles import PROFILE_CODES_HOJAS, seed_profiles


class SeedProfilesTests(TenantTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        seed_uroanalisis()
        seed_profiles()

    def test_estan_los_perfiles_de_las_hojas(self):
        # 13 hojas; el glicémico trae dos variantes en la misma hoja.
        assert len(PROFILE_CODES_HOJAS) == 14
        assert set(PROFILE_CODES_HOJAS) <= set(Profile.objects.values_list("code", flat=True))
        assert Profile.objects.filter(code="PERFIL_PRENATAL").exists()

    def test_ningun_perfil_queda_sin_insumos_para_sus_calculos(self):
        for profile in Profile.objects.all():
            faltan = calculation_input_tests(tests=profile_tests(profile=profile))
            assert not faltan, f"{profile.code}: faltan {[t.code for t in faltan]}"

    def test_perfil_lipidico_agrupa_examenes_individuales(self):
        perfil = Profile.objects.get(code="PERFIL_LIPIDICO")

        assert [t.code for t in profile_tests(profile=perfil)] == [
            "COLESTEROL_TOTAL", "TRIGLICERIDOS", "HDL", "LDL_VLDL", "INDICES_CASTELLI",
        ]

    def test_todos_los_examenes_del_catalogo_tienen_parametros(self):
        for spec in TESTS:
            assert Test.objects.get(code=spec.code).parameters.exists(), spec.code

    def test_cubre_los_6_range_type(self):
        tipos = set(ReferenceRange.objects.values_list("range_type", flat=True))
        assert tipos == {c.value for c in ReferenceRange.RangeType}

    def test_es_idempotente_y_no_pisa_ediciones_del_tenant(self):
        perfil = Profile.objects.get(code="HIV_VDRL")
        perfil.profile_tests.filter(test__code="HIV").delete()
        cantidades = (Test.objects.count(), Parameter.objects.count(),
                      ReferenceRange.objects.count(), Profile.objects.count())

        seed_profiles()

        assert (Test.objects.count(), Parameter.objects.count(),
                ReferenceRange.objects.count(), Profile.objects.count()) == cantidades
        assert [t.code for t in profile_tests(profile=perfil)] == ["VDRL"]


class LegacyAggregateTestsTests(TenantTestCase):
    def test_muda_parametros_del_examen_agregado_y_lo_desactiva(self):
        seccion = Section.objects.create(code="QUIMICA_SANGUINEA", name="QS")
        quim = Test.objects.create(code="QUIM", name="QUÍMICA", section=seccion,
                                   sample_type=Test.SampleType.SUERO)
        Parameter.objects.create(test=quim, code="QUIM_GLICEMIA", name="GLICEMIA",
                                 value_type=Parameter.ValueType.NUMERIC, decimals=0)

        seed_base_catalog()

        quim.refresh_from_db()
        assert Parameter.objects.get(code="QUIM_GLICEMIA").test.code == "GLICEMIA"
        assert quim.is_active is False
