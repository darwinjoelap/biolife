from django.urls import path

from apps.reports import views

app_name = "reports"

urlpatterns = [
    path("", views.worklist, name="worklist"),
    path("orden/<uuid:pk>/", views.order_reports, name="order"),
    path("orden/<uuid:pk>/emitir/", views.emit, name="emit"),
    path("orden/<uuid:pk>/entregar/", views.deliver, name="deliver"),
    path("orden/<uuid:pk>/version/<uuid:report_pk>.pdf", views.report_pdf, name="pdf"),
]
