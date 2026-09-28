"""Edición del paciente desde su ficha (Fase 11e, ADR-032).

- Nada se borra: un representante o un antecedente que ya no aplica se **desactiva**.
- Un menor sin documento propio debe conservar al menos un representante activo.
- Toda edición queda en la bitácora (`AuditLog`).
"""
from __future__ import annotations

from django.db import IntegrityError, transaction

from apps.accounts.services.audit import log_action
from apps.core.exceptions import ApplicationError
from apps.patients.models import Guardian, Patient, PatientAntecedent, PatientGuardian
from apps.patients.services.guardian_linking import create_guardian

EDITABLE = ("document_type", "document_number", "first_name", "last_name", "sex",
            "birth_date", "declared_age_value", "declared_age_unit", "declared_age_at",
            "phone", "email", "locality", "address")


def _log(action: str, patient: Patient, by, changes: dict | None = None) -> None:
    log_action(action=action, user=by, model_name="patients.Patient",
               object_id=str(patient.pk), changes=changes)


def _needs_guardian(patient: Patient) -> bool:
    return patient.is_minor and not patient.document_number


def _active_guardians(patient: Patient):
    return PatientGuardian.objects.filter(patient=patient, is_active=True)


@transaction.atomic
def update_patient(*, patient: Patient, data: dict, by=None) -> Patient:
    """Datos del paciente (formulario ya validado). El código interno no cambia."""
    changes = {}
    for name in EDITABLE:
        if name not in data:
            continue
        old, new = getattr(patient, name), data[name]
        if old != new:
            changes[name] = [str(old or ""), str(new or "")]
            setattr(patient, name, new)
    if patient.document_type == Patient.DocumentType.SIN_DOCUMENTO:
        patient.document_number = None
    elif not patient.document_number:
        raise ApplicationError("Indique el número de documento o elija «Sin documento».")
    if _needs_guardian(patient) and not _active_guardians(patient).exists():
        raise ApplicationError("Es menor de edad sin documento propio: agregue primero un "
                               "representante.")
    try:
        with transaction.atomic():
            patient.save()
    except IntegrityError as exc:
        raise ApplicationError("Ya existe otro paciente con ese documento.") from exc
    if changes:
        _log("PACIENTE_MODIFICADO", patient, by, changes)
    return patient


@transaction.atomic
def add_guardian(*, patient: Patient, data: dict, by=None) -> PatientGuardian:
    """Agrega (o reactiva) un representante. Si ya existe alguien con ese documento se
    reutiliza; si es el único activo, queda como principal."""
    guardian = Guardian.objects.filter(document_type=data["document_type"],
                                       document_number=data["document_number"]).first()
    if guardian is None:
        guardian = create_guardian(
            document_type=data["document_type"], document_number=data["document_number"],
            first_name=data["first_name"], last_name=data["last_name"],
            phone=data.get("phone", ""))
    primary = data.get("is_primary") or not _active_guardians(patient).exists()
    if primary:
        _active_guardians(patient).update(is_primary=False)
    link, _ = PatientGuardian.objects.update_or_create(
        patient=patient, guardian=guardian,
        defaults={"relationship": data["relationship"],
                  "relationship_detail": data.get("relationship_detail", ""),
                  "is_primary": primary, "is_active": True})
    _log("REPRESENTANTE_AGREGADO", patient, by,
         {"representante": str(guardian), "documento": guardian.document_number})
    return link


@transaction.atomic
def deactivate_guardian(*, link: PatientGuardian, by=None) -> PatientGuardian:
    patient = link.patient
    others = _active_guardians(patient).exclude(pk=link.pk)
    if _needs_guardian(patient) and not others.exists():
        raise ApplicationError("Es menor de edad sin documento propio: debe conservar al "
                               "menos un representante.")
    link.is_active = False
    was_primary, link.is_primary = link.is_primary, False
    link.save(update_fields=["is_active", "is_primary", "updated_at"])
    if was_primary and (first := others.order_by("created_at").first()):
        first.is_primary = True
        first.save(update_fields=["is_primary", "updated_at"])
    _log("REPRESENTANTE_RETIRADO", patient, by, {"representante": str(link.guardian)})
    return link


@transaction.atomic
def make_primary(*, link: PatientGuardian, by=None) -> PatientGuardian:
    _active_guardians(link.patient).update(is_primary=False)
    link.is_primary = True
    link.save(update_fields=["is_primary", "updated_at"])
    return link


@transaction.atomic
def add_antecedent(*, patient: Patient, antecedent, notes: str = "",
                   by=None) -> PatientAntecedent:
    """Registra (o reactiva) un antecedente; queda quién y cuándo."""
    link = PatientAntecedent.objects.filter(patient=patient, antecedent=antecedent).first()
    if link is None:
        link = PatientAntecedent.objects.create(patient=patient, antecedent=antecedent,
                                                notes=notes.strip(), created_by=by)
    else:
        link.is_active, link.notes, link.created_by = True, notes.strip(), by
        link.save()
    _log("ANTECEDENTE_AGREGADO", patient, by, {"antecedente": antecedent.name})
    return link


def remove_antecedent(*, link: PatientAntecedent, by=None) -> PatientAntecedent:
    link.is_active = False
    link.save(update_fields=["is_active", "updated_at"])
    _log("ANTECEDENTE_RETIRADO", link.patient, by, {"antecedente": link.antecedent.name})
    return link
