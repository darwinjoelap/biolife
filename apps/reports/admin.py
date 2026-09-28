"""Admin de consulta: los informes se emiten desde la pantalla de la orden (Fase 11)."""
from django.contrib import admin

from apps.reports.models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ["__str__", "kind", "status", "created_at", "created_by", "short_hash"]
    list_filter = ["kind", "status"]
    search_fields = ["order__number", "verification_code", "content_hash"]
    readonly_fields = [f.name for f in Report._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
