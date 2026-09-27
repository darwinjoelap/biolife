from datetime import date

from django_tenants.test.cases import TenantTestCase

from apps.patients.models import Patient
from apps.patients.services.patient_age import (
    patient_age_days,
    patient_age_short,
    patient_age_text,
)

HOY = date(2026, 9, 27)


def _p(**kw) -> Patient:
    return Patient(first_name="A", last_name="B", sex="F", document_type="V", **kw)


class PatientAgeTests(TenantTestCase):
    def test_con_fecha_de_nacimiento(self):
        adulto = _p(birth_date=date(1992, 9, 27))
        assert patient_age_short(adulto, as_of=HOY) == "34A"
        assert patient_age_text(adulto, as_of=HOY) == "34 años"
        assert patient_age_short(_p(birth_date=date(2025, 3, 1)), as_of=HOY) == "18M"
        assert patient_age_short(_p(birth_date=date(2026, 9, 10)), as_of=HOY) == "17D"

    def test_edad_declarada_avanza_con_el_tiempo(self):
        bebe = _p(declared_age_value=3, declared_age_unit="MESES",
                  declared_age_at=date(2026, 6, 27))
        assert patient_age_days(bebe, as_of=HOY) == 91 + 92
        assert patient_age_short(bebe, as_of=HOY) == "6M"
        assert patient_age_text(bebe, as_of=HOY) == "3 meses (declarada)"
