"""Siembra de rangos de referencia (Fase 06).

Desde la Fase 08 los exámenes, parámetros y rangos viven declarados en
`services/seeding_base_catalog.py` (fuente única, ADR-019): los 4 exámenes agregados que
sembraba esta fase (`HEM_COMP`, `PERFIL_LIPIDICO`, `COAGUL`, `QUIM`) se separaron en
exámenes individuales para poder agruparlos en perfiles. Este módulo conserva la entrada
pública `seed_reference_ranges()` y agrega el único rango que depende del Uroanálisis de la
Fase 05 (`URO_NITRITOS`, tipo `QUALITATIVE`).

**Rangos "PENDIENTE DE CONFIRMAR" / "NO CONFIRMADO"**: ver docstring de
`seeding_base_catalog.py` y ADR-016. No usar en un informe real sin revisión del laboratorio.
"""
from apps.catalog.models import CodedOption, Parameter, ReferenceRange
from apps.catalog.services.seeding_base_catalog import seed_base_catalog
from apps.core.exceptions import ApplicationError


def seed_reference_ranges() -> None:
    """Siembra el catálogo base con sus rangos (los 6 `range_type`) más el rango
    cualitativo de `URO_NITRITOS`. Idempotente. Requiere que `seed_uroanalisis()` (Fase 05)
    ya haya corrido en el tenant."""
    try:
        nitritos = Parameter.objects.get(code="URO_NITRITOS")
        negativo = CodedOption.objects.get(option_set__code="NEG_POS", value="NEGATIVO")
    except (Parameter.DoesNotExist, CodedOption.DoesNotExist) as exc:
        raise ApplicationError(
            "seed_reference_ranges() requiere que seed_uroanalisis() (Fase 05) ya haya "
            "corrido en este tenant — no se encontró URO_NITRITOS o su opción NEGATIVO."
        ) from exc

    seed_base_catalog()
    ReferenceRange.objects.get_or_create(
        parameter=nitritos, sex=ReferenceRange.Sex.ANY, age_min_days=0, age_max_days=54750,
        condition=ReferenceRange.Condition.NINGUNA,
        range_type=ReferenceRange.RangeType.QUALITATIVE,
        defaults={"display_text": "NEGATIVO", "expected_option": negativo},
    )
