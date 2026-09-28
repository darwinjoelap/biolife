"""Usuarios y roles del laboratorio (Fase 11b), bajo /configuracion/."""
from django.urls import path

from apps.accounts import views

app_name = "lab_users"

urlpatterns = [
    path("usuarios/", views.user_list, name="list"),
    path("usuarios/nuevo/", views.user_new, name="new"),
    path("usuarios/<int:pk>/", views.user_edit, name="edit"),
    path("usuarios/<int:pk>/activo/", views.user_toggle, name="toggle"),
    path("usuarios/<int:pk>/clave/", views.user_reset_password, name="reset-password"),
    path("roles/", views.roles, name="roles"),
]
