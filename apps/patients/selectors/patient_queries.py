"""Consultas de la lista y la ficha del paciente (Fase 11e)."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db.models import Count, F, Max, Prefetch, Q, QuerySet

from apps.patients.models import Antecedent, Patient, PatientAntecedent, PatientGuardian


def patient_list(*, query: str = "", limit: int = 60) -> QuerySet[Patient]:
    """Pacientes con su n.º de órdenes y la última visita. Cada palabra buscada debe
    aparecer en el código, documento, nombre, apellido o teléfono."""
    patients = Patient.objects.filter(is_active=True).annotate(
        order_count=Count("orders", distinct=True), last_order=Max("orders__ordered_at"))
    for word in query.split():
        patients = patients.filter(
            Q(internal_code__icontains=word) | Q(document_number__icontains=word)
            | Q(first_name__icontains=word) | Q(last_name__icontains=word)
            | Q(phone__icontains=word))
    return patients.order_by(F("last_order").desc(nulls_last=True), "last_name",
                             "first_name")[:limit]


def patient_detail(*, pk) -> Patient | None:
    try:
        return (
            Patient.objects.filter(pk=pk, is_active=True).select_related("locality")
            .prefetch_related(
                Prefetch("guardians", queryset=PatientGuardian.objects.filter(is_active=True)
                         .select_related("guardian").order_by("-is_primary", "created_at"),
                         to_attr="active_guardians"),
                Prefetch("antecedents", queryset=PatientAntecedent.objects
                         .filter(is_active=True, antecedent__is_active=True)
                         .select_related("antecedent", "created_by"),
                         to_attr="active_antecedents"),
            ).first()
        )
    except (ValueError, ValidationError):
        return None


def active_antecedents(*, patient) -> list[PatientAntecedent]:
    return list(PatientAntecedent.objects.filter(
        patient=patient, is_active=True, antecedent__is_active=True)
        .select_related("antecedent"))


def antecedent_options(*, patient=None) -> QuerySet[Antecedent]:
    """Antecedentes activos que el paciente aún no tiene."""
    options = Antecedent.objects.filter(is_active=True)
    if patient is not None:
        options = options.exclude(patients__patient=patient, patients__is_active=True)
    return options


def suggested_parameters(*, patient) -> list:
    """Parámetros activos que sus antecedentes piden vigilar, sin repetir, en el orden de
    los antecedentes."""
    links = (Antecedent.suggested_parameters.through.objects.filter(
        antecedent__patients__patient=patient, antecedent__patients__is_active=True,
        antecedent__is_active=True, parameter__is_active=True)
        .select_related("parameter", "parameter__test")
        .order_by("antecedent__order_index", "parameter__order_index"))
    return list({str(link.parameter_id): link.parameter for link in links}.values())


def guardian_link(*, patient, pk) -> PatientGuardian | None:
    try:
        return PatientGuardian.objects.select_related("guardian").filter(
            patient=patient, pk=pk).first()
    except (ValueError, ValidationError):
        return None


def antecedent_link(*, patient, pk) -> PatientAntecedent | None:
    try:
        return PatientAntecedent.objects.filter(patient=patient, pk=pk).first()
    except (ValueError, ValidationError):
        return None
