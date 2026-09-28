from django import forms


class ImageInput(forms.ClearableFileInput):
    """Subir imagen con vista previa y casilla «Quitar» (logo, firma, sello)."""

    # En apps/core/templates: el renderer de formularios busca en las apps, no en DIRS.
    template_name = "components/image_input.html"

    def __init__(self, attrs=None):
        super().__init__({"accept": "image/png,image/jpeg", **(attrs or {})})
