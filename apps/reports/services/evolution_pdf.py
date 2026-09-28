"""PDF de la evolución de un paciente para el médico (Fase 11e, ADR-032).

Membrete del laboratorio, datos del paciente y, por cada parámetro elegido, el mismo
gráfico que se ve en pantalla (se redibuja con ReportLab desde la geometría de
`core.charts`) y la tabla de valores. Sólo resultados validados. No reemplaza al informe:
no lleva firma ni QR, y lo dice.
"""
from __future__ import annotations

import io
from xml.sax.saxutils import escape

from django.utils import timezone
from reportlab.graphics.shapes import Circle, Drawing, Line, PolyLine, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from apps.patients.services.patient_age import patient_age_text
from apps.reports.services.report_payload import lab_info
from apps.reports.services.report_pdf import (
    INK,
    MARGIN,
    MUTED,
    PAGE_H,
    PAGE_W,
    RULE,
    SOFT,
    ST,
    _brand_icon,
    _fit,
    _hex,
    _image,
    _NumberedCanvas,
)
from apps.results.services.evolution_chart import FLAG_TEXT, build_chart, delta_text
from apps.tenants.services.platform import report_brand

HEADER_H = 46 * mm
FOOTER_H = 16 * mm
BODY_W = PAGE_W - 2 * MARGIN
CHART_H = 44 * mm
FLAG_COLORS = {"ok": colors.HexColor("#1B5FA8"), "hi": colors.HexColor("#c2410c"),
               "lo": colors.HexColor("#2563eb"), "crit": colors.HexColor("#b00020")}
BAND = colors.Color(0.13, 0.59, 0.33, alpha=0.13)
GRID = colors.HexColor("#e5e7eb")


def _flag_color(flag: str):
    key = {"ALTO": "hi", "ANORMAL": "hi", "BAJO": "lo", "CRITICO_ALTO": "crit",
           "CRITICO_BAJO": "crit"}.get(flag, "ok")
    return FLAG_COLORS[key]


def chart_drawing(series: dict, *, width: float = BODY_W, height: float = CHART_H):
    """El gráfico de pantalla en ReportLab (el eje Y de ReportLab crece hacia arriba)."""
    chart = build_chart(series, width=width, height=height)
    drawing = Drawing(width, height)

    def fy(y: float) -> float:
        return height - y

    for x, y, w, h in chart.bands:
        drawing.add(Rect(x, fy(y + h), w, max(h, 0.5), fillColor=BAND, strokeColor=None))
    for y, text in chart.y_ticks:
        drawing.add(Line(chart.left, fy(y), width - chart.right, fy(y), strokeColor=GRID,
                         strokeWidth=0.5))
        drawing.add(String(chart.left - 5, fy(y) - 2.5, text, fontName="Helvetica",
                           fontSize=7, fillColor=MUTED, textAnchor="end"))
    base = fy(height - chart.bottom)
    for x, text in chart.x_ticks:
        drawing.add(String(x, base - 12, text, fontName="Helvetica", fontSize=7,
                           fillColor=MUTED, textAnchor="middle"))
    if chart.unit:
        drawing.add(String(2, fy(chart.top) + 3, chart.unit, fontName="Helvetica",
                           fontSize=7, fillColor=MUTED))
    if len(chart.points) > 1:
        coords = []
        for x, y, _ in chart.points:
            coords += [x, fy(y)]
        drawing.add(PolyLine(coords, strokeColor=FLAG_COLORS["ok"], strokeWidth=1.4))
    for x, y, point in chart.points:
        drawing.add(Circle(x, fy(y), 3, fillColor=_flag_color(point.flag),
                           strokeColor=colors.white, strokeWidth=0.8))
    return drawing


def _values_table(series: dict) -> Table:
    unit = series["parameter"].unit.symbol if series["parameter"].unit_id else ""
    heads = ("Fecha", "Orden", f"Valor {escape(unit)}".strip(), "Marca", "Referencia",
             "Variación")
    rows = [[Paragraph(f"<b>{h}</b>", ST["small"]) for h in heads]]
    for p in reversed(series["points"]):
        flag = FLAG_TEXT.get(p.flag, "")
        rows.append([
            Paragraph(p.when.strftime("%d/%m/%Y"), ST["cell"]),
            Paragraph(escape(p.order_number), ST["cell"]),
            Paragraph(f"<b>{escape(p.text)}</b>", ST["cell"]),
            Paragraph(flag.capitalize() if flag else "—", ST["cell"]),
            Paragraph(escape(p.reference_text or "—"), ST["ref"]),
            Paragraph(delta_text(p.delta_pct) or "—", ST["cell"]),
        ])
    widths = [BODY_W * f for f in (0.12, 0.12, 0.12, 0.11, 0.41, 0.12)]
    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), SOFT),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    return table


def _story(series_list: list[dict], color: str) -> list:
    story: list = []
    for series in series_list:
        parameter = series["parameter"]
        test = "" if parameter.test.name == parameter.name else f"{parameter.test.name} · "
        title = Paragraph(
            f"<font color='{escape(color)}'><b>{escape(parameter.name)}</b></font>"
            f" <font color='#6b7280' size='8'>{escape(test)}"
            f"{len(series['points'])} resultado(s)</font>", ST["test"])
        block = [title, Spacer(1, 1.5 * mm), chart_drawing(series), Spacer(1, 2 * mm),
                 _values_table(series)]
        # Gráfico y tabla juntos si la tabla es corta; si no, la tabla sigue en otra hoja.
        story += ([KeepTogether(block)] if len(series["points"]) <= 12
                  else [KeepTogether(block[:3]), *block[3:]])
        story.append(Spacer(1, 7 * mm))
    story.append(Paragraph(
        "Documento informativo con los resultados <b>validados</b> del paciente en este "
        "laboratorio. La banda sombreada es el rango de referencia usado en cada fecha. No "
        "sustituye a los informes firmados.", ST["small"]))
    return story


