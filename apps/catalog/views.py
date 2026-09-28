"""Catálogo sin /admin (Fase 11c): exámenes con sus parámetros, rangos y observaciones, y
perfiles. Las vistas sólo orquestan: formularios + services/selectors."""
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import redirect, render

from apps.accounts.permissions import (
    CATALOG_EDIT_ROLES,
    CLINICAL_EDIT_ROLES,
    VIEW_ROLES,
    role_required,
    user_has_any_role,
)
from apps.catalog.admin_forms import RangeProbeForm
from apps.catalog.forms import (
    ObservationFormSet,
    ParameterForm,
    ParameterGroupFormSet,
    ProfileForm,
    SampleRequirementFormSet,
    TestForm,
    range_formset,
)
from apps.catalog.models import Parameter, Profile, Test
from apps.catalog.selectors import catalog_queries as q
from apps.catalog.services import catalog_editing as svc
from apps.catalog.services.reference_range_management import (
    explain_resolution,
    parameter_range_issues,
)
from apps.core.exceptions import ApplicationError


def _get(getter, pk):
    try:
        return getter(pk=pk)
    except (Test.DoesNotExist, Parameter.DoesNotExist, Profile.DoesNotExist,
            ValidationError) as exc:
        raise Http404("No encontrado.") from exc


def _can(request, roles) -> bool:
    return user_has_any_role(request.user, *roles)


# Exámenes --------------------------------------------------------------------------------
@role_required(*VIEW_ROLES)
def test_list(request):
    return render(request, "catalog/test_list.html", {
        "tests": q.catalog_tests(query=request.GET.get("q", ""),
                                 section_id=request.GET.get("seccion", ""),
                                 show_inactive=request.GET.get("inactivos") == "1"),
        "sections": q.active_sections(), "query": request.GET.get("q", ""),
        "section_id": request.GET.get("seccion", ""),
        "show_inactive": request.GET.get("inactivos") == "1",
    })


def _test_forms(request, test):
    data = request.POST if request.method == "POST" else None
    locked = test is not None and q.test_in_use(test=test)
    instance = test or Test()
    return (TestForm(data, instance=test, code_locked=locked),
            SampleRequirementFormSet(data, instance=instance, prefix="tubos"),
            ParameterGroupFormSet(data, instance=instance, prefix="grupos"),
            ObservationFormSet(data, instance=instance, prefix="obs"))


def _readonly(*items) -> None:
    """Deshabilita formularios (y formsets) que el rol no puede cambiar."""
    for item in items:
        for form in getattr(item, "forms", [item]):
            for field in form.fields.values():
                field.disabled = True


@role_required(*VIEW_ROLES)
def test_edit(request, pk=None):
    test = _get(q.test_detail, pk) if pk else None
    can_edit, clinical = _can(request, CATALOG_EDIT_ROLES), _can(request, CLINICAL_EDIT_ROLES)
    form, reqs, groups, obs = _test_forms(request, test)
    if not can_edit:
        _readonly(form, reqs, groups, *([] if clinical else [obs]))
    if request.method == "POST":
        saved = _save_test(request, test, form, reqs, groups, obs, can_edit, clinical)
        if saved is not None:
            messages.success(request, f"Examen {saved.code} guardado.")
            return redirect("catalog:test", pk=saved.pk)
    return render(request, "catalog/test_edit.html", {
        "test": test, "form": form, "reqs": reqs, "groups": groups, "obs": obs,
        "can_edit": can_edit, "clinical_edit": clinical,
    })


def _save_test(request, test, form, reqs, groups, obs, can_edit, clinical):
    """El administrador guarda todo; el bioanalista, sólo las observaciones."""
    if not (can_edit or (clinical and test is not None)):
        raise PermissionDenied("Su rol no puede editar exámenes.")
    to_check = (form, reqs, groups, obs) if can_edit else (obs,)
    if not all(f.is_valid() for f in to_check):
        return None
    try:
        if can_edit:
            return svc.save_test(form=form, requirements=reqs, groups=groups,
                                 observations=obs, by=request.user)
        return svc.save_observations(test=test, observations=obs, by=request.user)
    except ApplicationError as exc:
        messages.error(request, exc.message)
        return None


