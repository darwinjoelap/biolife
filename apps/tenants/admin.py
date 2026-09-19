from django.contrib import admin

from apps.tenants.models import Domain, Plan, Subscription, Tenant


class DomainInline(admin.TabularInline):
    model = Domain
    extra = 1


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "schema_name", "status", "onboarded_at", "paid_until")
    list_filter = ("status",)
    search_fields = ("name", "schema_name", "rif")
    inlines = [DomainInline]


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "price_monthly", "currency", "is_public")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("tenant", "plan", "status", "current_period_end")
    list_filter = ("status",)
