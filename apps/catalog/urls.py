from django.urls import path

from apps.catalog import views

app_name = "catalog"

urlpatterns = [
    path("examenes/", views.test_list, name="tests"),
    path("examenes/nuevo/", views.test_edit, name="test-new"),
    path("examenes/<uuid:pk>/", views.test_edit, name="test"),
    path("examenes/<uuid:test_pk>/parametros/nuevo/", views.parameter_edit,
         name="parameter-new"),
    path("parametros/<uuid:pk>/", views.parameter_edit, name="parameter"),
    path("perfiles/", views.profile_list, name="profiles"),
    path("perfiles/nuevo/", views.profile_edit, name="profile-new"),
    path("perfiles/<uuid:pk>/", views.profile_edit, name="profile"),
]
