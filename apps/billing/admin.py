from django.contrib import admin

from apps.billing.models import Currency, Discount, ExchangeRate, PriceList, PriceListItem


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "symbol", "decimals", "is_base", "order_index",
                    "is_active"]
    list_editable = ["order_index"]


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ["effective_date", "from_currency", "to_currency", "rate", "source"]
    list_filter = ["from_currency", "to_currency", "source"]
    date_hierarchy = "effective_date"


class PriceListItemInline(admin.TabularInline):
    model = PriceListItem
    extra = 0
    fields = ["order_index", "test", "profile", "pricing_mode", "price",
              "profile_discount_percent", "is_active"]
    autocomplete_fields = ["test", "profile"]
    ordering = ["order_index"]


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "currency", "is_default", "valid_from", "valid_until",
                    "order_index", "is_active"]
    list_editable = ["order_index"]
    search_fields = ["code", "name"]
    inlines = [PriceListItemInline]


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "kind", "value", "currency", "scope", "valid_from",
                    "valid_until", "is_stackable", "requires_authorization", "is_active"]
    list_filter = ["kind", "scope", "is_stackable", "requires_authorization"]
    search_fields = ["code", "name"]
    filter_horizontal = ["tests", "profiles"]
