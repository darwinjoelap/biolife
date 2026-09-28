"""Antecedentes en las tablas auxiliares de `core` (Fase 11e). Se registran desde
`PatientsConfig.ready()`."""
from apps.accounts.permissions import CLINICAL_EDIT_ROLES, VIEW_ROLES, user_has_any_role
from apps.core.aux_tables import AuxTable, register
from apps.patients.forms import AntecedentConfigForm
from apps.patients.models import Antecedent
from apps.patients.selectors.antecedent_queries import antecedents
from apps.patients.services.antecedent_config import save_antecedent

register(AuxTable(
    key="antecedentes", title="Antecedentes", singular="antecedente", icon="activity",
    group="Pacientes", position=40,
    description="Antecedentes clínicos (diabetes, hipertensión…) y qué parámetros vigilar "
                "en la evolución del paciente.",
    form_class=AntecedentConfigForm, queryset=antecedents,
    get=lambda pk: Antecedent.objects.get(pk=pk), new=Antecedent,
    columns=["Antecedente", "Código", "Parámetros a vigilar", "Pacientes"],
    row=lambda a: [a.name, a.code, a.parameter_count, a.patient_count],
    save=save_antecedent, count=lambda: Antecedent.objects.filter(is_active=True).count(),
    layout={"code": "col-3", "name": "col-5", "order_index": "col-2", "is_active": "col-2",
            "description": "col-12", "suggested_parameters": "col-12"},
    can_view=lambda user: user_has_any_role(user, *VIEW_ROLES),
    can_edit=lambda user: user_has_any_role(user, *CLINICAL_EDIT_ROLES),
    editors="Administrador y bioanalista",
))
