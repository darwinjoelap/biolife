from datetime import date

from django_tenants.test.cases import TenantTestCase

from apps.patients.models import Patient, PatientGuardian
from apps.patients.services.guardian_linking import create_guardian, link_guardian
from apps.patients.services.patient_creation import create_patient
from apps.settings_lab.models import TenantSettings


class GuardianLinkingTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        settings_obj = TenantSettings.get_solo()
        settings_obj.lab_initials = "LDU"
        settings_obj.save()

    def test_link_guardian_is_primary_desmarca_anterior(self):
        primero = create_guardian(
            document_type=Patient.DocumentType.V,
            document_number="1000001",
            first_name="Primera",
            last_name="Madre",
        )
        segundo = create_guardian(
            document_type=Patient.DocumentType.V,
            document_number="1000002",
            first_name="Segundo",
            last_name="Padre",
        )

        patient = create_patient(
            first_name="Niño",
            last_name="Ejemplo",
            sex=Patient.Sex.M,
            document_type=Patient.DocumentType.SIN_DOCUMENTO,
            birth_date=date(2018, 1, 1),
            guardian=primero,
            guardian_relationship=PatientGuardian.Relationship.MADRE,
        )

        relacion_previa = patient.guardians.get(guardian=primero)
        assert relacion_previa.is_primary is True

        link_guardian(
            patient=patient,
            guardian=segundo,
            relationship=PatientGuardian.Relationship.PADRE,
            is_primary=True,
        )

        relacion_previa.refresh_from_db()
        relacion_nueva = patient.guardians.get(guardian=segundo)

        assert relacion_previa.is_primary is False
        assert relacion_nueva.is_primary is True
