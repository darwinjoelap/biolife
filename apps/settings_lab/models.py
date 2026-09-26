from django.db import models


class TenantSettings(models.Model):
    """
    Configuración del laboratorio. Singleton por esquema de tenant: no lleva FK a
    Tenant porque ya vive aislada dentro del esquema (ADR-001). `save()` fuerza
    `pk=1` y `delete()` no hace nada — siempre debe existir exactamente una fila.
    """

    class TimeFormat(models.TextChoices):
        H12 = "H12", "12 horas"
        H24 = "H24", "24 horas"

    class DecimalSeparator(models.TextChoices):
        COMA = "COMA", "Coma"
        PUNTO = "PUNTO", "Punto"

    # Identidad visual
    logo = models.ImageField("Logo", upload_to="branding/", blank=True, null=True)
    banner = models.ImageField("Banner", upload_to="branding/", blank=True, null=True)
    color_primary = models.CharField("Color primario", max_length=7, default="#1B5FA8")
    color_secondary = models.CharField(
        "Color secundario", max_length=7, blank=True, default=""
    )
    report_header_html = models.TextField("Cabecera del informe", blank=True, default="")
    report_footer_text = models.TextField("Pie del informe", blank=True, default="")
    report_disclaimer = models.TextField(
        "Descargo de responsabilidad", blank=True, default=""
    )

    # Contacto (impreso en el informe)
    phone = models.CharField("Teléfono", max_length=30, blank=True, default="")
    address = models.CharField("Dirección", max_length=255, blank=True, default="")
    email = models.EmailField("Correo", blank=True, default="")
    instagram = models.CharField("Instagram", max_length=100, blank=True, default="")
    website = models.URLField("Sitio web", blank=True, default="")

    # Localización
    timezone = models.CharField("Zona horaria", max_length=50, default="America/Caracas")
    time_format = models.CharField(
        "Formato de hora", max_length=3, choices=TimeFormat.choices, default=TimeFormat.H12
    )
    date_format = models.CharField("Formato de fecha", max_length=20, default="dd/MM/yyyy")
    decimal_separator = models.CharField(
        "Separador decimal",
        max_length=5,
        choices=DecimalSeparator.choices,
        default=DecimalSeparator.COMA,
    )

    # Operación
    order_number_prefix = models.CharField(
        "Prefijo de número de orden", max_length=10, blank=True, default=""
    )
    order_number_next = models.PositiveIntegerField("Próximo número de orden", default=1)
    require_second_validation = models.BooleanField(
        "Requiere doble validación", default=False
    )

    class Meta:
        verbose_name = "Configuración del laboratorio"
        verbose_name_plural = "Configuración del laboratorio"

    def __str__(self) -> str:
        return "Configuración del laboratorio"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def get_solo(cls) -> "TenantSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
