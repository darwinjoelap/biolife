"""Formularios de las tablas auxiliares del catálogo (Fase 11d, ADR-031)."""
from django import forms

from apps.catalog.models import (
    CodedOption,
    CodedOptionSet,
    ContainerType,
    Method,
    ObservationTemplate,
    ReagentLot,
    Section,
    Unit,
)


def _code(value: str) -> str:
    return value.strip().upper().replace(" ", "_")


class _LockableCodeForm(forms.ModelForm):
    """El código queda fijo cuando el registro ya está en uso."""

    locked_help = "Ya está en uso: el código queda fijo."

    def __init__(self, *args, code_locked: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        if code_locked:
            self.fields["code"].disabled = True
            self.fields["code"].help_text = self.locked_help

    def clean_code(self):
        return _code(self.cleaned_data["code"])


class SectionForm(_LockableCodeForm):
    class Meta:
        model = Section
        fields = ["code", "name", "order_index", "print_page_break", "is_active"]
        labels = {"is_active": "Activa"}
        help_texts = {"order_index": "Orden en el informe y en las listas.",
                      "print_page_break": "La sección empieza en hoja nueva en el informe."}


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ["symbol", "description", "is_active"]
        labels = {"is_active": "Activa"}
        help_texts = {"symbol": "Tal como se imprime: g/dL, mg/dL, /mm³, %…"}

    def clean_symbol(self):
        return self.cleaned_data["symbol"].strip()


class MethodForm(forms.ModelForm):
    class Meta:
        model = Method
        fields = ["name", "description", "is_active"]
        labels = {"is_active": "Activo"}
        help_texts = {"name": "Se imprime bajo el examen: «Colorimétrico enzimático»."}


class OptionSetForm(_LockableCodeForm):
    locked_help = "La usan parámetros: el código queda fijo."

    class Meta:
        model = CodedOptionSet
        fields = ["code", "name", "is_active"]
        labels = {"is_active": "Activa"}
        help_texts = {"code": "Único y sin espacios (p. ej. NEG_POS_CRUCES)."}


class _OptionFormSet(forms.BaseInlineFormSet):
    """Las opciones ya usadas en resultados conservan su texto (se pueden desactivar)."""

    def __init__(self, *args, values_locked: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        if values_locked:
            for form in self.forms:
                if not form.instance._state.adding:
                    form.fields["value"].disabled = True
                    form.fields["value"].widget.attrs["title"] = (
                        "Ya hay resultados con esta lista: el texto queda fijo.")

    def clean(self):
        super().clean()
        seen = set()
        for form in self.forms:
            value = (form.cleaned_data or {}).get("value", "")
            if value and value.strip().upper() in seen:
                form.add_error("value", "Repetido en esta lista.")
            seen.add((value or "").strip().upper())


OptionFormSet = forms.inlineformset_factory(
    CodedOptionSet, CodedOption, formset=_OptionFormSet,
    fields=["value", "order_index", "ordinal", "numeric_equivalent", "is_pathological",
            "is_active"],
    extra=2, can_delete=False,
    labels={"value": "Opción", "order_index": "Orden", "ordinal": "Orden clínico",
            "numeric_equivalent": "Equivalente numérico", "is_pathological": "Patológica",
            "is_active": "Activa"},
)


class GeneralObservationForm(forms.ModelForm):
    """Observación general o de una sección. Las propias de un examen se editan en su
    ficha (Fase 11c)."""

    class Meta:
        model = ObservationTemplate
        fields = ["text", "section", "order_index", "is_active"]
        labels = {"text": "Texto", "section": "Sección", "is_active": "Activa"}
        help_texts = {"text": "Use __ para un hueco que se completa al usarla.",
                      "section": "Vacío = se ofrece en todos los exámenes."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["section"].queryset = Section.objects.filter(is_active=True)
        self.fields["section"].empty_label = "Todas (general)"


class ContainerForm(_LockableCodeForm):
    locked_help = "Ya se usa en exámenes u órdenes: el código queda fijo."

    class Meta:
        model = ContainerType
        fields = ["code", "name", "short_name", "color", "additive", "sample_type",
                  "volume_ml", "draw_order", "max_tests", "is_active"]
        labels = {"is_active": "Activo"}
        widgets = {"color": forms.TextInput(attrs={"type": "color"})}
        help_texts = {"draw_order": "Orden de extracción (CLSI): menor se extrae antes.",
                      "color": "Color del tapón, se usa en pantallas y etiquetas."}

    def clean_short_name(self):
        return self.cleaned_data["short_name"].strip().upper()


class LotForm(forms.ModelForm):
    class Meta:
        model = ReagentLot
        fields = ["reagent", "lot_number", "brand", "isi", "expires_on", "is_current",
                  "is_active"]
        labels = {"is_current": "Vigente (el que se usa ahora)", "is_active": "Activo"}
        widgets = {"expires_on": forms.DateInput(attrs={"type": "date"},
                                                 format="%Y-%m-%d")}
        help_texts = {
            "isi": "Índice de sensibilidad del inserto del reactivo (para el INR).",
            "is_current": "Al marcarlo, el lote vigente anterior deja de serlo.",
        }

    def clean_lot_number(self):
        return self.cleaned_data["lot_number"].strip().upper()

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_current") and not cleaned.get("is_active", True):
            self.add_error("is_current", "Un lote inactivo no puede estar vigente.")
        if (cleaned.get("reagent") == ReagentLot.Reagent.TROMBOPLASTINA
                and cleaned.get("is_current") and cleaned.get("isi") is None):
            self.add_error("isi", "Indique el ISI: sin él no se calcula el INR.")
        return cleaned

    def _get_validation_exclusions(self):
        # «Un solo lote vigente por reactivo» lo resuelve el service, que desmarca el
        # anterior en la misma transacción: aquí no debe impedir marcar uno nuevo.
        return super()._get_validation_exclusions() | {"is_current"}
