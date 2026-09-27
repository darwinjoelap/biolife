"""Formularios del admin para rangos de referencia (Fase 08b, ADR-020).

La edad se captura en años/meses/días (no en días crudos). "Desde" es inclusiva y "Hasta"
es **exclusiva** ("de 0 a 1 año" = hasta el día anterior a cumplir 1 año), así los tramos
consecutivos (0–1 año, 1–18 años, desde 18 años) encajan sin huecos ni solapes. "Hasta"
vacío = sin límite.
"""
from django import forms
from django.core.exceptions import ValidationError

from apps.catalog.models import ReferenceRange
from apps.catalog.services.reference_range_management import (
    EDAD_MAXIMA_DIAS,
    ERROR,
    RangeSpec,
    find_range_issues,
)
from apps.core.utils.dates import age_parts_to_days, days_to_age_parts

RANGE_TYPE_REQUIRED = {
    ReferenceRange.RangeType.CLOSED: ("low", "high"),
    ReferenceRange.RangeType.UPPER_BOUND: ("high",),
    ReferenceRange.RangeType.LOWER_BOUND: ("low",),
    ReferenceRange.RangeType.TOLERANCE: ("center", "tolerance"),
    ReferenceRange.RangeType.QUALITATIVE: ("expected_option",),
    ReferenceRange.RangeType.INTERPRETIVE: ("bands",),
}
AGE_FIELDS = ("desde_anos", "desde_meses", "desde_dias", "hasta_anos", "hasta_meses",
              "hasta_dias")


def _age_field(label: str, max_value: int | None = None) -> forms.IntegerField:
    return forms.IntegerField(
        label=label, required=False, min_value=0, max_value=max_value,
        widget=forms.NumberInput(attrs={"style": "width: 5em"}),
    )


class ReferenceRangeForm(forms.ModelForm):
    desde_anos = _age_field("Desde: años", 150)
    desde_meses = _age_field("meses", 11)
    desde_dias = _age_field("días", 400)
    hasta_anos = _age_field("Hasta (sin incluir): años", 150)
    hasta_meses = _age_field("meses", 11)
    hasta_dias = _age_field("días", 400)

    class Meta:
        model = ReferenceRange
        fields = [
            "sex", "condition", "priority", "range_type", "low", "high", "center",
            "tolerance", "expected_option", "bands", "display_text", "unit", "is_active",
            "critical_low", "critical_high", "critical_note",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = self.instance
        if not instance._state.adding:
            y, m, d = days_to_age_parts(instance.age_min_days)
            self.initial.update(desde_anos=y, desde_meses=m, desde_dias=d)
            if instance.age_max_days < EDAD_MAXIMA_DIAS:
                y, m, d = days_to_age_parts(instance.age_max_days + 1)
                self.initial.update(hasta_anos=y, hasta_meses=m, hasta_dias=d)

    def clean(self):
        cleaned = super().clean()
        desde = age_parts_to_days(
            years=cleaned.get("desde_anos") or 0, months=cleaned.get("desde_meses") or 0,
            days=cleaned.get("desde_dias") or 0,
        )
        hasta_given = any(cleaned.get(f) for f in ("hasta_anos", "hasta_meses", "hasta_dias"))
        if hasta_given:
            hasta = age_parts_to_days(
                years=cleaned.get("hasta_anos") or 0, months=cleaned.get("hasta_meses") or 0,
                days=cleaned.get("hasta_dias") or 0,
            ) - 1
            if hasta < desde:
                raise ValidationError("La edad «hasta» debe ser mayor que la edad «desde».")
            hasta = min(hasta, EDAD_MAXIMA_DIAS)
        else:
            hasta = EDAD_MAXIMA_DIAS
        self.instance.age_min_days = desde
        self.instance.age_max_days = hasta

        range_type = cleaned.get("range_type")
        for field_name in RANGE_TYPE_REQUIRED.get(range_type, ()):
            if cleaned.get(field_name) in (None, ""):
                self.add_error(field_name, "Obligatorio para este tipo de rango.")
        critical_low, critical_high = cleaned.get("critical_low"), cleaned.get("critical_high")
        if critical_low is not None and critical_high is not None and critical_low >= critical_high:
            self.add_error("critical_high", "El crítico alto debe ser mayor que el bajo.")
        if range_type == ReferenceRange.RangeType.CLOSED:
            low, high = cleaned.get("low"), cleaned.get("high")
            if low is not None and high is not None and low > high:
                self.add_error("high", "El límite superior debe ser mayor o igual al inferior.")
        return cleaned

    def as_spec(self) -> RangeSpec:
        return RangeSpec(
            sex=self.cleaned_data.get("sex"), condition=self.cleaned_data.get("condition"),
            priority=self.cleaned_data.get("priority") or 0,
            age_min_days=self.instance.age_min_days, age_max_days=self.instance.age_max_days,
            label=self.cleaned_data.get("display_text", ""),
        )


class ReferenceRangeInlineFormSet(forms.BaseInlineFormSet):
    """Revisa el conjunto completo de rangos del parámetro: bloquea los solapes ambiguos
    (ERROR) y guarda los AVISOS para mostrarlos después de guardar."""

    def clean(self):
        super().clean()
        specs = []
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or not form.cleaned_data:
                continue
            if form.cleaned_data.get("DELETE") or not form.cleaned_data.get("is_active", True):
                continue
            if form.errors:
                return
            specs.append(form.as_spec())
        issues = find_range_issues(specs)
        errors = [i.message for i in issues if i.level == ERROR]
        if errors:
            raise ValidationError(errors)
        self.range_warnings = [i.message for i in issues if i.level != ERROR]


class RangeProbeForm(forms.Form):
    """Probador: paciente de ejemplo."""

    sexo = forms.ChoiceField(
        choices=[("M", "Masculino"), ("F", "Femenino")], initial="F", label="Sexo"
    )
    anos = forms.IntegerField(label="Años", min_value=0, max_value=150, initial=30,
                              required=False)
    meses = forms.IntegerField(label="Meses", min_value=0, max_value=11, required=False)
    dias = forms.IntegerField(label="Días", min_value=0, max_value=400, required=False)
    condicion = forms.ChoiceField(
        choices=ReferenceRange.Condition.choices, initial=ReferenceRange.Condition.NINGUNA,
        label="Condición",
    )

    def age_days(self) -> int:
        data = self.cleaned_data
        return age_parts_to_days(
            years=data.get("anos") or 0, months=data.get("meses") or 0,
            days=data.get("dias") or 0,
        )
