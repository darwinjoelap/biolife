from .base import *  # noqa: F401,F403

DEBUG = True

INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE.insert(1, "debug_toolbar.middleware.DebugToolbarMiddleware")
INTERNAL_IPS = ["127.0.0.1"]

# FASE 08: agregar debug_toolbar.urls a config/urls_tenant.py cuando existan rutas reales

# En desarrollo y tests no hay collectstatic: sin manifiesto de versiones, {% static %}
# fallaría con la storage de producción cuando DEBUG=False (pytest lo fuerza).
STORAGES = {
    **STORAGES,
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
