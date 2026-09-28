"""Formularios de monedas y descuentos (Fase 11d, ADR-031)."""
from django import forms

from apps.billing.models import Currency, Discount


class CurrencyForm(forms.ModelForm):
    """La moneda base se define al crear el laboratorio y no cambia desde aquí: cambiarla
    invertiría todas las tasas y listas. El código ISO tampoco cambia una vez creada."""

    class Meta:
        model = Currency
        fields = ["code", "name", "symbol", "decimals", "order_index", "is_active"]
        labels = {"is_active": "Activa"}
        help_texts = {"code": "ISO 4217 de 3 letras: USD, VES, EUR…",
                      "decimals": "Decimales con que se muestran los montos."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance._state.adding:
            self.fields["code"].disabled = True
            self.fields["code"].help_text = "El código de una moneda existente no cambia."

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        if len(code) != 3 or not code.isalpha():
            raise forms.ValidationError("Use el código ISO de 3 letras.")
        return code


class DiscountForm(forms.ModelForm):
    class Meta:
        model = Discount
        fields = ["code", "name", "kind", "value", "currency", "scope", "tests", "profiles",
                  "valid_from", "valid_until", "is_stackable", "requires_authorization",
                  "order_index", "notes", "is_active"]
        labels = {"is_active": "Activo"}
        widgets = {"valid_from": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
                   "valid_until": forms.DateInput(attrs={"type": "date"},
                                                  format="%Y-%m-%d"),
                   "notes": forms.Textarea(attrs={"rows": 2}),
                   "tests": forms.SelectMultiple(attrs={"size": 8}),
                   "profiles": forms.SelectMultiple(attrs={"size": 8})}
        help_texts = {
            "value": "Porcentaje (1 a 100) o monto fijo.",
            "currency": "Sólo para monto fijo.",
            "tests": "Sólo si el alcance es por examen/perfil. Ctrl+clic para varios.",
            "profiles": "Sólo si el alcance es por examen/perfil.",
            "requires_authorization": "Al aplicarlo en una orden se pide autorización.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["currency"].queryset = Currency.objects.filter(is_active=True)
        for name in ("tests", "profiles"):
            field = self.fields[name]
            field.required = False
            field.queryset = field.queryset.filter(is_active=True).order_by("name")

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper().replace(" ", "_")

    def clean(self):
        cleaned = super().clean()
        kind, value = cleaned.get("kind"), cleaned.get("value")
        if value is not None and value <= 0:
            self.add_error("value", "Debe ser mayor que cero.")
        if kind == Discount.Kind.PERCENT:
            cleaned["currency"] = None
            if value is not None and value > 100:
                self.add_error("value", "Un porcentaje no pasa de 100.")
        elif kind == Discount.Kind.FIXED_AMOUNT and not cleaned.get("currency"):
            self.add_error("currency", "Indique la moneda del monto fijo.")
        if cleaned.get("scope") == Discount.Scope.ITEM:
            if not cleaned.get("tests") and not cleaned.get("profiles"):
                self.add_error("tests", "Elija al menos un examen o perfil.")
        else:
            cleaned["tests"], cleaned["profiles"] = [], []
        start, end = cleaned.get("valid_from"), cleaned.get("valid_until")
        if start and end and end < start:
            self.add_error("valid_until", "No puede ser anterior a «Vigente desde».")
        return cleaned
