"""Edad del paciente en días a una fecha (etiquetas de la Fase 09, rangos de la Fase 10).

Con fecha de nacimiento es exacta. Con edad declarada se suma el tiempo transcurrido desde
que se declaró (365,25 días por año, ADR-020)."""
from datetime import date

from django.utils import timezone

from apps.core.utils.dates import (
    age_in_days,
    age_parts_to_days,
    days_to_age_parts,
    format_age_days,
)
from apps.patients.models import Patient


def patient_age_days(patient: Patient, *, as_of: date | None = None) -> int:
    as_of = as_of or timezone.localdate()
    if patient.birth_date is not None:
        return age_in_days(patient.birth_date, as_of)
    value = patient.declared_age_value or 0
    declared = {
        Patient.AgeUnit.ANOS: {"years": value},
        Patient.AgeUnit.MESES: {"months": value},
    }.get(patient.declared_age_unit, {"days": value})
    elapsed = (as_of - (patient.declared_age_at or as_of)).days
    return age_parts_to_days(**declared) + max(elapsed, 0)


def patient_age_text(patient: Patient, *, as_of: date | None = None) -> str:
    """'34 años', '1 año 6 meses'… con '(declarada)' si no hay fecha de nacimiento."""
    if patient.birth_date is None:
        return (f"{patient.declared_age_value} "
                f"{patient.get_declared_age_unit_display().lower()} (declarada)")
    return format_age_days(patient_age_days(patient, as_of=as_of))


def patient_age_short(patient: Patient, *, as_of: date | None = None) -> str:
    """Forma corta para etiquetas: '34A', '18M', '12D'."""
    days = patient_age_days(patient, as_of=as_of)
    years, months, _ = days_to_age_parts(days)
    if years >= 2:
        return f"{years}A"
    if years or months:
        return f"{years * 12 + months}M"
    return f"{days}D"
