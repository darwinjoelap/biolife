"""Monedas y descuentos en las tablas auxiliares de `core` (Fase 11d, ADR-031).
Se registran desde `BillingConfig.ready()`."""
from apps.accounts.permissions import PRICE_EDIT_ROLES, VIEW_ROLES, user_has_any_role
from apps.billing.aux_forms import CurrencyForm, DiscountForm
from apps.billing.models import Currency, Discount
from apps.billing.selectors import aux_queries as q
from apps.billing.services import aux_editing as svc
from apps.core.aux_tables import AuxTable, register

GROUP = "Cobro"
MONEY = {
    "can_view": lambda user: user_has_any_role(user, *VIEW_ROLES),
    "can_edit": lambda user: user_has_any_role(user, *PRICE_EDIT_ROLES),
    "editors": "Administrador y facturación",
}


def _discount_value(d):
    if d.kind == Discount.Kind.PERCENT:
        return f"{d.value:g} %"
    return f"{d.currency.symbol if d.currency_id else ''} {d.value}".strip()


def _validity(d):
    if not d.valid_from and not d.valid_until:
        return "Siempre"
    start = d.valid_from.strftime("%d/%m/%Y") if d.valid_from else "…"
    end = d.valid_until.strftime("%d/%m/%Y") if d.valid_until else "…"
    return f"{start} – {end}"


register(
    AuxTable(
        key="monedas", title="Monedas", singular="moneda", icon="coins", group=GROUP, position=30,
        description="Monedas de las listas de precios. La base no cambia.",
        form_class=CurrencyForm, queryset=q.currencies,
        get=lambda pk: Currency.objects.get(pk=pk), new=Currency,
        columns=["Moneda", "Código", "Símbolo", "Decimales", "Listas activas", "Base"],
        row=lambda c: [c.name, c.code, c.symbol, c.decimals, c.list_count,
                       "Moneda base" if c.is_base else "—"],
        save=svc.save_currency,
        count=lambda: Currency.objects.filter(is_active=True).count(),
        layout={"code": "col-2", "name": "col-4", "symbol": "col-2", "decimals": "col-2",
                "order_index": "col-2", "is_active": "col-3"},
        note="La moneda base no se cambia ni se desactiva. Las tasas se cargan en Precios.",
        **MONEY,
    ),
    AuxTable(
        key="descuentos", title="Descuentos", singular="descuento", icon="percent",
        group=GROUP, position=30,
        description="Descuentos que se ofrecen al registrar una orden.",
        form_class=DiscountForm, queryset=q.discounts,
        get=lambda pk: Discount.objects.get(pk=pk), new=Discount,
        columns=["Descuento", "Código", "Valor", "Alcance", "Vigencia", "Autorización"],
        row=lambda d: [d.name, d.code, _discount_value(d), d.get_scope_display(),
                       _validity(d), "Requiere" if d.requires_authorization else "—"],
        save=svc.save_discount,
        count=lambda: Discount.objects.filter(is_active=True).count(),
        layout={"code": "col-3", "name": "col-6", "kind": "col-3", "value": "col-3",
                "currency": "col-3", "scope": "col-3", "tests": "col-6",
                "profiles": "col-6", "valid_from": "col-3", "valid_until": "col-3",
                "is_stackable": "col-3", "requires_authorization": "col-3",
                "order_index": "col-2", "notes": "col-7", "is_active": "col-3"},
        **MONEY,
    ),
)
