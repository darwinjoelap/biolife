"""Datos del laboratorio (Fase 11b): pantalla propia, sin /admin."""
from django.contrib import messages
from django.shortcuts import redirect, render

from apps.accounts.permissions import ADMIN_ROLES, role_required
from apps.settings_lab.forms import LabSettingsForm
from apps.settings_lab.models import TenantSettings
from apps.settings_lab.services.lab_settings import update_lab_settings


@role_required(*ADMIN_ROLES)
def edit(request):
    form = LabSettingsForm(request.POST or None, request.FILES or None,
                           instance=TenantSettings.get_solo())
    if request.method == "POST" and form.is_valid():
        update_lab_settings(form=form, by=request.user)
        messages.success(request, "Datos del laboratorio guardados.")
        return redirect("settings_lab:edit")
    return render(request, "settings_lab/edit.html", {"form": form,
                                                      "tenant": request.tenant})
