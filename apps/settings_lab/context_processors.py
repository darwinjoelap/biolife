from apps.settings_lab.models import TenantSettings


def tenant_settings(request):
    tenant = getattr(request, "tenant", None)
    if tenant is None or tenant.schema_name == "public":
        return {}
    return {"tenant_settings": TenantSettings.get_solo()}
