from django.db import models


class Locality(models.Model):
    name = models.CharField("Nombre", max_length=120)
    state = models.CharField("Estado", max_length=80)
    municipality = models.CharField("Municipio", max_length=120, blank=True, default="")

    class Meta:
        verbose_name = "Localidad"
        verbose_name_plural = "Localidades"
        unique_together = [("name", "state")]
        ordering = ["state", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.state})"
