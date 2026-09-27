"""Etiquetas de tubo en PDF (ADR-024).

Una página por etiqueta, del tamaño exacto configurado en el laboratorio (50 × 25 mm por
defecto), para impresoras térmicas de cualquier marca: el navegador imprime el PDF y el
controlador de la impresora hace el resto. Monocromo: el color del tubo va como texto
invertido (fondo negro), que es lo que se lee en papel térmico.

Contenido: paciente, documento, edad/sexo, tubo y toma, código de barras Code 128 con el
número de la muestra (12 dígitos), número legible, exámenes y fecha/hora.
"""
from __future__ import annotations

import io
from collections.abc import Sequence

from django.db import transaction
from django.utils import timezone
from reportlab.graphics.barcode import code128
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from apps.core.utils.dates import format_time_12h
from apps.orders.models import LabelPrint, Order, Sample
from apps.patients.services.patient_age import patient_age_short

FONT = "Helvetica"
BOLD = "Helvetica-Bold"
PAD = 1.5 * mm


def _fit(text: str, font: str, size: float, width: float) -> str:
    """Recorta `text` con '…' para que quepa en `width`."""
    if stringWidth(text, font, size) <= width:
        return text
    while text and stringWidth(text + "…", font, size) > width:
        text = text[:-1]
    return text + "…"


def _patient_lines(order: Order) -> tuple[str, str]:
    patient = order.patient
    name = f"{patient.last_name}, {patient.first_name}".upper()
    document = (f"{patient.document_type}-{patient.document_number}"
                if patient.document_number else patient.internal_code)
    return name, f"{document}  {patient_age_short(patient)} {patient.sex}"


def _draw_barcode(pdf, value: str, *, x: float, y: float, width: float, height: float):
    # 12 dígitos en Code 128 (juego C) ≈ 101 módulos + 20 de zona muda (10 por lado, que
    # el lector necesita): en 47 mm, ~0,38 mm por módulo.
    modules = code128.Code128(value, barWidth=1, quiet=True).width
    bar_width = min(width / modules, 0.5 * mm)
    barcode = code128.Code128(value, barHeight=height, barWidth=bar_width,
                              humanReadable=False, quiet=True)
    barcode.drawOn(pdf, x + (width - barcode.width) / 2, y)


def _draw_sample(pdf, sample: Sample, *, width: float, height: float, when: str) -> None:
    order = sample.order
    name, id_line = _patient_lines(order)
    inner = width - 2 * PAD
    top = height - PAD

    # Fila 1: paciente | tubo (texto invertido)
    tube = sample.container_type.short_name.upper()
    tube_w = stringWidth(tube, BOLD, 6.5) + 2 * mm
    pdf.setFillColorRGB(0, 0, 0)
    pdf.rect(width - PAD - tube_w, top - 3.2 * mm, tube_w, 3.2 * mm, stroke=0, fill=1)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont(BOLD, 6.5)
    pdf.drawCentredString(width - PAD - tube_w / 2, top - 2.4 * mm, tube)
    pdf.setFillColorRGB(0, 0, 0)
    pdf.setFont(BOLD, 7)
    pdf.drawString(PAD, top - 2.5 * mm, _fit(name, BOLD, 7, inner - tube_w - 1 * mm))

    # Fila 2: documento, edad y sexo | fecha
    pdf.setFont(FONT, 6)
    pdf.drawString(PAD, top - 5.4 * mm, id_line)
    pdf.drawRightString(width - PAD, top - 5.4 * mm, when)

    # Código de barras
    bar_h = height * 0.34
    bar_y = top - 6.4 * mm - bar_h
    _draw_barcode(pdf, sample.barcode, x=PAD, y=bar_y, width=inner, height=bar_h)

    # Número legible + toma
    pdf.setFont(BOLD, 7)
    label = sample.number + (f"  {sample.collection_label}" if sample.collection_label
                             else "")
    pdf.drawString(PAD, bar_y - 2.8 * mm, _fit(label, BOLD, 7, inner))

    # Exámenes
    codes = ", ".join(item.test.code for item in sample.order_items.all())
    urgent = "URG · " if order.priority == Order.Priority.URGENTE else ""
    pdf.setFont(FONT, 5.5)
    pdf.drawString(PAD, PAD, _fit(urgent + codes, FONT, 5.5, inner))


def _draw_order(pdf, order: Order, *, width: float, height: float, when: str,
                samples: int) -> None:
    name, id_line = _patient_lines(order)
    inner = width - 2 * PAD
    top = height - PAD
    pdf.setFont(BOLD, 7)
    pdf.drawString(PAD, top - 2.5 * mm, _fit(name, BOLD, 7, inner))
    pdf.setFont(FONT, 6)
    pdf.drawString(PAD, top - 5.4 * mm, id_line)
    pdf.drawRightString(width - PAD, top - 5.4 * mm, when)
    bar_h = height * 0.34
    bar_y = top - 6.4 * mm - bar_h
    _draw_barcode(pdf, order.barcode, x=PAD, y=bar_y, width=inner, height=bar_h)
    pdf.setFont(BOLD, 7)
    pdf.drawString(PAD, bar_y - 2.8 * mm, f"ORDEN {order.number}")
    pdf.setFont(FONT, 5.5)
    pdf.drawString(PAD, PAD, f"{samples} muestra(s)")


def render_labels_pdf(*, order: Order, samples: Sequence[Sample], width_mm: int,
                      height_mm: int, include_order_label: bool = False) -> bytes:
    """PDF con una página por etiqueta. No registra nada (ver `print_labels`)."""
    width, height = width_mm * mm, height_mm * mm
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(width, height))
    pdf.setTitle(f"Etiquetas {order.number}")
    ordered = timezone.localtime(order.ordered_at)
    when = f"{ordered:%d/%m/%y} {format_time_12h(order.ordered_at).replace('.', '')}"
    if include_order_label:
        _draw_order(pdf, order, width=width, height=height, when=when,
                    samples=len(samples))
        pdf.showPage()
    for sample in samples:
        _draw_sample(pdf, sample, width=width, height=height, when=when)
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def print_labels(*, order: Order, samples: Sequence[Sample], user, width_mm: int,
                 height_mm: int, include_order_label: bool = False) -> bytes:
    """Genera el PDF y registra quién imprimió cada etiqueta (y si es reimpresión)."""
    pdf = render_labels_pdf(order=order, samples=samples, width_mm=width_mm,
                            height_mm=height_mm, include_order_label=include_order_label)
    with transaction.atomic():
        for sample in samples:
            LabelPrint.objects.create(sample=sample, created_by=user,
                                      is_reprint=sample.prints.exists())
    return pdf
