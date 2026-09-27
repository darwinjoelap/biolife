from django import forms
from django.contrib import admin, messages
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html, format_html_join

from apps.catalog.admin_forms import (
    RangeProbeForm,
    ReferenceRangeForm,
    ReferenceRangeInlineFormSet,
)
from apps.catalog.models import (
    CodedOption,
    CodedOptionSet,
    ContainerType,
    Method,
    ObservationTemplate,
    Parameter,
    ParameterGroup,
    Profile,
    ProfileTest,
    ReagentLot,
    ReferenceRange,
    SampleRequirement,
    Section,
    Test,
    Unit,
)
from apps.catalog.selectors.catalog_queries import calculation_input_tests, profile_tests
from apps.catalog.services.formula_engine import FormulaSyntaxError
from apps.catalog.services.formula_validation import (
    sync_parameter_dependencies,
    validate_formula,
)
from apps.catalog.services.reagent_lots import set_current_lot
from apps.catalog.services.reference_range_management import (
    AVISO,
    age_window_text,
    explain_resolution,
    parameter_range_issues,
)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "order_index"]
    search_fields = ["code", "name"]


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ["symbol", "description"]
    search_fields = ["symbol"]


@admin.register(Method)
class MethodAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]


class CodedOptionInline(admin.TabularInline):
    model = CodedOption
    extra = 0


@admin.register(CodedOptionSet)
class CodedOptionSetAdmin(admin.ModelAdmin):
    list_display = ["code", "name"]
    search_fields = ["code", "name"]
    inlines = [CodedOptionInline]


class ParameterGroupInline(admin.TabularInline):
    model = ParameterGroup
    extra = 0


class ParameterInline(admin.TabularInline):
    """En la ficha del examen: cada parámetro con sus rangos y un enlace para editarlos."""

    model = Parameter
    fk_name = "test"
    extra = 0
    fields = ["code", "name", "group", "value_type", "unit", "order_index", "ranges_summary"]
    readonly_fields = ["ranges_summary"]
    show_change_link = True

    @admin.display(description="Rangos de referencia")
    def ranges_summary(self, obj: Parameter) -> str:
        if obj is None or obj._state.adding:
            return "—"
        ranges = obj.reference_ranges.filter(is_active=True).order_by(
            "condition", "sex", "age_min_days"
        )
        url = reverse("admin:catalog_parameter_change", args=[obj.pk])
        rows = format_html_join(
            "", "<div>{} · {} · {}: <b>{}</b></div>",
            (
                (r.get_sex_display(), age_window_text(r.age_min_days, r.age_max_days),
                 r.get_condition_display(), r.display_text)
                for r in ranges
            ),
        )
        return format_html('{}<a href="{}#reference_ranges-group">Editar rangos →</a>',
                           rows or "Sin rangos. ", url)


@admin.register(ObservationTemplate)
class ObservationTemplateAdmin(admin.ModelAdmin):
    list_display = ["text", "test", "section", "order_index", "is_active"]
    list_filter = ["section", "is_active"]
    list_editable = ["order_index", "is_active"]
    search_fields = ["text"]
    autocomplete_fields = ["test"]


