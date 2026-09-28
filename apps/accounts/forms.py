from django import forms

from apps.accounts.models import Role, User
from apps.core.widgets import ImageInput


def _role_choices():
    return [(r.code, r.name) for r in Role.objects.order_by("id")]


class LabUserForm(forms.Form):
    username = forms.CharField(label="Usuario (para entrar)", max_length=150)
    first_name = forms.CharField(label="Nombres", max_length=150)
    last_name = forms.CharField(label="Apellidos", max_length=150)
    email = forms.EmailField(label="Correo", required=False)
    phone = forms.CharField(label="Teléfono", max_length=30, required=False)
    professional_title = forms.CharField(label="Título profesional", max_length=60,
                                         required=False,
                                         help_text="P. ej. «Lcda. en Bioanálisis».")
    professional_license = forms.CharField(label="Nº de colegiatura / MPPS", max_length=40,
                                           required=False)
    roles = forms.MultipleChoiceField(label="Roles", widget=forms.CheckboxSelectMultiple,
                                      choices=())
    password = forms.CharField(
        label="Clave temporal", required=False, widget=forms.TextInput(
            attrs={"autocomplete": "off"}),
        help_text="Déjela vacía para generarla. El usuario la cambia al entrar.")

    def __init__(self, *args, editing: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["roles"].choices = _role_choices()
        if editing:
            self.fields["username"].disabled = True
            del self.fields["password"]


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "professional_title",
                  "professional_license", "signature_image", "stamp_image"]
        labels = {"first_name": "Nombres", "last_name": "Apellidos", "email": "Correo",
                  "professional_license": "Nº de colegiatura / MPPS"}
        widgets = {
            "signature_image": ImageInput(),
            "stamp_image": ImageInput(),
        }


class PasswordChangeForm(forms.Form):
    current = forms.CharField(label="Clave actual", widget=forms.PasswordInput(
        attrs={"autocomplete": "current-password"}))
    new = forms.CharField(label="Clave nueva", widget=forms.PasswordInput(
        attrs={"autocomplete": "new-password"}),
        help_text="Mínimo 8 caracteres; no sólo números ni una clave común.")
    repeat = forms.CharField(label="Repita la clave nueva", widget=forms.PasswordInput(
        attrs={"autocomplete": "new-password"}))

    def clean(self):
        data = super().clean()
        if data.get("new") and data.get("new") != data.get("repeat"):
            self.add_error("repeat", "Las claves no coinciden.")
        return data
