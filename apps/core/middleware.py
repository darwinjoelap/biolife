# TenantTimezoneMiddleware se mudó a apps.settings_lab.middleware en la Fase 03
# (ADR-012): "core/ no importa a nadie", y este middleware necesita el modelo
# TenantSettings de apps.settings_lab. Este módulo queda vacío a propósito;
# cualquier middleware genuinamente de core (sin dependencias de otras apps)
# puede vivir aquí en el futuro.
