from datetime import date

import pytest
from django_tenants.test.cases import TenantTestCase

from apps.core.exceptions import ApplicationError
from apps.patients.models import Patient, PatientGuardian
from apps.patients.services.guardian_linking import create_guardian
from apps.patients.services.patient_creation import create_patient
from apps.settings_lab.models import TenantSettings


class PatientCreationTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        settings_obj = TenantSettings.get_solo()
        settings_obj.lab_initials = "LDU"
        settings_obj.save()

    def test_create_patient_adulto_con_documento_no_requiere_representante(self):
        patient = create_patient(
            first_name="Ana",
            last_name="Pérez",
            sex=Patient.Sex.F,
            document_type=Patient.DocumentType.V,
            document_number="12345678",
            birth_date=date(1990, 1, 1),
        )

        assert patient.pk is not None
        assert patient.internal_code
        assert not patient.guardians.exists()

    def test_create_patient_menor_sin_documento_sin_representante_falla(self):
        with pytest.raises(ApplicationError):
            create_patient(
                first_name="Juan",
                last_name="Gómez",
                sex=Patient.Sex.M,
                document_type=Patient.DocumentType.SIN_DOCUMENTO,
                birth_date=date(2015, 1, 1),
            )

    def test_create_patient_menor_sin_documento_con_representante_crea_relacion(self):
        guardian = create_guardian(
            document_type=Patient.DocumentType.V,
            document_number="5000000",
            first_name="María",
            last_name="Gómez",
        )

        patient = create_patient(
            first_name="Juan",
            last_name="Gómez",
            sex=Patient.Sex.M,
            document_type=Patient.DocumentType.SIN_DOCUMENTO,
            birth_date=date(2015, 1, 1),
            guardian=guardian,
            guardian_relationship=PatientGuardian.Relationship.MADRE,
        )

        assert patient.guardians.count() == 1
        relation = patient.guardians.get()
        assert relation.guardian_id == guardian.id
        assert relation.is_primary is True

    def test_create_patient_menor_con_documento_propio_no_requiere_representante(self):
        patient = create_patient(
            first_name="Luis",
            last_name="Rojas",
            sex=Patient.Sex.M,
            document_type=Patient.DocumentType.V,
            document_number="30111222",
            birth_date=date(2010, 1, 1),
        )

        assert patient.pk is not None
        assert not patient.guardians.exists()

    def test_create_patient_sin_documento_con_document_number_falla(self):
        with pytest.raises(ApplicationError):
            create_patient(
                first_name="X",
                last_name="Y",
                sex=Patient.Sex.M,
                document_type=Patient.DocumentType.SIN_DOCUMENTO,
                document_number="1",
                birth_date=date(1990, 1, 1),
            )

    def test_create_patient_documento_duplicado_falla(self):
        create_patient(
            first_name="Primero",
            last_name="Apellido",
            sex=Patient.Sex.M,
            document_type=Patient.DocumentType.V,
            document_number="99999999",
            birth_date=date(1990, 1, 1),
        )

        with pytest.raises(ApplicationError):
            create_patient(
                first_name="Segundo",
                last_name="Apellido",
                sex=Patient.Sex.M,
                document_type=Patient.DocumentType.V,
                document_number="99999999",
                birth_date=date(1991, 1, 1),
            )
