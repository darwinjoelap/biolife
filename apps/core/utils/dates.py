from datetime import date, datetime

from django.utils import timezone


def age_in_days(birth_date: date, reference_date: date | None = None) -> int:
    """Edad en días completos entre birth_date y reference_date (hoy por defecto)."""
    if reference_date is None:
        reference_date = timezone.localdate()
    if birth_date > reference_date:
        raise ValueError(
            "La fecha de nacimiento no puede ser posterior a la fecha de referencia."
        )
    return (reference_date - birth_date).days


def format_time_12h(dt: datetime, tz=None) -> str:
    """Formatea una hora en 12h con A.M./P.M. y puntos, como imprime el laboratorio."""
    local_dt = timezone.localtime(dt, tz) if timezone.is_aware(dt) else dt
    formatted = local_dt.strftime("%I:%M %p").lstrip("0")
    return formatted.replace("AM", "A.M.").replace("PM", "P.M.")
