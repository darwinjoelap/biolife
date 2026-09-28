from django.contrib import admin
from django.db import connection

from apps.tenants.models import Domain, Plan, PlatformSettings, Subscription, Tenant


class PublicOnlyAdmin(admin.ModelAdmin):
    """Modelos de la plataforma: sólo se ven en el admin de `public`, nunca desde el admin
    de un laboratorio (aunque el usuario sea superusuario allí)."""

    def has_module_permission(self, request):
        return connection.schema_name == "public" and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return connection.schema_name == "public" and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return connection.schema_name == "public" and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return (connection.schema_name == "public"
                and super().has_change_permission(request, obj))

    def has_delete_permission(self, request, obj=None):
        return (connection.schema_name == "public"
                and super().has_delete_permission(request, obj))


class DomainInline(admin.TabularInline):
    model = Domain
    extra = 1


@admin.register(Tenant)
class TenantAdmin(PublicOnlyAdmin):
    list_display = ("name", "schema_name", "status", "onboarded_at", "paid_until")
    list_filter = ("status",)
    search_fields = ("name", "schema_name", "rif")
    inlines = [DomainInline]


@admin.register(Plan)
class PlanAdmin(PublicOnlyAdmin):
    list_display = ("name", "code", "price_monthly", "currency", "is_public")


@admin.register(Subscription)
class SubscriptionAdmin(PublicOnlyAdmin):
    list_display = ("tenant", "plan", "status", "current_period_end")
    list_filter = ("status",)


@admin.register(PlatformSettings)
class PlatformSettingsAdmin(PublicOnlyAdmin):
    fieldsets = [("Pie del informe PDF", {"fields": (
        "report_brand_enabled", "report_brand_text", "report_brand_contact")})]

    def has_add_permission(self, request):
        return super().has_add_permission(request) and not PlatformSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