@admin.register(ReagentLot)
class ReagentLotAdmin(admin.ModelAdmin):
    list_display = ["reagent", "lot_number", "brand", "isi", "expires_on", "is_current"]
    list_filter = ["reagent", "is_current"]
    search_fields = ["lot_number", "brand"]
    actions = ["marcar_vigente"]

    @admin.action(description="Marcar como lote vigente")
    def marcar_vigente(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Elija un solo lote.", level=messages.ERROR)
            return
        lot = set_current_lot(lot=queryset.get())
        self.message_user(request, f"{lot} es ahora el lote vigente.")

    def save_model(self, request, obj, form, change):
        wants_current = obj.is_current
        obj.is_current = False if wants_current else obj.is_current
        super().save_model(request, obj, form, change)
        if wants_current:
            set_current_lot(lot=obj)


@admin.register(ContainerType)
class ContainerTypeAdmin(admin.ModelAdmin):
    list_display = ["muestra_color", "name", "short_name", "additive", "sample_type",
                    "draw_order", "max_tests", "is_active"]
    list_display_links = ["name"]
    list_editable = ["draw_order", "max_tests"]
    search_fields = ["code", "name"]

    @admin.display(description="Color")
    def muestra_color(self, obj):
        return format_html(
            '<span style="display:inline-block;width:14px;height:14px;border-radius:50%;'
            'background:{}"></span>', obj.color,
        )


class SampleRequirementInline(admin.TabularInline):
    model = SampleRequirement
    extra = 0
    fields = ["container_type", "collection_label", "own_container", "order_index"]
    verbose_name_plural = "Tubos que requiere (toma de muestra)"


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "section", "sample_type", "tubos", "is_active"]
    list_filter = ["section", "sample_type"]
    search_fields = ["code", "name"]
    inlines = [SampleRequirementInline, ParameterGroupInline, ParameterInline]

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            "sample_requirements__container_type"
        )

    @admin.display(description="Tubos")
    def tubos(self, obj):
        return format_html_join(
            " ", '<span style="color:{}">●</span> {}',
            ((r.container_type.color, r.container_type.short_name)
             for r in obj.sample_requirements.all()),
        )


class ParameterAdminForm(forms.ModelForm):
    """Valida la fórmula (sintaxis, referencias, ciclos) antes de guardar."""

    class Meta:
        model = Parameter
        # depends_on fuera a propósito: se deriva de la fórmula, nunca se edita a mano.
        fields = [
            "test", "group", "code", "name", "value_type", "unit", "decimals",
            "order_index", "option_set", "formula", "is_printable", "is_optional",
            "instrument_code", "is_active",
        ]

    def clean(self):
        cleaned = super().clean()
        formula = cleaned.get("formula", "")
        code = cleaned.get("code")
        if cleaned.get("value_type") == Parameter.ValueType.NUMERIC_CALCULATED and code:
            try:
                cleaned["formula"] = validate_formula(code=code, formula=formula).source
            except FormulaSyntaxError as exc:
                self.add_error("formula", exc.message)
        return cleaned


