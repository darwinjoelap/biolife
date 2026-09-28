from django.urls import path

from apps.settings_lab import views

app_name = "settings_lab"

urlpatterns = [
    path("", views.edit, name="edit"),
]
