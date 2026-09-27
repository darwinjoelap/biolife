"""Formularios de la captura de resultados (Fase 10)."""
from django import forms

from apps.results.models import CriticalNotification

ORDER_CONDITIONS = [("NINGUNA", "Ninguna"), ("EMBARAZO", "Embarazo")]


class ClinicalDataForm(forms.Form):
    weight_kg = forms.DecimalField(label="Peso (kg)", required=False, max_digits=5,
                                   decimal_places=1, min_value=0)
    height_cm = forms.DecimalField(label="Talla (cm)", required=False, max_digits=5,
                                   decimal_places=1, min_value=0)
    urine_volume_24h_ml = forms.DecimalField(label="Orina 24 h (mL)", required=False,
                                             max_digits=7, decimal_places=1, min_value=0)
    patient_condition = forms.ChoiceField(label="Condición", choices=ORDER_CONDITIONS)


class CriticalNoticeForm(forms.Form):
    value_confirmed = forms.BooleanField(label="Valor confirmado (repetido o verificado)")
    notified_to = forms.CharField(label="Notificado a", max_length=150)
    method = forms.ChoiceField(label="Medio", choices=CriticalNotification.Method.choices)
    notes = forms.CharField(label="Notas", max_length=255, required=False)


def entries_from_post(data) -> dict:
    """{str(parameter_id): valor} desde el POST: `v_<id>` (un valor) y `m_<id>` (varios)."""
    entries = {}
    for key in data:
        if key.startswith("v_"):
            entries[key[2:]] = data.get(key, "")
        elif key.startswith("m_"):
            entries[key[2:]] = [v for v in data.getlist(key) if v]
    for key in data.getlist("m_present"):  # multi sin nada marcado = vaciar
        entries.setdefault(key, [])
    return entries


def notes_from_post(data) -> dict:
    """{str(result_id): {"observations", "internal_note"}} desde `obs_<id>` y `nota_<id>`."""
    notes: dict = {}
    for key in data:
        for prefix, field_name in (("obs_", "observations"), ("nota_", "internal_note")):
            if key.startswith(prefix):
                notes.setdefault(key[len(prefix):], {})[field_name] = data.get(key, "")
    return notes
