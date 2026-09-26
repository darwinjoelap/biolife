from django.contrib import admin

from apps.catalog.models import (
    CodedOption,
    CodedOptionSet,
    Method,
    Parameter,
    ParameterGroup,
    ReferenceRange,
    Section,
    Test,
    Unit,
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
    model = Parameter
    fk_name = "test"
    extra = 0
    fields = ["code", "name", "group", "value_type", "unit", "order_index"]


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "section", "sample_type", "is_active"]
    list_filter = ["section", "sample_type"]
    search_fields = ["code", "name"]
    inlines = [ParameterGroupInline, ParameterInline]


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "test", "group", "value_type", "unit"]
    list_filter = ["value_type", "test"]
    search_fields = ["code", "name"]


@admin.register(ReferenceRange)
class ReferenceRangeAdmin(admin.ModelAdmin):
    list_display = [
        "parameter", "range_type", "sex", "age_min_days", "age_max_days",
        "condition", "display_text", "priority",
    ]
    list_filter = ["range_type", "sex", "condition", "parameter__test"]
    search_fields = ["parameter__code", "parameter__name", "display_text"]
