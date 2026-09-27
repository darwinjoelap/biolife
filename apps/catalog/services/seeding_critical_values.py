"""Valores críticos de uso común (Fase 10, ADR-025), marcados PROPUESTO.

Valores de literatura para adultos, a confirmar por cada laboratorio en la ficha del
examen. Idempotente y no destructivo: sólo completa rangos sin críticos cargados y no toca
rangos pediátricos/neonatales (edad máxima menor a 1 año), cuyos críticos son distintos.
"""
from decimal import Decimal

from apps.catalog.models import ReferenceRange

PROPOSED_NOTE = "PROPUESTO (literatura): confirmar con el laboratorio"
ONE_YEAR_DAYS = 365

# código de parámetro: (crítico bajo, crítico alto)
CRITICAL_VALUES: dict[str, tuple[str | None, str | None]] = {
    "QUIM_POTASIO": ("2.8", "6.2"),
    "QUIM_SODIO": ("120", "160"),
    "QUIM_GLICEMIA": ("40", "450"),
    "QUIM_CALCIO": ("6.0", "13.0"),
    "QUIM_FOSFORO": ("1.0", None),
    "QUIM_CREATININA": (None, "7.0"),
    "HEM_HEMOGLOBINA": ("7.0", "20.0"),
    "HEM_HEMATOCRITO": ("20", "60"),
    "HEM_PLAQUETAS": ("20000", "1000000"),
    "HEM_GLOBULOS_BLANCOS": ("2000", "30000"),
    "COAG_INR": (None, "5.0"),
    "COAG_FIBRINOGENO": ("100", None),
}


def seed_critical_values() -> int:
    """Completa los críticos propuestos. Devuelve cuántos rangos actualizó."""
    updated = 0
    ranges = ReferenceRange.objects.filter(
        parameter__code__in=CRITICAL_VALUES, critical_low__isnull=True,
        critical_high__isnull=True, age_max_days__gte=ONE_YEAR_DAYS,
    ).select_related("parameter")
    for reference_range in ranges:
        low, high = CRITICAL_VALUES[reference_range.parameter.code]
        reference_range.critical_low = Decimal(low) if low else None
        reference_range.critical_high = Decimal(high) if high else None
        reference_range.critical_note = PROPOSED_NOTE
        reference_range.save(update_fields=["critical_low", "critical_high", "critical_note",
                                            "updated_at"])
        updated += 1
    return updated
