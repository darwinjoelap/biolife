from .base import *  # noqa: F401,F403

DEBUG = True

INSTALLED_APPS += ["debug_toolbar"]
MIDDLEWARE.insert(1, "debug_toolbar.middleware.DebugToolbarMiddleware")
INTERNAL_IPS = ["127.0.0.1"]

# FASE 08: agregar debug_toolbar.urls a config/urls_tenant.py cuando existan rutas reales
