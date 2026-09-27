"""Admin de consulta: las órdenes se registran y modifican desde las pantallas de
recepción (services), no desde aquí."""
from django.contrib import admin

from apps.orders.models import LabelPrint, Order, OrderItem, Sample


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ["test", "profile", "status"]
    readonly_fields = fields
    can_delete = False


class SampleInline(admin.TabularInline):
    model = Sample
    extra = 0
    fields = ["number", "container_type", "collection_label", "status", "collected_at"]
    readonly_fields = fields
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["number", "patient", "status", "priority", "total", "currency_code",
                    "is_paid", "ordered_at"]
    list_filter = ["status", "priority", "is_paid"]
    search_fields = ["number", "patient__first_name", "patient__last_name",
                     "patient__document_number"]
    readonly_fields = [f.name for f in Order._meta.fields]
    inlines = [OrderItemInline, SampleInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    list_display = ["number", "order", "container_type", "status", "collected_at"]
    list_filter = ["status", "container_type"]
    search_fields = ["number", "barcode", "order__number"]
    readonly_fields = [f.name for f in Sample._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LabelPrint)
class LabelPrintAdmin(admin.ModelAdmin):
    list_display = ["sample", "is_reprint", "created_by", "created_at"]
    readonly_fields = ["sample", "is_reprint", "created_by", "created_at"]

    def has_add_permission(self, request):
        return False
