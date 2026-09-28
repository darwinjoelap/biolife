"""Emisión de informes (Fase 11, ADR-027).

- Sólo entran exámenes validados; sin ninguno validado no hay informe.
- Si el contenido es igual al de la versión vigente, se devuelve esa (no se duplica).
- Si cambió (se validó otro examen, cambió la firma o los datos del laboratorio), se crea
  la versión siguiente, encadenada a la anterior por su huella, y la anterior queda
  *Reemplazada*.
"""
from __future__ import annotations

import secrets

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import ApplicationError
from apps.reports.models import Report
from apps.reports.services.report_payload import build_payload, content_hash


def _new_code() -> str:
    while True:
        code = secrets.token_urlsafe(16)
        if not Report.objects.filter(verification_code=code).exists():
            return code


@transaction.atomic
def emit_report(*, order, user=None) -> tuple[Report, bool]:
    """(informe vigente, creado). Bloquea la orden para que dos emisiones simultáneas no
    choquen en el número de versión."""
    if order.is_cancelled:
        raise ApplicationError(f"La orden {order.number} está anulada.")
    type(order).objects.select_for_update().filter(pk=order.pk).first()
    payload = build_payload(order)
    if not payload["test_count"]:
        raise ApplicationError("La orden no tiene exámenes validados para el informe.")
    digest = content_hash(payload)

    current = Report.objects.filter(order=order, status=Report.Status.VIGENTE).first()
    if current is not None and current.content_hash == digest:
        return current, False
    last_version = (Report.objects.filter(order=order).order_by("-version")
                    .values_list("version", flat=True).first() or 0)
    if current is not None:
        current.status = Report.Status.REEMPLAZADO
        current.replaced_at = timezone.now()
        current.save(update_fields=["status", "replaced_at", "updated_at"])
    report = Report.objects.create(
        order=order, version=last_version + 1, kind=payload["kind"], payload=payload,
        content_hash=digest, previous_hash=current.content_hash if current else "",
        verification_code=_new_code(), created_by=user,
    )
    return report, True


def is_outdated(report: Report | None, order) -> bool:
    """True si lo validado hoy difiere del informe vigente (hay que emitir de nuevo)."""
    if report is None:
        return True
    return content_hash(build_payload(order)) != report.content_hash
