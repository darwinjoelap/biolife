"""Resolución de rangos de referencia. Único punto de la app que decide qué
`ReferenceRange` aplica a un resultado — la captura/validación de resultados (Fase 10)
debe llamar siempre a `resolve_reference_range()`, nunca filtrar `ReferenceRange`
directamente."""
from django.db.models import F, Q

from apps.catalog.models import Parameter, ReferenceRange


def resolve_reference_range(
    *,
    parameter: Parameter,
    sex: str,
    age_days: int,
    condition: str = ReferenceRange.Condition.NINGUNA,
) -> ReferenceRange | None:
    """Resuelve el `ReferenceRange` vigente para un parámetro, sexo y edad en días.

    Filtra por el parámetro, por sexo (coincidente o `ANY`), por el rango etario que
    contiene `age_days` (límites inclusivos) y por `condition`. Ordena por `priority`
    descendente y, a igualdad de prioridad, por el rango etario más estrecho primero.
    Devuelve la primera coincidencia o `None` si ninguna aplica — en ese caso el informe
    imprime la celda de referencia vacía (documentado para MONOCITOS/BASÓFILOS en
    `docs/01_MODELO_DATOS.md`; el propio informe, no este resolver, decide qué hacer con
    `None`)."""
    candidates = (
        ReferenceRange.objects.filter(
            parameter=parameter,
            age_min_days__lte=age_days,
            age_max_days__gte=age_days,
            condition=condition,
            is_active=True,  # un rango desactivado en la ficha del examen no aplica
        )
        .filter(Q(sex=sex) | Q(sex=ReferenceRange.Sex.ANY))
        .annotate(_age_window=F("age_max_days") - F("age_min_days"))
        .order_by("-priority", "_age_window")
    )
    return candidates.first()
