from django.urls import path

from apps.patients import views

app_name = "patients"

urlpatterns = [
    path("nuevo/", views.patient_create, name="create"),
]
