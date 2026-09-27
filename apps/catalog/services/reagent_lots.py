"""Lotes de reactivos (Fase 10, ADR-025): el lote vigente aporta datos de cálculo, hoy el
ISI de la tromboplastina para el INR."""
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import ReagentLot


@dataclass(frozen=True)
class LotInfo:
    lot_number: str
    isi: Decimal | None
    expired: bool


@transaction.atomic
def set_current_lot(*, lot: ReagentLot) -> ReagentLot:
    """Deja `lot` como el único vigente de su reactivo."""
    ReagentLot.objects.filter(reagent=lot.reagent, is_current=True).exclude(pk=lot.pk).update(
        is_current=False
    )
    lot.is_current = True
    lot.save(update_fields=["is_current", "updated_at"])
    return lot


def current_lot(*, reagent: str) -> LotInfo | None:
    lot = ReagentLot.objects.filter(reagent=reagent, is_current=True, is_active=True).first()
    if lot is None:
        return None
    expired = bool(lot.expires_on and lot.expires_on < timezone.localdate())
    return LotInfo(lot_number=lot.lot_number, isi=lot.isi, expired=expired)


def current_isi() -> LotInfo | None:
    return current_lot(reagent=ReagentLot.Reagent.TROMBOPLASTINA)
