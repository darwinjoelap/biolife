from django_tenants.test.cases import TenantTestCase

from apps.catalog.models import ContainerType, SampleRequirement, Test
from apps.catalog.services.seeding import seed_uroanalisis
from apps.catalog.services.seeding_containers import seed_containers
from apps.catalog.services.seeding_reference_ranges import seed_reference_ranges


def _tubos(code):
    return [(r.container_type.code, r.collection_label)
            for r in SampleRequirement.objects.filter(test__code=code)
            .select_related("container_type").order_by("order_index")]


class SeedContainersTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        seed_uroanalisis()
        seed_reference_ranges()

    def test_todo_examen_activo_queda_con_tubo_y_es_idempotente(self):
        seed_containers()
        seed_containers()

        assert ContainerType.objects.count() == 9
        sin_tubo = Test.objects.filter(is_active=True, sample_requirements__isnull=True)
        assert list(sin_tubo.values_list("code", flat=True)) == []
        assert _tubos("HEM_COMP") == [("MORADO_EDTA", "")]
        assert _tubos("COLESTEROL_TOTAL") == [("ROJO_SECO", "")]
        assert _tubos("PT") == [("AZUL_CITRATO", "")]
        assert _tubos("URO") == [("FRASCO_ORINA", "")]
        assert _tubos("DEPURACION") == [("ENVASE_ORINA_24H", ""), ("ROJO_SECO", "")]
        assert _tubos("GLICEMIA_POST_CARGA") == [("ROJO_SECO", "Post-carga 2 h")]

    def test_no_pisa_la_asignacion_del_laboratorio(self):
        seed_containers()
        glicemia = SampleRequirement.objects.get(test__code="GLICEMIA")
        glicemia.container_type = ContainerType.objects.get(code="GRIS_FLUORURO")
        glicemia.save()

        seed_containers()

        assert _tubos("GLICEMIA") == [("GRIS_FLUORURO", "")]
