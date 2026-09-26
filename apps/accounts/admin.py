from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import Membership, Role, User


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 1


@admin.register(User)
class BiolifeUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Datos de Biolife", {"fields": ("phone", "professional_license")}),
    )
    inlines = [MembershipInline]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_system")
    list_filter = ("is_system",)
