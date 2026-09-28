"""Informes de resultados (Fase 11, ADR-027).

Un `Report` es una **versión emitida** del informe de una orden. Guarda el contenido
congelado (`payload`: laboratorio, paciente, exámenes validados, firmantes) y su huella
SHA-256; el PDF se genera siempre desde ese contenido, así el mismo informe se ve igual
hoy y dentro de un año aunque cambie el catálogo o los rangos.

- Parcial: faltan exámenes por validar (el PDF lo dice en la cabecera y en marca de agua).
- Al emitir de nuevo con contenido distinto se crea la versión siguiente y la anterior
  queda *Reemplazada* (se conserva; nunca se borra).
- `verification_code` es el token del QR: abre la página pública de verificación, que
  confirma la autenticidad sin mostrar valores clínicos y permite descargar el PDF de la
  versión vigente mientras no venza el plazo del laboratorio.
"""
from django.db import models

from apps.core.models import TenantBaseModel


class Report(TenantBaseModel):
    class Kind(models.TextChoices):
        PARCIAL = "PARCIAL", "Parcial"
        FINAL = "FINAL", "Final"

    class Status(models.TextChoices):
        VIGENTE = "VIGENTE", "Vigente"
        REEMPLAZADO = "REEMPLAZADO", "Reemplazado"

    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT,
                              related_name="reports", verbose_name="Orden")
    version = models.PositiveSmallIntegerField("Versión")
    kind = models.CharField("Tipo", max_length=8, choices=Kind.choices)
    status = models.CharField("Estado", max_length=12, choices=Status.choices,
                              default=Status.VIGENTE)
    payload = models.JSONField("Contenido congelado")
    content_hash = models.CharField("Huella SHA-256", max_length=64)
    previous_hash = models.CharField("Huella de la versión anterior", max_length=64,
                                     blank=True, default="")
    verification_code = models.CharField("Código de verificación", max_length=40,
                                         unique=True, editable=False)
    replaced_at = models.DateTimeField("Reemplazado el", null=True, blank=True)

    class Meta:
        verbose_name = "Informe"
        verbose_name_plural = "Informes"
        ordering = ["order", "-version"]
        constraints = [
            models.UniqueConstraint(fields=["order", "version"],
                                    name="report_unique_version"),
            models.UniqueConstraint(fields=["order"], condition=models.Q(status="VIGENTE"),
                                    name="report_one_current_per_order"),
        ]

    def __str__(self) -> str:
        return f"Informe {self.payload.get('order', {}).get('number', '')} v{self.version}"

    @property
    def is_current(self) -> bool:
        return self.status == self.Status.VIGENTE

    @property
    def is_partial(self) -> bool:
        return self.kind == self.Kind.PARCIAL

    @property
    def short_hash(self) -> str:
        return self.content_hash[:16]
