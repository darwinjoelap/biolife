"""Formularios de pacientes: registro desde la recepción (Fase 09) y ficha (Fase 11e)."""
from django import forms
from django.utils import timezone

from apps.masterdata.models import Locality
from apps.patients.models import Antecedent, Guardian, Patient, PatientGuardian


class PatientDataForm(forms.Form):
    """Datos del paciente (sin representante): alta y edición."""

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

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("birth_date") and cleaned["birth_date"] > timezone.localdate():
            self.add_error("birth_date", "No puede ser una fecha futura.")
        if not cleaned.get("birth_date") and cleaned.get("declared_age_value") is None:
            self.add_error("birth_date", "Indique la fecha de nacimiento o la edad.")
        return cleaned

    def patient_data(self, *, current: Patient | None = None) -> dict:
        """Datos listos para el service. Al editar, una edad declarada que no cambió
        conserva la fecha en que se declaró (si no, el paciente «rejuvenecería»)."""
        data = self.cleaned_data
        declared = data.get("declared_age_value") is not None and not data.get("birth_date")
        declared_at = timezone.localdate() if declared else None
        if (declared and current is not None and current.birth_date is None
                and current.declared_age_value == data["declared_age_value"]
                and current.declared_age_unit == data.get("declared_age_unit")):
            declared_at = current.declared_age_at
        return {
            "document_type": data["document_type"],
            "document_number": data.get("document_number") or None,
            "first_name": data["first_name"].strip(), "last_name": data["last_name"].strip(),
            "sex": data["sex"], "birth_date": data.get("birth_date"),
            "declared_age_value": data["declared_age_value"] if declared else None,
            "declared_age_unit": data.get("declared_age_unit", "") if declared else "",
            "declared_age_at": declared_at,
            "phone": data.get("phone", ""), "email": data.get("email", ""),
            "locality": data.get("locality"), "address": data.get("address", ""),
        }

    @classmethod
    def initial_for(cls, patient: Patient) -> dict:
        return {
            "document_type": patient.document_type,
            "document_number": patient.document_number or "",
            "first_name": patient.first_name, "last_name": patient.last_name,
            "sex": patient.sex, "birth_date": patient.birth_date,
            "declared_age_value": patient.declared_age_value,
            "declared_age_unit": patient.declared_age_unit or Patient.AgeUnit.ANOS,
            "phone": patient.phone, "email": patient.email,
            "locality": patient.locality_id, "address": patient.address,
        }


class PatientForm(PatientDataForm):
    """Alta desde la recepción: datos del paciente y, si hace falta, su representante."""

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
        if any(cleaned.get(f) for f in self.GUARDIAN_REQUIRED):
            for name in self.GUARDIAN_REQUIRED:
                if not cleaned.get(name):
                    self.add_error(name, "Obligatorio para el representante.")
        return cleaned

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


class GuardianForm(forms.Form):
    """Representante agregado desde la ficha del paciente."""

    document_type = forms.ChoiceField(label="Tipo", choices=Guardian.DOCUMENT_TYPE_CHOICES)
    document_number = forms.CharField(label="N.º de documento", max_length=20)
    first_name = forms.CharField(label="Nombres", max_length=100)
    last_name = forms.CharField(label="Apellidos", max_length=100)
    phone = forms.CharField(label="Teléfono", max_length=30, required=False)
    relationship = forms.ChoiceField(label="Parentesco",
                                     choices=PatientGuardian.Relationship.choices)
    relationship_detail = forms.CharField(label="Detalle", max_length=100, required=False)
    is_primary = forms.BooleanField(label="Representante principal", required=False)

    def clean(self):
        cleaned = super().clean()
        if (cleaned.get("relationship") == PatientGuardian.Relationship.OTRO
                and not cleaned.get("relationship_detail")):
            self.add_error("relationship_detail", "Indique el parentesco.")
        if cleaned.get("document_number"):
            cleaned["document_number"] = cleaned["document_number"].strip()
        return cleaned


class AntecedentForm(forms.Form):
    antecedent = forms.ModelChoiceField(label="Antecedente", queryset=Antecedent.objects.none(),
                                        empty_label="Elija…")
    notes = forms.CharField(label="Nota", max_length=200, required=False,
                            widget=forms.TextInput(attrs={
                                "placeholder": "Nota opcional: tipo 2, warfarina 5 mg…"}))

    def __init__(self, *args, options=None, **kwargs):
        super().__init__(*args, **kwargs)
        if options is not None:
            self.fields["antecedent"].queryset = options


class AntecedentConfigForm(forms.ModelForm):
    """Antecedente en Tablas auxiliares (lo configura el laboratorio)."""

    class Meta:
        model = Antecedent
        fields = ["code", "name", "description", "suggested_parameters", "order_index",
                  "is_active"]
        labels = {"is_active": "Activo"}
        widgets = {"suggested_parameters": forms.SelectMultiple(attrs={"size": 12})}
        help_texts = {
            "suggested_parameters": "Se destacan en la ficha y en la evolución del paciente. "
                                    "Ctrl+clic para varios.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields["suggested_parameters"]
        field.required = False
        field.queryset = (field.queryset.filter(
            is_active=True, value_type__in=("NUMERIC", "NUMERIC_CALCULATED"))
            .select_related("test").order_by("test__name", "order_index"))
        field.label_from_instance = lambda p: f"{p.test.name} · {p.name}"
        if not self.instance._state.adding and self.instance.patients.exists():
            self.fields["code"].disabled = True
            self.fields["code"].help_text = "Ya hay pacientes con este antecedente."

    def clean_code(self):
        return self.cleaned_data["code"].strip().upper().replace(" ", "_")
