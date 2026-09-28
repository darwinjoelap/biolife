"""Precios y tasa de cambio sin /admin (Fase 11c): tabla editable por lista (se guarda al
salir de cada campo), ajuste masivo, copia de listas y registro de la tasa."""
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.permissions import PRICE_EDIT_ROLES, VIEW_ROLES, role_required
from apps.billing.forms import AdjustForm, CopyListForm, RateForm
from apps.billing.models import PriceList, PriceListItem
from apps.billing.selectors import price_queries as q
from apps.billing.services.exchange import register_exchange_rate
from apps.billing.services.price_lists import (
    adjust_prices,
    copy_price_list,
    remove_price,
    set_default_price_list,
    set_price,
)
from apps.catalog.selectors.catalog_queries import (
    active_profiles_by_ids,
    active_sections,
    active_tests_by_ids,
    catalog_profiles,
    catalog_tests,
)
from apps.core.exceptions import ApplicationError


def _list(pk) -> PriceList:
    try:
        return q.price_list_by_id(pk=pk)
    except (PriceList.DoesNotExist, ValidationError) as exc:
        raise Http404("Lista no encontrada.") from exc


def _grid_rows(price_list, query="", section_id=""):
    tests_prices, profile_prices = q.items_by_target(price_list=price_list)
    profiles = [] if section_id else [
        p for p in catalog_profiles() if query.lower() in (p.code + p.name).lower()]
    return ([("profile", p, profile_prices.get(p.pk)) for p in profiles]
            + [("test", t, tests_prices.get(t.pk))
               for t in catalog_tests(query=query, section_id=section_id)])


@role_required(*VIEW_ROLES)
def grid(request):
    lists = list(q.all_price_lists())
    if not lists:
        return render(request, "billing/grid.html", {"lists": []})
    current = next((pl for pl in lists if str(pl.pk) == request.GET.get("lista")),
                   lists[0])
    query, section_id = request.GET.get("q", ""), request.GET.get("seccion", "")
    base = q.base_currency()
    return render(request, "billing/grid.html", {
        "lists": lists, "current": current, "rows": _grid_rows(current, query, section_id),
        "query": query, "section_id": section_id, "sections": active_sections(),
        "rates": q.latest_rates(), "base": base, "rate_form": RateForm(base=base),
        "adjust_form": AdjustForm(), "copy_form": CopyListForm(),
        "modes": PriceListItem.PricingMode.choices,
    })


def _decimal(value: str | None):
    """«1.250,50» o «1250.50» → Decimal; vacío → None."""
    value = (value or "").strip()
    if not value:
        return None
    if "," in value:  # formato local: punto de miles, coma decimal
        value = value.replace(".", "").replace(",", ".")
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ApplicationError("Escriba un número válido.") from exc


@role_required(*PRICE_EDIT_ROLES)
@require_POST
def save_price(request, pk):
    """Guarda una fila (htmx) y devuelve la fila actualizada."""
    price_list, kind = _list(pk), request.POST.get("kind")
    getter = active_tests_by_ids if kind == "test" else active_profiles_by_ids
    found = getter(ids=[request.POST.get("id")])
    if not found:
        raise Http404("Examen o perfil no encontrado.")
    target, error = found[0], ""
    target_kw = {kind: target}
    try:
        mode = request.POST.get("mode") or PriceListItem.PricingMode.FIXED
        price, discount = _decimal(request.POST.get("price")), _decimal(
            request.POST.get("discount"))
        if mode == PriceListItem.PricingMode.FIXED and price is None:
            remove_price(price_list=price_list, **target_kw)
        else:
            set_price(price_list=price_list, price=price, pricing_mode=mode,
                      profile_discount_percent=discount, **target_kw)
    except ApplicationError as exc:
        error = exc.message
    tests_prices, profile_prices = q.items_by_target(price_list=price_list)
    item = (tests_prices if kind == "test" else profile_prices).get(target.pk)
    return render(request, "billing/_row.html", {
        "kind": kind, "obj": target, "item": item, "current": price_list, "error": error,
        "saved": not error, "modes": PriceListItem.PricingMode.choices, "can": {
            "prices_edit": True}})


@role_required(*PRICE_EDIT_ROLES)
@require_POST
def adjust(request, pk):
    price_list, form = _list(pk), AdjustForm(request.POST)
    if form.is_valid():
        try:
            changed = adjust_prices(price_list=price_list, **form.cleaned_data)
        except ApplicationError as exc:
            messages.error(request, exc.message)
        else:
            messages.success(request, f"{changed} precio(s) ajustado(s) en {price_list.name}.")
    else:
        messages.error(request, "Revise el porcentaje y el redondeo.")
    return redirect(f"/precios/?lista={price_list.pk}")


@role_required(*PRICE_EDIT_ROLES)
@require_POST
def copy_list(request, pk):
    source, form = _list(pk), CopyListForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Revise el código y el nombre de la nueva lista.")
        return redirect(f"/precios/?lista={source.pk}")
    data = form.cleaned_data
    try:
        target = copy_price_list(
            source=source, code=data["code"], name=data["name"], currency=data["currency"],
            on_date=timezone.localdate(), percent=data["percent"] or Decimal(0),
            round_to=data["round_to"])
    except ApplicationError as exc:
        messages.error(request, exc.message)
        return redirect(f"/precios/?lista={source.pk}")
    messages.success(request, f"Lista {target.name} creada.")
    return redirect(f"/precios/?lista={target.pk}")


@role_required(*PRICE_EDIT_ROLES)
@require_POST
def make_default(request, pk):
    price_list = set_default_price_list(price_list=_list(pk))
    messages.success(request, f"{price_list.name} es ahora la lista predeterminada.")
    return redirect(f"/precios/?lista={price_list.pk}")


@role_required(*PRICE_EDIT_ROLES)
@require_POST
def save_rate(request):
    base = q.base_currency()
    form = RateForm(request.POST, base=base)
    if base is None or not form.is_valid():
        messages.error(request, "Revise la moneda, la tasa y la fecha.")
    else:
        try:
            rate = register_exchange_rate(from_currency=base, to_currency=form.cleaned_data[
                "currency"], rate=form.cleaned_data["rate"],
                effective_date=form.cleaned_data["effective_date"])
        except ApplicationError as exc:
            messages.error(request, exc.message)
        else:
            messages.success(request, f"Tasa {base.code} → {rate.to_currency.code} "
                             f"registrada: {rate.rate}.")
    next_url = request.POST.get("next", "")
    return redirect(next_url if next_url.startswith("/precios/") else "/precios/")
