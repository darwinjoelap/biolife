from django.utils import timezone
from django_tenants.test.cases import TenantTestCase

from apps.patients.models import PatientCodeSequence
from apps.patients.services.patient_creation import generate_internal_code
from apps.settings_lab.models import TenantSettings


class CodeSequenceTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        settings_obj = TenantSettings.get_solo()
        settings_obj.lab_initials = "LDU"
        settings_obj.save()

    def test_generate_internal_code_correlativos_consecutivos_mismo_anio(self):
        primero = generate_internal_code()
        segundo = generate_internal_code()

        year_terminal = str(timezone.localdate().year)[-2:]
        assert primero == f"{year_terminal}LDU000001"
        assert segundo == f"{year_terminal}LDU000002"

    def test_generate_internal_code_no_hereda_correlativo_de_otro_anio(self):
        anio_actual = timezone.localdate().year
        PatientCodeSequence.objects.create(year=anio_actual - 1, last_value=41)

        codigo = generate_internal_code()

        year_terminal = str(anio_actual)[-2:]
        assert codigo == f"{year_terminal}LDU000001"
