"""Pantallas de pacientes: registro desde la recepción (Fase 09); lista, ficha,
representantes, antecedentes y evolución (Fase 11e). Sólo orquestan."""
import uuid

from django.contrib import messages
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.accounts.permissions import RECEPTION_ROLES, VIEW_ROLES, role_required
from apps.core.exceptions import ApplicationError
from apps.orders.selectors.order_queries import patient_orders
from apps.patients.forms import AntecedentForm, GuardianForm, PatientDataForm, PatientForm
from apps.patients.selectors import patient_queries as q
from apps.patients.services import patient_editing as svc
from apps.patients.services.patient_age import patient_age_text
from apps.patients.services.patient_creation import register_patient
from apps.reports.services.evolution_pdf import render_evolution_pdf
from apps.results.selectors.evolution import evolution_series, series_for
from apps.results.services.evolution_chart import delta_text, series_svg, trend_cards


def _next_url(request, patient) -> str:
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target == reverse("patients:list"):
        return reverse("patients:detail", args=[patient.pk])
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = reverse("orders:new")
    separator = "&" if "?" in target else "?"
    return f"{target}{separator}paciente={patient.pk}"


def _patient(pk):
    patient = q.patient_detail(pk=pk)
    if patient is None:
        raise Http404("Paciente no encontrado.")
    return patient


def _uuids(values) -> list[str]:
    ids = []
    for value in values:
        try:
            ids.append(str(uuid.UUID(str(value))))
        except ValueError:
            continue
    return ids


@role_required(*RECEPTION_ROLES)
def patient_create(request):
    form = PatientForm(request.POST or None, initial=request.GET.dict() or None)
    if request.method == "POST" and form.is_valid():
        try:
            patient = register_patient(guardian_data=form.guardian_data(),
                                       created_by=request.user, **form.patient_data())
        except ApplicationError as exc:
            form.add_error(None, exc.message)
        else:
            messages.success(request, f"Paciente {patient.internal_code} registrado.")
            return redirect(_next_url(request, patient))
    return render(request, "patients/patient_form.html",
                  {"form": form, "next": request.GET.get("next", "")})


# Lista y ficha (Fase 11e) ---------------------------------------------------------------
@role_required(*VIEW_ROLES)
def patient_list(request):
    query = request.GET.get("q", "").strip()
    return render(request, "patients/patient_list.html",
                  {"patients": q.patient_list(query=query), "query": query})


@role_required(*VIEW_ROLES)
def patient_detail(request, pk):
    patient = _patient(pk)
    suggested = q.suggested_parameters(patient=patient)
    suggested_ids = [str(p.pk) for p in suggested]
    series = evolution_series(patient=patient)
    with_data = {str(s["parameter"].pk) for s in series}
    return render(request, "patients/patient_detail.html", {
        "patient": patient, "age": patient_age_text(patient),
        "orders": patient_orders(patient=patient),
        "cards": trend_cards(series, suggested_ids=suggested_ids),
        "series_count": len(series),
        "suggested_without_data": [p for p in suggested if str(p.pk) not in with_data],
        "antecedent_form": AntecedentForm(options=q.antecedent_options(patient=patient)),
    })


@role_required(*RECEPTION_ROLES)
def patient_edit(request, pk):
    patient = _patient(pk)
    form = PatientDataForm(request.POST or None, initial=PatientDataForm.initial_for(patient))
    if request.method == "POST" and form.is_valid():
        try:
            svc.update_patient(patient=patient, data=form.patient_data(current=patient),
                               by=request.user)
        except ApplicationError as exc:
            form.add_error(None, exc.message)
        else:
            messages.success(request, "Datos del paciente guardados.")
            return redirect("patients:detail", pk=patient.pk)
    return render(request, "patients/patient_edit.html", {"patient": patient, "form": form})


# Representantes y antecedentes -------------------------------------------------------------
@role_required(*RECEPTION_ROLES)
def guardian_add(request, pk):
    patient = _patient(pk)
    form = GuardianForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        svc.add_guardian(patient=patient, data=form.cleaned_data, by=request.user)
        messages.success(request, "Representante agregado.")
        return redirect("patients:detail", pk=patient.pk)
    return render(request, "patients/guardian_form.html", {"patient": patient, "form": form})


@require_POST
@role_required(*RECEPTION_ROLES)
def guardian_action(request, pk, link_pk, action):
    patient = _patient(pk)
    link = q.guardian_link(patient=patient, pk=link_pk)
    if link is None or action not in ("retirar", "principal"):
        raise Http404("Representante no encontrado.")
    try:
        if action == "retirar":
            svc.deactivate_guardian(link=link, by=request.user)
        else:
            svc.make_primary(link=link, by=request.user)
    except ApplicationError as exc:
        messages.error(request, exc.message)
    return redirect("patients:detail", pk=patient.pk)


@require_POST
@role_required(*RECEPTION_ROLES)
def antecedent_add(request, pk):
    patient = _patient(pk)
    form = AntecedentForm(request.POST, options=q.antecedent_options(patient=patient))
    if form.is_valid():
        svc.add_antecedent(patient=patient, antecedent=form.cleaned_data["antecedent"],
                           notes=form.cleaned_data["notes"], by=request.user)
        messages.success(request, f"Antecedente «{form.cleaned_data['antecedent']}» "
                                  "registrado.")
    else:
        messages.error(request, "Elija un antecedente.")
    return redirect("patients:detail", pk=patient.pk)


@require_POST
@role_required(*RECEPTION_ROLES)
def antecedent_remove(request, pk, link_pk):
    patient = _patient(pk)
    link = q.antecedent_link(patient=patient, pk=link_pk)
    if link is None:
        raise Http404("Antecedente no encontrado.")
    svc.remove_antecedent(link=link, by=request.user)
    return redirect("patients:detail", pk=patient.pk)


# Evolución ------------------------------------------------------------------------------------
@role_required(*VIEW_ROLES)
def evolution(request, pk):
    patient = _patient(pk)
    series_list = evolution_series(patient=patient)
    suggested_ids = [str(p.pk) for p in q.suggested_parameters(patient=patient)]
    by_id = {str(s["parameter"].pk): s for s in series_list}
    wanted = _uuids([request.GET.get("p", "")]) or [i for i in suggested_ids if i in by_id]
    current = by_id.get(wanted[0]) if wanted else None
    current = current or (series_list[0] if series_list else None)
    rows = []
    if current:
        rows = [(p, delta_text(p.delta_pct)) for p in reversed(current["points"])]
    return render(request, "patients/evolution.html", {
        "patient": patient, "age": patient_age_text(patient), "series_list": series_list,
        "current": current, "chart": series_svg(current) if current else "", "rows": rows,
        "pdf_default": {str(current["parameter"].pk)} | set(suggested_ids) if current
        else set(suggested_ids),
    })


@role_required(*VIEW_ROLES)
def evolution_pdf(request, pk):
    patient = _patient(pk)
    series_list = series_for(patient=patient, parameter_ids=_uuids(request.GET.getlist("p")))
    if not series_list:
        messages.error(request, "Elija al menos un parámetro con resultados.")
        return redirect("patients:evolution", pk=patient.pk)
    pdf = render_evolution_pdf(patient=patient, series_list=series_list)
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (f'inline; filename="evolucion-'
                                       f'{patient.internal_code}.pdf"')
    return response
