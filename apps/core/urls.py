from django.urls import path

from apps.core import views

app_name = "core"

urlpatterns = [
    path("estilo/", views.style_guide, name="style-guide"),
]