class _Decor:
    def __init__(self, lab: dict, patient: dict, brand: dict):
        self.lab, self.patient, self.brand = lab, patient, brand
        self.logo = _image(lab.get("logo", ""))
        self.color = _hex(lab.get("color", ""))

    def __call__(self, canvas, doc):
        canvas.saveState()
        top = PAGE_H - 12 * mm
        x = MARGIN
        if self.logo is not None:
            w, h = _fit(self.logo, 28 * mm, 16 * mm)
            canvas.drawImage(self.logo, MARGIN, top - h, width=w, height=h, mask="auto")
            x += w + 4 * mm
        canvas.setFillColor(INK)
        canvas.setFont("Helvetica-Bold", 12)
        canvas.drawString(x, top - 4.5 * mm,
                          self.lab.get("legal_name") or self.lab.get("name", ""))
        canvas.setFont("Helvetica", 7.8)
        canvas.setFillColor(MUTED)
        y = top - 9 * mm
        for line in (self.lab.get("address", ""), self.lab.get("phone", ""),
                     self.lab.get("email", "")):
            if line:
                canvas.drawString(x, y, line[:95])
                y -= 3.5 * mm
        right = PAGE_W - MARGIN
        canvas.setFillColor(self.color)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawRightString(right, top - 4.5 * mm, "EVOLUCIÓN DE RESULTADOS")
        canvas.setFont("Helvetica", 7.8)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(right, top - 9 * mm, "Generado el "
                               + timezone.localtime().strftime("%d/%m/%Y %I:%M %p"))
        rule_y = PAGE_H - 30 * mm
        canvas.setStrokeColor(self.color)
        canvas.setLineWidth(1.2)
        canvas.line(MARGIN, rule_y, right, rule_y)
        p = self.patient
        canvas.setFillColor(SOFT)
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.roundRect(MARGIN, rule_y - 12 * mm, BODY_W, 9.5 * mm, 1.5 * mm, stroke=1,
                         fill=1)
        cells = [("Paciente", p["name"]), ("C.I.", p["document"] or "—"),
                 ("Edad", p["age"]), ("Sexo", p["sex"]), ("Historia", p["code"])]
        widths = [0.32, 0.15, 0.25, 0.12, 0.16]
        cx, cy = MARGIN + 3 * mm, rule_y - 8.2 * mm
        for (label, value), frac in zip(cells, widths, strict=True):
            canvas.setFont("Helvetica", 6.8)
            canvas.setFillColor(MUTED)
            canvas.drawString(cx, cy + 3.3 * mm, label.upper())
            canvas.setFont("Helvetica-Bold" if label == "Paciente" else "Helvetica", 8.5)
            canvas.setFillColor(INK)
            canvas.drawString(cx, cy, str(value)[:48])
            cx += BODY_W * frac
        # Pie: firma de la plataforma (el número de página lo pone _NumberedCanvas).
        canvas.setStrokeColor(RULE)
        canvas.line(MARGIN, FOOTER_H - 4 * mm, right, FOOTER_H - 4 * mm)
        if self.brand.get("enabled") and self.brand.get("text"):
            bx = MARGIN
            icon = _brand_icon()
            if icon:
                canvas.drawImage(ImageReader(icon), bx, 4.5 * mm, width=5 * mm,
                                 height=5 * mm, mask="auto")
                bx += 6.5 * mm
            canvas.setFont("Helvetica-Bold", 8)
            canvas.setFillColor(colors.HexColor("#1B5FA8"))
            canvas.drawString(bx, 5.8 * mm, self.brand["text"])
        canvas.restoreState()


def patient_facts(patient) -> dict:
    document = (f"{patient.document_type}-{patient.document_number}"
                if patient.document_number else "")
    return {"name": f"{patient.first_name} {patient.last_name}".strip(),
            "document": document, "code": patient.internal_code,
            "sex": patient.get_sex_display(), "age": patient_age_text(patient)}


def render_evolution_pdf(*, patient, series_list: list[dict]) -> bytes:
    buffer = io.BytesIO()
    lab = lab_info()
    facts = patient_facts(patient)
    doc = BaseDocTemplate(
        buffer, pagesize=letter, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=HEADER_H, bottomMargin=FOOTER_H + 2 * mm,
        title=f"Evolución — {facts['name']}",
        author=lab.get("legal_name") or lab.get("name", ""),
        subject="Evolución de resultados de laboratorio")
    frame = Frame(MARGIN, FOOTER_H + 2 * mm, BODY_W, PAGE_H - HEADER_H - FOOTER_H - 2 * mm,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="evolucion", frames=[frame],
                                       onPage=_Decor(lab, facts, report_brand()))])
    doc.build(_story(series_list, lab.get("color") or "#1B5FA8"),
              canvasmaker=_NumberedCanvas)
    return buffer.getvalue()
