from django.urls import path

from apps.billing import views

app_name = "billing"

urlpatterns = [
    path("", views.grid, name="grid"),
    path("tasa/", views.save_rate, name="rate"),
    path("<uuid:pk>/precio/", views.save_price, name="price"),
    path("<uuid:pk>/ajustar/", views.adjust, name="adjust"),
    path("<uuid:pk>/copiar/", views.copy_list, name="copy"),
    path("<uuid:pk>/predeterminada/", views.make_default, name="default"),
]
