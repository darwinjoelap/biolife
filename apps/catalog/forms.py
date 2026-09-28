"""Formularios de las pantallas del catálogo (Fase 11c). Los rangos reutilizan los de la
Fase 08b (`admin_forms`): edad en años/meses/días, validación de solapes y huecos."""
from django import forms

from apps.catalog.admin_forms import ReferenceRangeForm, ReferenceRangeInlineFormSet
from apps.catalog.models import (
    CodedOption,
    ObservationTemplate,
    Parameter,
    ParameterGroup,
    Profile,
    ReferenceRange,
    SampleRequirement,
    Test,
)
from apps.catalog.services.formula_engine import FormulaSyntaxError
from apps.catalog.services.formula_validation import validate_formula


class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = ["code", "name", "section", "method", "sample_type", "process_hours",
                  "requires_fasting", "requires_anthropometry", "is_active"]
        labels = {"method": "Método", "section": "Sección",
                  "is_active": "Activo (se puede ordenar)"}
        help_texts = {
            "code": "Único y sin espacios (p. ej. HEM_COMP). No cambia una vez ordenado.",
            "process_hours": "Tiempo habitual de entrega, en horas.",
            "requires_anthropometry": "Pide peso, talla y orina de 24 h (depuración).",
        }

    def __init__(self, *args, code_locked: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        if code_locked:
            self.fields["code"].disabled = True
            self.fields["code"].help_text = "Ya se ordenó: el código queda fijo."

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper().replace(" ", "_")


SampleRequirementFormSet = forms.inlineformset_factory(
    Test, SampleRequirement, fields=["container_type", "collection_label", "own_container",
                                     "order_index"],
    extra=1, can_delete=True,
    labels={"container_type": "Tubo", "collection_label": "Toma (opcional)",
            "own_container": "Tubo propio", "order_index": "Orden"},
)

ParameterGroupFormSet = forms.inlineformset_factory(
    Test, ParameterGroup, fields=["name", "order_index"], extra=1, can_delete=True,
    labels={"name": "Grupo (subtítulo)", "order_index": "Orden"},
)

ObservationFormSet = forms.inlineformset_factory(
    Test, ObservationTemplate, fields=["text", "order_index", "is_active"], extra=1,
    can_delete=False, labels={"text": "Texto", "order_index": "Orden", "is_active": "Activa"},
)


class ParameterForm(forms.ModelForm):
    """Datos del parámetro. La fórmula se valida (sintaxis, referencias, ciclos) antes de
    guardar; `depends_on` se deriva de ella al guardar."""

    class Meta:
        model = Parameter
        fields = ["code", "name", "group", "value_type", "unit", "decimals", "order_index",
                  "option_set", "formula", "is_printable", "is_optional", "instrument_code",
                  "is_active"]
        labels = {"group": "Grupo", "unit": "Unidad", "option_set": "Lista de opciones",
                  "is_active": "Activo"}
        widgets = {"formula": forms.Textarea(attrs={"rows": 2, "class": "mono"})}
        help_texts = {
            "formula": "Sólo para «Numérico calculado». Use {CODIGO} de otros parámetros y "
                       "{@peso}, {@talla}, {@volumen_orina_24h}, {@isi}.",
            "option_set": "Para codificados, cualitativos, semicuantitativos, títulos y "
                          "multi-selección.",
            "instrument_code": "Código con que lo envía el analizador (Fase 16).",
        }

    def __init__(self, *args, test: Test, locked: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["group"].queryset = ParameterGroup.objects.filter(test=test)
        self.fields["group"].label_from_instance = lambda group: group.name
        if locked:
            for name in ("code", "value_type"):
                self.fields[name].disabled = True
            self.fields["code"].help_text = "Ya tiene resultados: código y tipo quedan fijos."

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper().replace(" ", "_")

    def clean(self):
        cleaned = super().clean()
        value_type = cleaned.get("value_type")
        if value_type == Parameter.ValueType.NUMERIC_CALCULATED:
            try:
                cleaned["formula"] = validate_formula(
                    code=cleaned.get("code", ""), formula=cleaned.get("formula", "")).source
            except FormulaSyntaxError as exc:
                self.add_error("formula", exc.message)
        else:
            cleaned["formula"] = ""
        if value_type in ("CODED", "SEMIQUANTITATIVE", "QUALITATIVE", "TITER",
                          "MULTI_CATALOG") and not cleaned.get("option_set"):
            self.add_error("option_set", "Obligatorio para este tipo de valor.")
        return cleaned


class RangeForm(ReferenceRangeForm):
    """Rango en la ficha del parámetro: la opción esperada sólo puede ser de la lista de
    opciones del parámetro."""

    def __init__(self, *args, parameter: Parameter | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = CodedOption.objects.none()
        if parameter is not None and parameter.option_set_id:
            queryset = CodedOption.objects.filter(option_set_id=parameter.option_set_id)
        self.fields["expected_option"].queryset = queryset
        self.fields["unit"].label = "Unidad"
        for prefix in ("desde", "hasta"):
            for part, hint in (("anos", "años"), ("meses", "meses"), ("dias", "días")):
                self.fields[f"{prefix}_{part}"].widget.attrs.update(
                    placeholder=hint, title=hint, style="")
        self.fields["expected_option"].label = "Resultado esperado"
        self.fields["bands"].widget = forms.Textarea(attrs={"rows": 2, "class": "mono"})
        self.fields["bands"].help_text = ('Sólo interpretativo. Ej.: [{"max": 2.5, '
                                          '"label": "NORMAL"}, {"min": 2.5, "label": "..."}]')


def range_formset(parameter: Parameter, data=None):
    formset_class = forms.inlineformset_factory(
        Parameter, ReferenceRange, form=RangeForm, formset=ReferenceRangeInlineFormSet,
        fields=RangeForm.Meta.fields, extra=1, can_delete=False)
    return formset_class(data, instance=parameter, form_kwargs={"parameter": parameter},
                   queryset=ReferenceRange.objects.filter(parameter=parameter)
                   .order_by("-is_active", "condition", "sex", "age_min_days"))


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["code", "name", "description", "order_index", "is_active"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}
        labels = {"is_active": "Activo (se puede ordenar)"}

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper().replace(" ", "_")
