from django.contrib import admin

from apps.settings_lab.models import TenantSettings


@admin.register(TenantSettings)
class TenantSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not TenantSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
