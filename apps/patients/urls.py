from django.urls import path

from apps.patients import views

app_name = "patients"

urlpatterns = [
    path("", views.patient_list, name="list"),
    path("nuevo/", views.patient_create, name="create"),
    path("<uuid:pk>/", views.patient_detail, name="detail"),
    path("<uuid:pk>/editar/", views.patient_edit, name="edit"),
    path("<uuid:pk>/representantes/nuevo/", views.guardian_add, name="guardian-add"),
    path("<uuid:pk>/representantes/<uuid:link_pk>/<slug:action>/", views.guardian_action,
         name="guardian-action"),
    path("<uuid:pk>/antecedentes/", views.antecedent_add, name="antecedent-add"),
    path("<uuid:pk>/antecedentes/<uuid:link_pk>/retirar/", views.antecedent_remove,
         name="antecedent-remove"),
    path("<uuid:pk>/evolucion/", views.evolution, name="evolution"),
    path("<uuid:pk>/evolucion/pdf/", views.evolution_pdf, name="evolution-pdf"),
]
