import uuid

from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Creado el", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado el", auto_now=True)

    class Meta:
        abstract = True


class TenantBaseModel(TimeStampedModel):
    """Base de todo modelo que vive dentro del esquema de un laboratorio."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Referencia por string: apps.core no importa apps.accounts (CLAUDE.md, regla 3).
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Creado por",
    )
    is_active = models.BooleanField("Activo", default=True)

    class Meta:
        abstract = True
