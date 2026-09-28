"""Consultas de la tabla auxiliar de antecedentes (Fase 11e)."""
from django.db.models import Count, Q

from apps.patients.models import Antecedent


def antecedents(*, show_inactive=False, query=""):
    qs = Antecedent.objects.annotate(
        parameter_count=Count("suggested_parameters", distinct=True),
        patient_count=Count("patients", filter=Q(patients__is_active=True), distinct=True))
    if not show_inactive:
        qs = qs.filter(is_active=True)
    if query:
        qs = qs.filter(Q(code__icontains=query) | Q(name__icontains=query))
    return qs.order_by("order_index", "name")
