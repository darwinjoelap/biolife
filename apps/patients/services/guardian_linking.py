from django.db import transaction

from apps.patients.models import Guardian, Patient, PatientGuardian


def create_guardian(
    *,
    document_type: str,
    document_number: str,
    first_name: str,
    last_name: str,
    phone: str = "",
    address: str = "",
    email: str = "",
) -> Guardian:
    return Guardian.objects.create(
        document_type=document_type,
        document_number=document_number,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        address=address,
        email=email,
    )


def link_guardian(
    *,
    patient: Patient,
    guardian: Guardian,
    relationship: str,
    relationship_detail: str = "",
    is_primary: bool = True,
    legal_doc_ref: str = "",
) -> PatientGuardian:
    """Vincula un representante a un paciente (al crearlo o después). Si
    is_primary=True, desmarca cualquier otro representante principal del mismo
    paciente dentro de la misma transacción."""
    with transaction.atomic():
        if is_primary:
            PatientGuardian.objects.filter(patient=patient, is_primary=True).update(
                is_primary=False
            )

        return PatientGuardian.objects.create(
            patient=patient,
            guardian=guardian,
            relationship=relationship,
            relationship_detail=relationship_detail,
            is_primary=is_primary,
            legal_doc_ref=legal_doc_ref,
        )
