from django.conf import settings
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path

# TODO(FASE 08): reemplazar por la vista real de inicio del tenant


def _placeholder(request):
    return HttpResponse(f"Tenant activo: {request.tenant.name}")


urlpatterns = [
    path("", _placeholder, name="tenant-home"),
    path("cuenta/", include("apps.accounts.urls")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    import debug_toolbar
    from django.conf.urls.static import static

    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
