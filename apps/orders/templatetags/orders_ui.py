"""Etiquetas visuales de órdenes y muestras."""
from django import template

register = template.Library()

STATUS_TAGS = {
    "REGISTRADA": "", "MUESTRA_TOMADA": "tag--info", "EN_PROCESO": "tag--brand",
    "RESULTADOS_CARGADOS": "tag--warn", "VALIDADA": "tag--ok", "ENTREGADA": "tag--ok",
    "ANULADA": "tag--danger",
    "PENDIENTE": "tag--warn", "TOMADA": "tag--ok", "RECHAZADA": "tag--danger",
}


@register.filter
def status_tag(status: str) -> str:
    """Clase del `.tag` según el estado de una orden o muestra."""
    return STATUS_TAGS.get(status, "")
