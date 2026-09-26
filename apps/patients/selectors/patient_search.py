from django.db.models import Q, QuerySet

from apps.patients.models import Patient


def search_patients(*, query: str) -> QuerySet[Patient]:
    """Busca por código interno, número de documento, nombre o apellido.

    select_related en la localidad porque cualquier listado de resultados suele
    mostrarla junto al nombre del paciente.
    """
    query = query.strip()
    if not query:
        return Patient.objects.none()

    return Patient.objects.select_related("locality").filter(
        Q(internal_code__icontains=query)
        | Q(document_number__icontains=query)
        | Q(first_name__icontains=query)
        | Q(last_name__icontains=query)
    )
