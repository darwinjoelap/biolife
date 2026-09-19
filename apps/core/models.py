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
    is_active = models.BooleanField("Activo", default=True)

    class Meta:
        abstract = True

    # created_by se agrega en FASE 02, cuando exista el modelo de usuario.
