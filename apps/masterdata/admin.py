from django.contrib import admin

from apps.masterdata.models import Locality


@admin.register(Locality)
class LocalityAdmin(admin.ModelAdmin):
    list_display = ("name", "state", "municipality")
    list_filter = ("state",)
    search_fields = ("name", "municipality")
