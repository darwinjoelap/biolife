"""Precios por tenant (Fase 08, ADR-019): monedas, tasas de cambio, listas de precios,
precios por examen/perfil y descuentos. El cobro (pagos, facturas al paciente) llega en una
fase posterior; aquí sólo se define cuánto cuesta algo y cómo se cotiza."""
from django.db import models
from django.db.models import F, Q

from apps.core.models import TenantBaseModel


class Currency(TenantBaseModel):
    """Moneda que usa el laboratorio (USD, VES...). Una sola es la moneda base."""

    code = models.CharField("Código ISO 4217", max_length=3, unique=True)
    name = models.CharField("Nombre", max_length=60)
    symbol = models.CharField("Símbolo", max_length=8)
    decimals = models.PositiveSmallIntegerField("Decimales", default=2)
    is_base = models.BooleanField("Moneda base", default=False)
    order_index = models.PositiveIntegerField("Orden", default=0)

    class Meta:
        verbose_name = "Moneda"
        verbose_name_plural = "Monedas"
        ordering = ["order_index", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_base"], condition=Q(is_base=True), name="currency_single_base"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.symbol})"


class ExchangeRate(TenantBaseModel):
    """Tasa de cambio vigente desde `effective_date`: 1 `from_currency` = `rate`
    `to_currency`. Se usa la más reciente con fecha <= la de la cotización."""

    class Source(models.TextChoices):
        MANUAL = "MANUAL", "Carga manual"
        BCV = "BCV", "Banco Central de Venezuela"
        OTRO = "OTRO", "Otra fuente"

    from_currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="rates_from", verbose_name="De"
    )
    to_currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="rates_to", verbose_name="A"
    )
    rate = models.DecimalField("Tasa", max_digits=20, decimal_places=8)
    effective_date = models.DateField("Vigente desde")
    source = models.CharField(
        "Fuente", max_length=10, choices=Source.choices, default=Source.MANUAL
    )
    notes = models.CharField("Notas", max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "Tasa de cambio"
        verbose_name_plural = "Tasas de cambio"
        ordering = ["-effective_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["from_currency", "to_currency", "effective_date"],
                name="exchangerate_unique_pair_date",
            ),
            models.CheckConstraint(condition=Q(rate__gt=0), name="exchangerate_rate_positive"),
            models.CheckConstraint(
                condition=~Q(from_currency=F("to_currency")),
                name="exchangerate_distinct_currencies",
            ),
        ]

    def __str__(self) -> str:
        return f"1 {self.from_currency.code} = {self.rate} {self.to_currency.code}"


