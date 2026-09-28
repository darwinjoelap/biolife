"""Datos del laboratorio editados por su administrador (Fase 11b). Razón social y RIF
viven en `tenants.Tenant` (esquema `public`) y sólo los cambia el administrador del SaaS."""
from __future__ import annotations

from apps.accounts.services.audit import log_action
from apps.settings_lab.models import TenantSettings


def update_lab_settings(*, form, by=None) -> TenantSettings:
    """Guarda el formulario validado y deja en la bitácora qué campos cambiaron."""
    changed = list(form.changed_data)
    settings_obj = form.save()
    if changed:
        log_action(action="LABORATORIO_MODIFICADO", user=by,
                   model_name="settings_lab.TenantSettings", object_id="1",
                   changes={"campos": changed})
    return settings_obj
