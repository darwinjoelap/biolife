"""Pantallas de informes (Fase 11): bandeja, informe de una orden, PDF y verificación
pública por QR. Las vistas sólo orquestan: services/selectors."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts.permissions import RECEPTION_ROLES, VIEW_ROLES, role_required
from apps.core.exceptions import ApplicationError
from apps.orders.models import Order
from apps.orders.selectors.order_queries import (
    REPORT_TABS,
    get_order,
    orders_for_reports,
    report_order_facts,
    report_tab_counts,
)
from apps.orders.services.order_management import mark_delivered
from apps.reports.models import Report
from apps.reports.selectors import report_queries as q
from apps.reports.services.report_emission import emit_report, is_outdated
from apps.reports.services.report_pdf import render_report_pdf


def _order(pk) -> Order:
    try:
        return get_order(pk=pk)
    except (Order.DoesNotExist, ValidationError) as exc:
        raise Http404("Orden no encontrada.") from exc


def _verify_url(request, report: Report) -> str:
    return request.build_absolute_uri(reverse("verify:page", args=[report.verification_code]))


def _pdf_response(request, report: Report, *, download: bool = False) -> HttpResponse:
    pdf = render_report_pdf(report, verify_url=_verify_url(request, report))
    name = f"informe-{report.payload['order']['number']}-v{report.version}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    disposition = "attachment" if download else "inline"
    response["Content-Disposition"] = f'{disposition}; filename="{name}"'
    response["Cache-Control"] = "no-store"
    return response


@role_required(*VIEW_ROLES)
def worklist(request):
    tab = request.GET.get("tab", "listas")
    tab = tab if tab in REPORT_TABS else "listas"
    orders = list(orders_for_reports(tab=tab, query=request.GET.get("q", "")))
    current = q.current_reports(order_ids=[o.pk for o in orders])
    return render(request, "reports/worklist.html", {
        "rows": [(o, current.get(o.pk)) for o in orders], "tab": tab,
        "counts": report_tab_counts(), "query": request.GET.get("q", ""),
    })


@role_required(*VIEW_ROLES)
def order_reports(request, pk):
    order = _order(pk)
    reports = q.reports_of_order(order=order)
    current = next((r for r in reports if r.is_current), None)
    facts = report_order_facts(order=order)
    return render(request, "reports/order_reports.html", {
        "order": order, "reports": reports, "current": current,
        "outdated": not order.is_cancelled and is_outdated(current, order),
        "pending_tests": facts["pending_tests"],
        "verify_url": _verify_url(request, current) if current else "",
        "expires_at": q.link_expires_at(current) if current else None,
    })


@role_required(*RECEPTION_ROLES)
@require_POST
def emit(request, pk):
    order = _order(pk)
    try:
        report, created = emit_report(order=order, user=request.user)
    except ApplicationError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, f"Informe versión {report.version} emitido."
                         if created else "El informe vigente ya está al día.")
    return redirect("reports:order", pk=order.pk)


@role_required(*RECEPTION_ROLES)
@require_POST
def deliver(request, pk):
    order = _order(pk)
    try:
        emit_report(order=order, user=request.user)  # lo entregado es lo último validado
        mark_delivered(order=order, user=request.user)
    except ApplicationError as exc:
        messages.error(request, exc.message)
    else:
        messages.success(request, f"Orden {order.number} marcada como entregada.")
    return redirect("reports:order", pk=order.pk)


@role_required(*VIEW_ROLES)
def report_pdf(request, pk, report_pk):
    try:
        report = q.get_report(pk=report_pk, order=_order(pk))
    except (Report.DoesNotExist, ValidationError) as exc:
        raise Http404("Informe no encontrado.") from exc
    return _pdf_response(request, report, download=request.GET.get("descargar") == "1")


# Público (sin sesión): lo que abre el QR -------------------------------------------------
def _by_code(code: str) -> Report:
    try:
        return q.report_by_code(code=code)
    except Report.DoesNotExist as exc:
        raise Http404("Código de verificación no encontrado.") from exc


def verify(request, code):
    report = _by_code(code)
    return render(request, "reports/verify.html", {
        "report": report, "payload": report.payload,
        "current": q.current_version_of(report),
        "can_download": q.can_download_publicly(report),
        "expires_at": q.link_expires_at(report),
    })


def verify_pdf(request, code):
    report = _by_code(code)
    if not q.can_download_publicly(report):
        raise Http404("El enlace de descarga venció o el informe fue reemplazado.")
    return _pdf_response(request, report, download=True)
