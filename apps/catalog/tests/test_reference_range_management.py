from decimal import Decimal

from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient

from apps.accounts.models import User
from apps.catalog.admin_forms import ReferenceRangeForm
from apps.catalog.models import Parameter, ReferenceRange, Section, Test
from apps.catalog.services.reference_range_management import (
    AVISO,
    ERROR,
    RangeSpec,
    explain_resolution,
    find_range_issues,
    parameter_range_issues,
)
from apps.catalog.services.seeding import seed_uroanalisis
from apps.catalog.services.seeding_reference_ranges import seed_reference_ranges

MAX = 54750


def spec(sex="ANY", lo=0, hi=MAX, cond="NINGUNA", prio=0, label="r"):
    return RangeSpec(sex=sex, age_min_days=lo, age_max_days=hi, condition=cond,
                     priority=prio, label=label)


def levels(issues):
    return sorted(i.level for i in issues)


class FindRangeIssuesTests(TenantTestCase):
    def test_tramos_contiguos_no_dan_avisos(self):
        assert find_range_issues([spec(lo=0, hi=364), spec(lo=365, hi=6573),
                                  spec(lo=6574)]) == []

    def test_hombre_y_mujer_completos_no_dan_avisos(self):
        assert find_range_issues([spec("M"), spec("F")]) == []

    def test_mismo_tramo_misma_prioridad_es_error(self):
        assert levels(find_range_issues([spec("M"), spec("ANY")])) == [ERROR]

    def test_solape_con_ancho_distinto_es_aviso_y_gana_el_estrecho(self):
        issues = find_range_issues([spec(lo=0, hi=MAX, label="adulto"),
                                    spec(lo=0, hi=28, label="neonato")])
        assert levels(issues) == [AVISO]
        assert "neonato" in issues[0].message.split("se usa el más estrecho")[1]

    def test_prioridad_distinta_no_es_problema(self):
        assert find_range_issues([spec(prio=0), spec(lo=0, hi=28, prio=1)]) == []

    def test_huecos_por_edad_y_por_sexo(self):
        issues = find_range_issues([spec("M", lo=29), spec("F")])
        assert levels(issues) == [AVISO]
        assert "Masculino entre 0 días y 28 días" in issues[0].message

    def test_huecos_se_revisan_por_condicion_y_solo_sexos_cubiertos(self):
        # Un rango sólo para embarazadas no exige rango masculino en EMBARAZO.
        assert find_range_issues([spec(), spec("F", cond="EMBARAZO")]) == []

    def test_catalogo_sembrado_no_tiene_errores(self):
        seed_uroanalisis()
        seed_reference_ranges()
        for parameter in Parameter.objects.filter(reference_ranges__isnull=False).distinct():
            errores = [i for i in parameter_range_issues(parameter=parameter)
                       if i.level == ERROR]
            assert not errores, (parameter.code, errores)


class ExplainResolutionTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        section = Section.objects.create(code="S", name="S")
        test = Test.objects.create(code="T", name="T", section=section,
                                   sample_type=Test.SampleType.SUERO)
        self.p = Parameter.objects.create(test=test, code="HB", name="HB",
                                          value_type=Parameter.ValueType.NUMERIC)

        def rr(text, **kw):
            return ReferenceRange.objects.create(
                parameter=self.p, range_type="CLOSED", display_text=text,
                low=Decimal(1), high=Decimal(2), **kw)
        self.m = rr("M", sex="M")
        self.f = rr("F", sex="F")
        self.rn = rr("RN", age_min_days=0, age_max_days=28, priority=1)
        self.inactivo = rr("VIEJO", sex="F", priority=5, is_active=False)

    def test_elige_lo_mismo_que_el_resolver_y_explica_descartes(self):
        e = explain_resolution(parameter=self.p, sex="F", age_days=10000)

        assert e.chosen == self.f
        motivos = {c.reference_range.display_text: c.reason for c in e.candidates}
        assert motivos["F"] == "Aplica."
        assert "es para Masculino" in motivos["M"]
        assert "cubre 0 días a 28 días" in motivos["RN"]
        assert "desactivado" in motivos["VIEJO"]

    def test_recien_nacido_gana_por_prioridad(self):
        e = explain_resolution(parameter=self.p, sex="M", age_days=5)

        assert e.chosen == self.rn
        motivos = {c.reference_range.display_text: c.reason for c in e.candidates}
        assert "pierde el desempate" in motivos["M"]

    def test_sin_rango_para_la_condicion(self):
        e = explain_resolution(parameter=self.p, sex="M", age_days=10000, condition="AYUNO")

        assert e.chosen is None
        assert "referencia vacía" in e.summary


class ReferenceRangeFormTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        section = Section.objects.create(code="S", name="S")
        test = Test.objects.create(code="T", name="T", section=section,
                                   sample_type=Test.SampleType.SUERO)
        self.p = Parameter.objects.create(test=test, code="X", name="X",
                                          value_type=Parameter.ValueType.NUMERIC)

    def _form(self, **data):
        base = {"sex": "ANY", "condition": "NINGUNA", "priority": 0, "range_type": "CLOSED",
                "low": "1", "high": "2", "display_text": "1 - 2", "is_active": True}
        base.update(data)
        return ReferenceRangeForm(data=base, instance=ReferenceRange(parameter=self.p))

    def test_hasta_es_exclusivo_y_vacio_es_sin_limite(self):
        f = self._form(desde_anos=1, hasta_anos=18)
        assert f.is_valid(), f.errors
        assert (f.instance.age_min_days, f.instance.age_max_days) == (365, 6573)

        f = self._form(desde_dias=29)
        assert f.is_valid(), f.errors
        assert (f.instance.age_min_days, f.instance.age_max_days) == (29, MAX)

    def test_valores_segun_tipo_de_rango(self):
        f = self._form(low="", range_type="CLOSED")
        assert not f.is_valid() and "low" in f.errors
        f = self._form(low="5", high="2")
        assert not f.is_valid() and "high" in f.errors

    def test_hasta_menor_que_desde_falla(self):
        assert not self._form(desde_anos=5, hasta_anos=1).is_valid()

    def test_edad_inicial_se_muestra_en_anos_meses_dias(self):
        rr = ReferenceRange.objects.create(
            parameter=self.p, range_type="CLOSED", display_text="x", low=1, high=2,
            age_min_days=183, age_max_days=6573)
        f = ReferenceRangeForm(instance=rr)
        assert (f.initial["desde_meses"], f.initial["hasta_anos"]) == (6, 18)


class ParameterAdminTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        seed_uroanalisis()
        seed_reference_ranges()
        user = User.objects.create_superuser(username="admin", email="a@a.com", password="x")
        self.client = TenantClient(self.tenant)
        self.client.force_login(user)
        self.hb = Parameter.objects.get(code="HEM_HEMOGLOBINA")

    def test_ficha_del_examen_y_del_parametro_cargan(self):
        test_url = f"/admin/catalog/test/{self.hb.test_id}/change/"
        param_url = f"/admin/catalog/parameter/{self.hb.pk}/change/"

        assert "Editar rangos" in self.client.get(test_url).content.decode()
        body = self.client.get(param_url).content.decode()
        assert "Cobertura de rangos" in body and "desde_anos" in body

    def test_probador(self):
        url = f"/admin/catalog/parameter/{self.hb.pk}/probar-rangos/"
        body = self.client.get(url, {"sexo": "F", "anos": 30, "condicion": "NINGUNA"})

        assert "12,0 - 16,0 g/dL" in body.content.decode()