class ReferenceRangeInline(admin.StackedInline):
    """Rangos del parámetro por sexo, edad (años/meses/días) y condición."""

    model = ReferenceRange
    form = ReferenceRangeForm
    formset = ReferenceRangeInlineFormSet
    extra = 0
    ordering = ["condition", "sex", "age_min_days"]
    fieldsets = [
        ("A quién aplica", {"fields": [("sex", "condition", "priority", "is_active")]}),
        ("Edad", {
            "fields": [("desde_anos", "desde_meses", "desde_dias"),
                       ("hasta_anos", "hasta_meses", "hasta_dias")],
            "description": "«Hasta» no se incluye: 0 a 1 año = hasta el día antes de "
                           "cumplir 1 año. Vacío = sin límite.",
        }),
        ("Valores", {"fields": ["range_type", ("low", "high"), ("center", "tolerance"),
                                "expected_option", "bands"]}),
        ("Impresión", {"fields": [("display_text", "unit")]}),
        ("Valores críticos (pánico)", {
            "fields": [("critical_low", "critical_high"), "critical_note"],
            "description": "Fuera de estos límites el resultado se marca CRÍTICO y no se "
                           "valida sin registrar a quién se notificó. Vacío = sin crítico.",
        }),
    ]

    def get_formset(self, request, obj=None, **kwargs):
        self._parent_parameter = obj
        return super().get_formset(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        # La opción esperada sólo puede ser del conjunto de opciones del parámetro.
        if db_field.name == "expected_option":
            parameter = getattr(self, "_parent_parameter", None)
            queryset = CodedOption.objects.none()
            if parameter is not None and parameter.option_set_id:
                queryset = CodedOption.objects.filter(option_set_id=parameter.option_set_id)
            kwargs["queryset"] = queryset
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    form = ParameterAdminForm
    list_display = ["code", "name", "test", "group", "value_type", "unit", "formula"]
    list_filter = ["value_type", "test"]
    search_fields = ["code", "name"]
    readonly_fields = ["dependencies", "range_coverage", "range_probe_link"]
    inlines = [ReferenceRangeInline]

    @admin.display(description="Cobertura de rangos")
    def range_coverage(self, obj: Parameter) -> str:
        if obj is None or obj._state.adding:
            return "—"
        issues = parameter_range_issues(parameter=obj)
        if not issues:
            return "Sin solapes ni huecos."
        return format_html_join("", "<div>{}: {}</div>",
                                ((i.level, i.message) for i in issues))

    @admin.display(description="Probador")
    def range_probe_link(self, obj: Parameter) -> str:
        if obj is None or obj._state.adding:
            return "—"
        url = reverse("admin:catalog_parameter_probe", args=[obj.pk])
        return format_html('<a href="{}">Probar qué rango aplica a un paciente →</a>', url)

    def get_urls(self):
        custom = [
            path("<path:object_id>/probar-rangos/",
                 self.admin_site.admin_view(self.probe_view),
                 name="catalog_parameter_probe"),
        ]
        return custom + super().get_urls()

    def probe_view(self, request, object_id):
        """Orquesta: valida el formulario y delega en `explain_resolution()`."""
        parameter = get_object_or_404(Parameter, pk=object_id)
        form = RangeProbeForm(request.GET or None)
        explanation = None
        if form.is_valid():
            explanation = explain_resolution(
                parameter=parameter, sex=form.cleaned_data["sexo"],
                age_days=form.age_days(), condition=form.cleaned_data["condicion"],
            )
        context = {
            **self.admin_site.each_context(request), "opts": self.model._meta,
            "original": parameter, "title": f"Probar rangos — {parameter}",
            "form": form, "explanation": explanation,
        }
        return TemplateResponse(request, "admin/catalog/parameter/probar_rangos.html",
                                context)

    @admin.display(description="Depende de")
    def dependencies(self, obj: Parameter) -> str:
        # El pk UUID existe antes de guardar: usar _state.adding, no obj.pk.
        if obj is None or obj._state.adding:
            return "—"
        return ", ".join(obj.depends_on.values_list("code", flat=True)) or "—"

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        sync_parameter_dependencies(parameter=form.instance)
        for formset in formsets:
            for warning in getattr(formset, "range_warnings", []):
                messages.warning(request, f"{AVISO}: {warning}")


class ReferenceRangeStandaloneForm(ReferenceRangeForm):
    class Meta(ReferenceRangeForm.Meta):
        fields = ["parameter", *ReferenceRangeForm.Meta.fields]


@admin.register(ReferenceRange)
class ReferenceRangeAdmin(admin.ModelAdmin):
    """Vista de lista global. Para editar con validación de solapes, usar la ficha del
    parámetro (los rangos se editan juntos allí)."""

    form = ReferenceRangeStandaloneForm
    list_display = [
        "parameter", "range_type", "sex", "age_window", "condition", "display_text",
        "priority", "is_active",
    ]
    autocomplete_fields = ["parameter"]

    @admin.display(description="Edad", ordering="age_min_days")
    def age_window(self, obj: ReferenceRange) -> str:
        return age_window_text(obj.age_min_days, obj.age_max_days)
    list_filter = ["range_type", "sex", "condition", "parameter__test"]
    search_fields = ["parameter__code", "parameter__name", "display_text"]


class ProfileTestInline(admin.TabularInline):
    model = ProfileTest
    extra = 0
    fields = ["order_index", "test"]
    autocomplete_fields = ["test"]
    ordering = ["order_index"]


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "order_index", "test_count", "is_active"]
    list_editable = ["order_index"]
    search_fields = ["code", "name"]
    inlines = [ProfileTestInline]

    @admin.display(description="Exámenes")
    def test_count(self, obj: Profile) -> int:
        return obj.profile_tests.count()

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        missing = calculation_input_tests(tests=profile_tests(profile=form.instance))
        if missing:
            messages.warning(
                request,
                "Este perfil no incluye exámenes que alimentan sus cálculos: "
                + ", ".join(sorted(t.code for t in missing)),
            )