# Parámetros ------------------------------------------------------------------------------
@role_required(*VIEW_ROLES)
def parameter_edit(request, pk=None, test_pk=None):
    parameter = _get(q.parameter_detail, pk) if pk else None
    test = parameter.test if parameter else _get(q.test_detail, test_pk)
    can_edit, clinical = _can(request, CATALOG_EDIT_ROLES), _can(request, CLINICAL_EDIT_ROLES)
    data = request.POST if request.method == "POST" else None
    locked = bool(parameter and q.parameter_in_use(parameter=parameter))
    form = ParameterForm(data, instance=parameter or Parameter(test=test), test=test,
                         locked=locked)
    ranges = range_formset(parameter, data) if parameter else None
    if not can_edit:
        _readonly(form, *([] if clinical or ranges is None else [ranges]))
    if request.method == "POST":
        if not (can_edit or clinical):
            raise PermissionDenied("Su rol no puede editar el catálogo.")
        saved = _save_parameter(request, form, ranges, test, can_edit)
        if saved is not None:
            return redirect("catalog:parameter", pk=saved.pk)
    return render(request, "catalog/parameter_edit.html", {
        "parameter": parameter, "test": test, "form": form, "ranges": ranges,
        "can_edit": can_edit, "clinical_edit": clinical,
        "issues": parameter_range_issues(parameter=parameter) if parameter else [],
        "probe": _probe(request, parameter),
    })


def _save_parameter(request, form, ranges, test, can_edit):
    """Guarda lo que el rol permite: el administrador todo; el bioanalista sólo rangos."""
    try:
        if can_edit and form.is_valid() and (ranges is None or ranges.is_valid()):
            parameter, warnings = svc.save_parameter(form=form, ranges=ranges,
                                                     by=request.user)
        elif not can_edit and ranges is not None and ranges.is_valid():
            parameter = form.instance
            warnings = svc.save_ranges(parameter=parameter, ranges=ranges, by=request.user)
        else:
            return None
    except ApplicationError as exc:
        messages.error(request, exc.message)
        return None
    messages.success(request, f"Parámetro {parameter.code} guardado.")
    for warning in warnings:
        messages.warning(request, warning)
    return parameter


def _probe(request, parameter):
    if parameter is None or "sexo" not in request.GET:
        return {"form": RangeProbeForm(), "explanation": None}
    form = RangeProbeForm(request.GET)
    explanation = None
    if form.is_valid():
        explanation = explain_resolution(
            parameter=parameter, sex=form.cleaned_data["sexo"], age_days=form.age_days(),
            condition=form.cleaned_data["condicion"])
    return {"form": form, "explanation": explanation}


# Perfiles --------------------------------------------------------------------------------
@role_required(*VIEW_ROLES)
def profile_list(request):
    return render(request, "catalog/profile_list.html", {
        "profiles": q.catalog_profiles(show_inactive=request.GET.get("inactivos") == "1"),
        "show_inactive": request.GET.get("inactivos") == "1",
    })


@role_required(*VIEW_ROLES)
def profile_edit(request, pk=None):
    profile = _get(q.get_profile, pk) if pk else None
    can_edit = _can(request, CATALOG_EDIT_ROLES)
    form = ProfileForm(request.POST or None, instance=profile)
    chosen = q.profile_tests(profile=profile) if profile else []
    if request.method == "POST":
        if not can_edit:
            raise PermissionDenied("Sólo el administrador edita perfiles.")
        chosen = q.active_tests_by_ids(ids=request.POST.getlist("tests"))
        order = {str(i): n for n, i in enumerate(request.POST.getlist("tests"))}
        chosen.sort(key=lambda t: order.get(str(t.pk), 0))
        if form.is_valid():
            try:
                profile, warnings = svc.save_profile(form=form, tests=chosen, by=request.user)
            except ApplicationError as exc:
                messages.error(request, exc.message)
            else:
                messages.success(request, f"Perfil {profile.code} guardado.")
                for warning in warnings:
                    messages.warning(request, warning)
                return redirect("catalog:profile", pk=profile.pk)
    return render(request, "catalog/profile_edit.html", {
        "profile": profile, "form": form, "can_edit": can_edit,
        "chosen_json": [_test_json(t) for t in chosen],
        "all_tests_json": [_test_json(t) for t in q.all_active_tests()],
    })


def _test_json(test) -> dict:
    return {"id": str(test.pk), "code": test.code, "name": test.name,
            "section": test.section.name if test.section_id else ""}
