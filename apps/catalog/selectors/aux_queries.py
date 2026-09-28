"""Consultas de las tablas auxiliares del catálogo (Fase 11d)."""
from django.db.models import Count, Q, QuerySet

from apps.catalog.models import (
    CodedOptionSet,
    ContainerType,
    Method,
    ObservationTemplate,
    Parameter,
    ReagentLot,
    Section,
    Unit,
)


def _filter(qs: QuerySet, *, show_inactive: bool, query: str, fields: tuple) -> QuerySet:
    if not show_inactive:
        qs = qs.filter(is_active=True)
    if query:
        condition = Q()
        for name in fields:
            condition |= Q(**{f"{name}__icontains": query.strip()})
        qs = qs.filter(condition)
    return qs


def sections(*, show_inactive=False, query=""):
    qs = Section.objects.annotate(test_count=Count("tests", distinct=True))
    return _filter(qs, show_inactive=show_inactive, query=query,
                   fields=("code", "name")).order_by("order_index", "name")


def units(*, show_inactive=False, query=""):
    qs = Unit.objects.annotate(parameter_count=Count("parameters", distinct=True))
    return _filter(qs, show_inactive=show_inactive, query=query,
                   fields=("symbol", "description")).order_by("symbol")


def methods(*, show_inactive=False, query=""):
    qs = Method.objects.annotate(test_count=Count("tests", distinct=True))
    return _filter(qs, show_inactive=show_inactive, query=query,
                   fields=("name", "description")).order_by("name")


def option_sets(*, show_inactive=False, query=""):
    qs = CodedOptionSet.objects.annotate(
        option_count=Count("options", filter=Q(options__is_active=True), distinct=True),
        parameter_count=Count("parameters", distinct=True))
    return _filter(qs, show_inactive=show_inactive, query=query,
                   fields=("code", "name", "options__value")).distinct().order_by("code")


def general_observations(*, show_inactive=False, query=""):
    qs = ObservationTemplate.objects.filter(test__isnull=True).select_related("section")
    qs = _filter(qs, show_inactive=show_inactive, query=query, fields=("text",))
    return qs.order_by("section__order_index", "order_index", "text")


def containers(*, show_inactive=False, query=""):
    qs = ContainerType.objects.annotate(
        test_count=Count("requirements__test", distinct=True))
    return _filter(qs, show_inactive=show_inactive, query=query,
                   fields=("code", "name", "short_name")).order_by("draw_order", "name")


def lots(*, show_inactive=False, query=""):
    return _filter(ReagentLot.objects.all(), show_inactive=show_inactive, query=query,
                   fields=("lot_number", "brand")).order_by("reagent", "-is_current",
                                                            "-created_at")


def section_in_use(*, section: Section) -> bool:
    return bool(section.pk) and section.tests.exists()


def option_set_in_use(*, option_set: CodedOptionSet) -> bool:
    return bool(option_set.pk) and option_set.parameters.exists()


def option_set_has_results(*, option_set: CodedOptionSet) -> bool:
    """Algún parámetro con esta lista ya tiene resultados: el texto de sus opciones
    queda fijo (los informes vuelven a emitirse con ese texto)."""
    return bool(option_set.pk) and Parameter.objects.filter(
        option_set=option_set, result_values__isnull=False).exists()


def container_in_use(*, container: ContainerType) -> bool:
    return bool(container.pk) and (container.requirements.exists()
                                   or container.samples.exists())
