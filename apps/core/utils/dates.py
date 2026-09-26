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


# --- Edad expresada en años/meses/días <-> días (rangos de referencia, ADR-020) ---------
# Un año = 365,25 días y un mes = 1/12 de año (30,4375 días), redondeando al día. Así
# "12 meses" y "1 año" dan lo mismo (365) y la conversión es exacta ida y vuelta.
DAYS_PER_YEAR = 365.25
DAYS_PER_MONTH = DAYS_PER_YEAR / 12


def age_parts_to_days(*, years: int = 0, months: int = 0, days: int = 0) -> int:
    """Convierte una edad en años/meses/días a días."""
    if min(years, months, days) < 0:
        raise ValueError("La edad no puede ser negativa.")
    return round(years * DAYS_PER_YEAR + months * DAYS_PER_MONTH) + days


def days_to_age_parts(total_days: int) -> tuple[int, int, int]:
    """Inversa exacta de `age_parts_to_days`: (años, meses, días) con meses < 12."""
    if total_days < 0:
        raise ValueError("La edad no puede ser negativa.")
    years = max(int(total_days // DAYS_PER_YEAR) - 1, 0)
    while age_parts_to_days(years=years + 1) <= total_days:
        years += 1
    months = 0
    while months < 11 and age_parts_to_days(years=years, months=months + 1) <= total_days:
        months += 1
    days = total_days - age_parts_to_days(years=years, months=months)
    return years, months, days


def format_age_days(total_days: int) -> str:
    """'1 año 6 meses', '29 días', '0 días'."""
    years, months, days = days_to_age_parts(total_days)
    parts = []
    for value, singular, plural in (
        (years, "año", "años"), (months, "mes", "meses"), (days, "día", "días"),
    ):
        if value:
            parts.append(f"{value} {singular if value == 1 else plural}")
    return " ".join(parts) or "0 días"
