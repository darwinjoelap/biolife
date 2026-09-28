from django import forms
from django.utils import timezone

from apps.billing.models import Currency


class RateForm(forms.Form):
    currency = forms.ModelChoiceField(label="Moneda", queryset=Currency.objects.none())
    rate = forms.DecimalField(label="Tasa", max_digits=20, decimal_places=8, min_value=0,
                              help_text="Cuántas unidades de esa moneda vale 1 de la base.")
    effective_date = forms.DateField(label="Vigente desde", widget=forms.DateInput(
        attrs={"type": "date"}, format="%Y-%m-%d"))

    def __init__(self, *args, base=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Currency.objects.filter(is_active=True)
        if base is not None:
            queryset = queryset.exclude(pk=base.pk)
        self.fields["currency"].queryset = queryset
        if queryset.count() == 1:
            self.fields["currency"].initial = queryset.first()
            self.fields["currency"].empty_label = None
        self.fields["effective_date"].initial = timezone.localdate()


class AdjustForm(forms.Form):
    percent = forms.DecimalField(label="Ajuste (%)", max_digits=6, decimal_places=2,
                                 help_text="Positivo sube, negativo baja (p. ej. 10 o -5).")
    round_to = forms.DecimalField(label="Redondear a", max_digits=10, decimal_places=2,
                                  required=False, min_value=0,
                                  help_text="Opcional: 0,50 · 1 · 5 · 100…")
    include_profiles = forms.BooleanField(label="Incluir perfiles con precio fijo",
                                          required=False, initial=True)


class CopyListForm(forms.Form):
    code = forms.CharField(label="Código de la nueva lista", max_length=30)
    name = forms.CharField(label="Nombre", max_length=100)
    currency = forms.ModelChoiceField(label="Moneda", queryset=Currency.objects.filter(
        is_active=True), required=False, help_text="Vacío = la misma moneda.")
    percent = forms.DecimalField(label="Ajuste (%)", max_digits=6, decimal_places=2,
                                 required=False, initial=0)
    round_to = forms.DecimalField(label="Redondear a", max_digits=10, decimal_places=2,
                                  required=False, min_value=0)

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper().replace(" ", "_")
