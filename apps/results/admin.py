"""Admin de consulta: los resultados se cargan y validan en las pantallas de la Fase 10."""
from django.contrib import admin

from apps.results.models import CriticalNotification, Result, ResultValue


class ResultValueInline(admin.TabularInline):
    model = ResultValue
    extra = 0
    fields = ["parameter", "value_numeric", "value_text", "coded_option", "flag",
              "reference_text"]
    readonly_fields = fields
    can_delete = False


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ["order_item", "status", "entered_by", "validated_by", "validated_at"]
    list_filter = ["status"]
    search_fields = ["order_item__order__number", "order_item__test__name"]
    readonly_fields = [f.name for f in Result._meta.fields]
    inlines = [ResultValueInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CriticalNotification)
class CriticalNotificationAdmin(admin.ModelAdmin):
    list_display = ["result_value", "value_display", "notified_to", "method", "notified_at",
                    "created_by"]
    readonly_fields = [f.name for f in CriticalNotification._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
