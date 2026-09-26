from apps.settings_lab.models import TenantSettings


def create_default_settings() -> TenantSettings:
    """Crea el TenantSettings del tenant activo si no existe. Debe llamarse dentro
    del schema_context() del tenant."""
    return TenantSettings.get_solo()
