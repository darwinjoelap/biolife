from django.conf import settings
from django.contrib import admin
from django.urls import include, path

# TODO(FASE 08): agregar la vista de landing pública de Biolife

urlpatterns = [
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
