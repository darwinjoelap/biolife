from django.contrib import admin

from apps.patients.models import Guardian, Patient, PatientGuardian


class PatientGuardianInline(admin.TabularInline):
    model = PatientGuardian
    fk_name = "patient"
    extra = 0
    autocomplete_fields = ["guardian"]


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = [
        "internal_code", "first_name", "last_name", "document_type",
        "document_number", "sex", "is_minor",
    ]
    list_filter = ["document_type", "sex"]
    search_fields = ["internal_code", "document_number", "first_name", "last_name"]
    readonly_fields = ["internal_code"]
    inlines = [PatientGuardianInline]

    @admin.display(boolean=True, description="Menor de edad")
    def is_minor(self, obj: Patient) -> bool:
        return obj.is_minor

    def save_formset(self, request, form, formset, change):
        """Los PatientGuardian inline se guardan junto con el Patient del admin, no
        vía services/patient_creation.py (ese service es para el flujo normal de
        recepción). La regla de negocio "menor sin documento exige representante" no
        se re-valida aquí — el admin es para operación manual mientras no hay UI
        propia (Fase 04, Tarea 5); no reemplaza al service."""
        super().save_formset(request, form, formset, change)


@admin.register(Guardian)
class GuardianAdmin(admin.ModelAdmin):
    list_display = ["first_name", "last_name", "document_type", "document_number", "phone"]
    search_fields = ["document_number", "first_name", "last_name"]
