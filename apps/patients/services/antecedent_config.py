"""Configuración de antecedentes en Tablas auxiliares (Fase 11e, ADR-032)."""
from django.db import transaction

from apps.accounts.services.audit import log_action
from apps.patients.models import Antecedent


@transaction.atomic
def save_antecedent(*, form, formsets=(), by=None) -> Antecedent:
    created = form.instance._state.adding
    antecedent = form.save()
    if created or form.changed_data:
        log_action(action="TABLA_CREADA" if created else "TABLA_MODIFICADA", user=by,
                   model_name="patients.Antecedent", object_id=str(antecedent.pk),
                   changes={"campos": form.changed_data} if form.changed_data else None)
    return antecedent
