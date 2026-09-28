"""Verificación pública por QR (sin sesión)."""
from django.urls import path

from apps.reports import views

app_name = "verify"

urlpatterns = [
    path("<str:code>/", views.verify, name="page"),
    path("<str:code>/pdf/", views.verify_pdf, name="pdf"),
]
