"""Consultas de informes (Fase 11)."""
from __future__ import annotations

import datetime

from django.utils import timezone

from apps.reports.models import Report
from apps.settings_lab.models import TenantSettings


def reports_of_order(*, order) -> list[Report]:
    return list(Report.objects.filter(order=order).select_related("created_by")
                .order_by("-version"))


def current_reports(*, order_ids) -> dict:
    """{order_id: Report vigente} para la bandeja."""
    return {r.order_id: r for r in Report.objects.filter(
        order_id__in=list(order_ids), status=Report.Status.VIGENTE)}


def get_report(*, pk, order=None) -> Report:
    reports = Report.objects.select_related("order", "created_by")
    if order is not None:
        reports = reports.filter(order=order)
    return reports.get(pk=pk)


def report_by_code(*, code: str) -> Report:
    return Report.objects.select_related("order").get(verification_code=code)


def current_version_of(report: Report) -> Report | None:
    return Report.objects.filter(order_id=report.order_id,
                                 status=Report.Status.VIGENTE).first()


def link_expires_at(report: Report):
    days = TenantSettings.get_solo().report_link_days
    return report.created_at + datetime.timedelta(days=days)


def can_download_publicly(report: Report) -> bool:
    """El QR descarga el PDF sólo de la versión vigente y dentro del plazo."""
    return report.is_current and timezone.now() <= link_expires_at(report)
