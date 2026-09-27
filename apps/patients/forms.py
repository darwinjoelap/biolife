"""Registro de paciente desde la recepción (Fase 09)."""
from django import forms
from django.utils import timezone

from apps.masterdata.models import Locality
from apps.patients.models import Guardian, Patient, PatientGuardian


class PatientForm(forms.Form):
    document_type = forms.ChoiceField(label="Tipo", choices=Patient.DocumentType.choices,
                                      initial=Patient.DocumentType.V)
    document_number = forms.CharField(label="N.º de documento", max_length=20,
                                      required=False)
    first_name = forms.CharField(label="Nombres", max_length=100)
    last_name = forms.CharField(label="Apellidos", max_length=100)
    sex = forms.ChoiceField(label="Sexo", choices=Patient.Sex.choices)
    birth_date = forms.DateField(label="Fecha de nacimiento", required=False,
                                 widget=forms.DateInput(attrs={"type": "date"}))
    declared_age_value = forms.IntegerField(label="Edad declarada", required=False,
                                            min_value=0, max_value=150)
    declared_age_unit = forms.ChoiceField(label="Unidad", required=False,
                                          choices=Patient.AgeUnit.choices,
                                          initial=Patient.AgeUnit.ANOS)
    phone = forms.CharField(label="Teléfono", max_length=30, required=False)
    email = forms.EmailField(label="Correo", required=False)
    locality = forms.ModelChoiceField(label="Localidad", required=False,
                                      queryset=Locality.objects.all(), empty_label="—")
    address = forms.CharField(label="Dirección", max_length=255, required=False)

    # Representante (obligatorio si es menor sin documento; lo valida el service).
    g_document_type = forms.ChoiceField(label="Tipo", required=False,
                                        choices=Guardian.DOCUMENT_TYPE_CHOICES)
    g_document_number = forms.CharField(label="N.º de documento", max_length=20,
                                        required=False)
    g_first_name = forms.CharField(label="Nombres", max_length=100, required=False)
    g_last_name = forms.CharField(label="Apellidos", max_length=100, required=False)
    g_phone = forms.CharField(label="Teléfono", max_length=30, required=False)
    g_relationship = forms.ChoiceField(
        label="Parentesco", required=False,
        choices=[("", "—")] + list(PatientGuardian.Relationship.choices),
    )
    g_relationship_detail = forms.CharField(label="Detalle", max_length=100,
                                            required=False)

    GUARDIAN_REQUIRED = ("g_document_number", "g_first_name", "g_last_name",
                         "g_relationship")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("birth_date") and cleaned["birth_date"] > timezone.localdate():
            self.add_error("birth_date", "No puede ser una fecha futura.")
        if not cleaned.get("birth_date") and cleaned.get("declared_age_value") is None:
            self.add_error("birth_date", "Indique la fecha de nacimiento o la edad.")
        if any(cleaned.get(f) for f in self.GUARDIAN_REQUIRED):
            for name in self.GUARDIAN_REQUIRED:
                if not cleaned.get(name):
                    self.add_error(name, "Obligatorio para el representante.")
        return cleaned

    def patient_data(self) -> dict:
        data = self.cleaned_data
        declared = data.get("declared_age_value") is not None and not data.get("birth_date")
        return {
            "document_type": data["document_type"],
            "document_number": data.get("document_number") or None,
            "first_name": data["first_name"].strip(), "last_name": data["last_name"].strip(),
            "sex": data["sex"], "birth_date": data.get("birth_date"),
            "declared_age_value": data["declared_age_value"] if declared else None,
            "declared_age_unit": data.get("declared_age_unit", "") if declared else "",
            "declared_age_at": timezone.localdate() if declared else None,
            "phone": data.get("phone", ""), "email": data.get("email", ""),
            "locality": data.get("locality"), "address": data.get("address", ""),
        }

    def guardian_data(self) -> dict | None:
        data = self.cleaned_data
        if not data.get("g_document_number"):
            return None
        return {
            "document_type": data["g_document_type"],
            "document_number": data["g_document_number"],
            "first_name": data["g_first_name"], "last_name": data["g_last_name"],
            "phone": data.get("g_phone", ""), "relationship": data["g_relationship"],
            "relationship_detail": data.get("g_relationship_detail", ""),
        }
