"""Pantallas de pacientes (Fase 09): registro desde la recepción."""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from apps.accounts.permissions import RECEPTION_ROLES, role_required
from apps.core.exceptions import ApplicationError
from apps.patients.forms import PatientForm
from apps.patients.services.patient_creation import register_patient


def _next_url(request, patient) -> str:
    target = request.POST.get("next") or request.GET.get("next") or ""
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        target = reverse("orders:new")
    separator = "&" if "?" in target else "?"
    return f"{target}{separator}paciente={patient.pk}"


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
