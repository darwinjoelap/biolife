"""Etiquetas de pacientes (Fase 11e)."""
from django import template

from apps.patients.services.patient_age import patient_age_short

register = template.Library()


@register.filter
def short_age(patient) -> str:
    """'34A', '18M', '12D' (años, meses o días), para listas."""
    return patient_age_short(patient)
