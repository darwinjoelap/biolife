from django.urls import path

from apps.core import views, views_aux

app_name = "core"

urlpatterns = [
    path("estilo/", views.style_guide, name="style-guide"),
    path("tablas/", views_aux.hub, name="aux-hub"),
    path("tablas/<slug:key>/", views_aux.table_list, name="aux-list"),
    path("tablas/<slug:key>/nuevo/", views_aux.table_edit, name="aux-new"),
    path("tablas/<slug:key>/<uuid:pk>/", views_aux.table_edit, name="aux-edit"),
]
