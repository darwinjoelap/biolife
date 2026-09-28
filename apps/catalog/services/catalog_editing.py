"""Edición del catálogo desde las pantallas del laboratorio (Fase 11c, ADR-030).

- Nada del catálogo se borra: exámenes, parámetros, rangos y observaciones se
  **desactivan** (hay órdenes, resultados e informes que los referencian). Sólo se pueden
  quitar filas de tubos requeridos y grupos vacíos, que no tienen historial propio.
- Un examen ya ordenado conserva su código; un parámetro con resultados conserva código y
  tipo de valor (los formularios los bloquean).
- Toda edición queda en la bitácora (`AuditLog`) con los campos que cambiaron.
"""
from __future__ import annotations

from django.db import transaction

from apps.accounts.services.audit import log_action
from apps.catalog.models import Parameter, Profile, Test
from apps.catalog.selectors.catalog_queries import calculation_input_tests
from apps.catalog.services.formula_validation import sync_parameter_dependencies
from apps.catalog.services.profiles import set_profile_tests
from apps.core.exceptions import ApplicationError


def _log(action: str, obj, by, changes: dict | None = None) -> None:
    log_action(action=action, user=by, model_name=f"catalog.{type(obj).__name__}",
               object_id=str(obj.pk), changes=changes)


def _formset_changes(formset) -> bool:
    return any(f.has_changed() for f in formset.forms) or bool(
        getattr(formset, "deleted_forms", []))


@transaction.atomic
def save_test(*, form, requirements, groups, observations=None, by=None) -> Test:
    """Examen con sus tubos, grupos y observaciones propias (formularios ya validados)."""
    test = form.save()
    for formset in (requirements, groups, observations):
        if formset is None:
            continue
        formset.instance = test
        for deleted in getattr(formset, "deleted_forms", []):
            obj = deleted.instance
            if getattr(obj, "pk", None) and hasattr(obj, "parameters") \
                    and obj.parameters.exists():
                raise ApplicationError(
                    f"El grupo «{obj.name}» tiene parámetros: muévalos a otro grupo antes "
                    "de quitarlo.")
        formset.save()
    changes = {"campos": form.changed_data} if form.changed_data else {}
    if any(_formset_changes(f) for f in (requirements, groups, observations) if f):
        changes["detalle"] = "tubos/grupos/observaciones"
    if changes:
        _log("EXAMEN_GUARDADO", test, by, changes)
    return test


@transaction.atomic
def save_observations(*, test: Test, observations, by=None) -> Test:
    """Observaciones predefinidas propias del examen (lo que puede cambiar el bioanalista)."""
    observations.instance = test
    observations.save()
    if _formset_changes(observations):
        _log("OBSERVACIONES_GUARDADAS", test, by, {"observaciones": True})
    return test


@transaction.atomic
def save_parameter(*, form, ranges=None, by=None) -> tuple[Parameter, list[str]]:
    """Parámetro (+ sus rangos). Devuelve (parámetro, avisos de cobertura de rangos)."""
    parameter = form.save()
    sync_parameter_dependencies(parameter=parameter)
    warnings: list[str] = []
    if ranges is not None:
        ranges.instance = parameter
        ranges.save()
        warnings = list(getattr(ranges, "range_warnings", []))
    changes = {}
    if form.changed_data:
        changes["campos"] = form.changed_data
    if ranges is not None and _formset_changes(ranges):
        changes["rangos"] = True
    if changes:
        _log("PARAMETRO_GUARDADO", parameter, by, changes)
    return parameter, warnings


@transaction.atomic
def save_ranges(*, parameter: Parameter, ranges, by=None) -> list[str]:
    """Sólo los rangos y críticos (lo que puede cambiar el bioanalista)."""
    ranges.instance = parameter
    ranges.save()
    if _formset_changes(ranges):
        _log("RANGOS_GUARDADOS", parameter, by, {"rangos": True})
    return list(getattr(ranges, "range_warnings", []))


@transaction.atomic
def save_profile(*, form, tests, by=None) -> tuple[Profile, list[str]]:
    """Perfil y su composición ordenada. Si falta un examen que alimenta un cálculo del
    perfil, se guarda igual y se avisa (el laboratorio decide)."""
    if not tests:
        raise ApplicationError("Agregue al menos un examen al perfil.")
    profile = form.save()
    set_profile_tests(profile=profile, tests=tests, allow_incomplete=True)
    missing = calculation_input_tests(tests=tests)
    warnings = []
    if missing:
        warnings.append("Este perfil no incluye exámenes que alimentan sus cálculos: "
                        + ", ".join(sorted(t.name for t in missing)) + ".")
    _log("PERFIL_GUARDADO", profile, by, {"examenes": [t.code for t in tests]})
    return profile, warnings