class PriceList(TenantBaseModel):
    """Lista de precios en una moneda (GENERAL, CONVENIO X, JORNADA...). Una sola es la
    predeterminada; puede tener vigencia."""

    code = models.CharField("Código", max_length=30, unique=True)
    name = models.CharField("Nombre", max_length=100)
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="price_lists", verbose_name="Moneda"
    )
    is_default = models.BooleanField("Predeterminada", default=False)
    valid_from = models.DateField("Vigente desde", null=True, blank=True)
    valid_until = models.DateField("Vigente hasta", null=True, blank=True)
    order_index = models.PositiveIntegerField("Orden", default=0)
    notes = models.TextField("Notas", blank=True, default="")

    class Meta:
        verbose_name = "Lista de precios"
        verbose_name_plural = "Listas de precios"
        ordering = ["order_index", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["is_default"], condition=Q(is_default=True),
                name="pricelist_single_default",
            ),
            models.CheckConstraint(
                condition=Q(valid_from__isnull=True)
                | Q(valid_until__isnull=True)
                | Q(valid_from__lte=F("valid_until")),
                name="pricelist_valid_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.currency.code})"


class PriceListItem(TenantBaseModel):
    """Precio de un examen **o** de un perfil dentro de una lista.

    Perfiles: `FIXED` usa `price`; `SUM_WITH_DISCOUNT` suma los precios individuales de sus
    exámenes en esta misma lista y resta `profile_discount_percent`."""

    class PricingMode(models.TextChoices):
        FIXED = "FIXED", "Precio fijo"
        SUM_WITH_DISCOUNT = "SUM_WITH_DISCOUNT", "Suma de exámenes menos %"

    price_list = models.ForeignKey(
        PriceList, on_delete=models.CASCADE, related_name="items", verbose_name="Lista"
    )
    test = models.ForeignKey(
        "catalog.Test", on_delete=models.PROTECT, related_name="price_items",
        null=True, blank=True, verbose_name="Examen",
    )
    profile = models.ForeignKey(
        "catalog.Profile", on_delete=models.PROTECT, related_name="price_items",
        null=True, blank=True, verbose_name="Perfil",
    )
    pricing_mode = models.CharField(
        "Modo de precio", max_length=20, choices=PricingMode.choices,
        default=PricingMode.FIXED,
    )
    price = models.DecimalField(
        "Precio", max_digits=14, decimal_places=2, null=True, blank=True
    )
    profile_discount_percent = models.DecimalField(
        "% de descuento del perfil", max_digits=5, decimal_places=2, null=True, blank=True
    )
    order_index = models.PositiveIntegerField("Orden", default=0)

    class Meta:
        verbose_name = "Precio"
        verbose_name_plural = "Precios"
        ordering = ["price_list", "order_index"]
        constraints = [
            models.CheckConstraint(
                condition=(Q(test__isnull=False) & Q(profile__isnull=True))
                | (Q(test__isnull=True) & Q(profile__isnull=False)),
                name="pricelistitem_test_xor_profile",
            ),
            models.UniqueConstraint(
                fields=["price_list", "test"], condition=Q(test__isnull=False),
                name="pricelistitem_unique_test",
            ),
            models.UniqueConstraint(
                fields=["price_list", "profile"], condition=Q(profile__isnull=False),
                name="pricelistitem_unique_profile",
            ),
            models.CheckConstraint(
                condition=~Q(pricing_mode="FIXED") | Q(price__isnull=False),
                name="pricelistitem_fixed_requires_price",
            ),
            models.CheckConstraint(
                condition=~Q(pricing_mode="SUM_WITH_DISCOUNT")
                | (
                    Q(profile__isnull=False)
                    & Q(profile_discount_percent__gte=0)
                    & Q(profile_discount_percent__lte=100)
                ),
                name="pricelistitem_sum_mode_only_profiles_with_percent",
            ),
            models.CheckConstraint(
                condition=Q(price__isnull=True) | Q(price__gte=0),
                name="pricelistitem_price_non_negative",
            ),
        ]

    def __str__(self) -> str:
        target = self.test or self.profile
        return f"{self.price_list.code} — {target}"


class Discount(TenantBaseModel):
    """Descuento configurable: porcentaje o monto fijo, sobre toda la orden o sobre ciertos
    exámenes/perfiles, con vigencia. Ver reglas de combinación en `services/quoting.py`."""

    class Kind(models.TextChoices):
        PERCENT = "PERCENT", "Porcentaje"
        FIXED_AMOUNT = "FIXED_AMOUNT", "Monto fijo"

    class Scope(models.TextChoices):
        ORDER = "ORDER", "Toda la orden"
        ITEM = "ITEM", "Por examen/perfil"

    code = models.CharField("Código", max_length=30, unique=True)
    name = models.CharField("Nombre", max_length=100)
    kind = models.CharField("Tipo", max_length=15, choices=Kind.choices)
    value = models.DecimalField("Valor", max_digits=14, decimal_places=2)
    currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, related_name="discounts",
        null=True, blank=True, verbose_name="Moneda (monto fijo)",
    )
    scope = models.CharField("Alcance", max_length=10, choices=Scope.choices)
    tests = models.ManyToManyField(
        "catalog.Test", blank=True, related_name="discounts", verbose_name="Exámenes"
    )
    profiles = models.ManyToManyField(
        "catalog.Profile", blank=True, related_name="discounts", verbose_name="Perfiles"
    )
    valid_from = models.DateField("Vigente desde", null=True, blank=True)
    valid_until = models.DateField("Vigente hasta", null=True, blank=True)
    is_stackable = models.BooleanField("Acumulable con otros", default=False)
    requires_authorization = models.BooleanField("Requiere autorización", default=False)
    order_index = models.PositiveIntegerField("Orden", default=0)
    notes = models.TextField("Notas", blank=True, default="")

    class Meta:
        verbose_name = "Descuento"
        verbose_name_plural = "Descuentos"
        ordering = ["order_index", "name"]
        constraints = [
            models.CheckConstraint(condition=Q(value__gt=0), name="discount_value_positive"),
            models.CheckConstraint(
                condition=~Q(kind="PERCENT") | Q(value__lte=100),
                name="discount_percent_max_100",
            ),
            models.CheckConstraint(
                condition=~Q(kind="FIXED_AMOUNT") | Q(currency__isnull=False),
                name="discount_fixed_requires_currency",
            ),
        ]

    def __str__(self) -> str:
        return self.name
