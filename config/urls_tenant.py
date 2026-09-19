from django.conf import settings
from django.http import HttpResponse
from django.urls import include, path

# TODO(FASE 08): reemplazar por la vista real de inicio del tenant


def _placeholder(request):
    return HttpResponse(f"Tenant activo: {request.tenant.name}")


urlpatterns = [
    path("", _placeholder, name="tenant-home"),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
