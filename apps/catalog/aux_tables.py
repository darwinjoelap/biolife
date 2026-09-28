"""Tablas auxiliares del catálogo en las pantallas de `core` (Fase 11d, ADR-031).
Se registran desde `CatalogConfig.ready()`."""
from django.utils.html import format_html

from apps.accounts.permissions import (
    CATALOG_EDIT_ROLES,
    CLINICAL_EDIT_ROLES,
    LOT_EDIT_ROLES,
    VIEW_ROLES,
    user_has_any_role,
)
from apps.catalog import aux_forms as f
from apps.catalog.models import (
    CodedOptionSet,
    ContainerType,
    Method,
    ObservationTemplate,
    ReagentLot,
    Section,
    Unit,
)
from apps.catalog.selectors import aux_queries as q
from apps.catalog.services import aux_editing as svc
from apps.core.aux_tables import AuxTable, register

GROUP = "Catálogo"
GROUP_LAB = "Toma y reactivos"


def _roles(*codes):
    return lambda user: user_has_any_role(user, *codes)


def _dash(value):
    return value if value not in (None, "") else "—"


def _active(model):
    return lambda: model.objects.filter(is_active=True).count()


COMMON = {"can_view": _roles(*VIEW_ROLES)}
ADMIN = {"can_edit": _roles(*CATALOG_EDIT_ROLES), "editors": "Administrador"}
CLINICAL = {"can_edit": _roles(*CLINICAL_EDIT_ROLES),
            "editors": "Administrador y bioanalista"}


def _option_formsets(data, instance):
    locked = q.option_set_has_results(option_set=instance)
    formset = f.OptionFormSet(data, instance=instance, prefix="opciones",
                              values_locked=locked)
    help_text = ("Ya hay resultados con esta lista: el texto de las opciones existentes "
                 "queda fijo; puede agregar nuevas o desactivarlas." if locked else
                 "«Patológica» marca el resultado como anormal; el orden clínico ordena "
                 "de menor a mayor (NEGATIVO, +, ++…).")
    return [("Opciones", formset, help_text)]


def _tube(c):
    return format_html('<span class="tube-dot" style="--tube: {}"></span> {}', c.color,
                       c.name)


register(
    AuxTable(
        key="secciones", title="Secciones", singular="sección", icon="folder", group=GROUP,
        description="Agrupan los exámenes en el informe y en las listas.",
        form_class=f.SectionForm, queryset=q.sections, get=lambda pk: Section.objects.get(pk=pk),
        new=Section, columns=["Sección", "Código", "Orden", "Exámenes", "Salto de página"],
        row=lambda s: [s.name, s.code, s.order_index, s.test_count,
                       "Sí" if s.print_page_break else "—"],
        save=svc.save_record, count=_active(Section),
        form_kwargs=lambda s: {"code_locked": q.section_in_use(section=s)},
        layout={"code": "col-3", "name": "col-6", "order_index": "col-3",
                "print_page_break": "col-6", "is_active": "col-6"},
        **COMMON, **ADMIN,
    ),
    AuxTable(
        key="unidades", title="Unidades", singular="unidad", icon="ruler", group=GROUP,
        description="Unidades de medida de los parámetros (g/dL, mg/dL, %…).",
        form_class=f.UnitForm, queryset=q.units, get=lambda pk: Unit.objects.get(pk=pk),
        new=Unit, columns=["Símbolo", "Descripción", "Parámetros"],
        row=lambda u: [u.symbol, _dash(u.description), u.parameter_count],
        save=svc.save_record, count=_active(Unit),
        layout={"symbol": "col-3", "description": "col-6", "is_active": "col-3"},
        **COMMON, **ADMIN,
    ),
    AuxTable(
        key="metodos", title="Métodos", singular="método", icon="book-open", group=GROUP,
        description="Método analítico que se imprime bajo el examen.",
        form_class=f.MethodForm, queryset=q.methods, get=lambda pk: Method.objects.get(pk=pk),
        new=Method, columns=["Método", "Descripción", "Exámenes"],
        row=lambda m: [m.name, _dash(m.description), m.test_count],
        save=svc.save_record, count=_active(Method),
        layout={"name": "col-6", "description": "col-6", "is_active": "col-3"},
        **COMMON, **ADMIN,
    ),
    AuxTable(
        key="opciones", title="Listas de opciones", singular="lista de opciones",
        icon="list", group=GROUP,
        description="Valores de los resultados codificados (NEGATIVO, POSITIVO ++…).",
        form_class=f.OptionSetForm, queryset=q.option_sets,
        get=lambda pk: CodedOptionSet.objects.get(pk=pk), new=CodedOptionSet,
        columns=["Lista", "Código", "Opciones activas", "Parámetros"],
        row=lambda s: [s.name, s.code, s.option_count, s.parameter_count],
        save=svc.save_option_set, count=_active(CodedOptionSet),
        form_kwargs=lambda s: {"code_locked": q.option_set_in_use(option_set=s)},
        formsets=_option_formsets,
        layout={"code": "col-4", "name": "col-6", "is_active": "col-2"},
        **COMMON, **CLINICAL,
    ),
    AuxTable(
        key="observaciones", title="Observaciones generales", singular="observación",
        icon="message-square", group=GROUP,
        description="Observaciones para todos los exámenes o para una sección. Las de un "
                    "examen se editan en su ficha.",
        form_class=f.GeneralObservationForm, queryset=q.general_observations,
        get=lambda pk: ObservationTemplate.objects.get(pk=pk, test__isnull=True),
        new=ObservationTemplate, columns=["Texto", "Alcance", "Orden"],
        row=lambda o: [o.text, o.section.name if o.section_id else "General",
                       o.order_index],
        save=svc.save_record,
        count=lambda: ObservationTemplate.objects.filter(test__isnull=True,
                                                         is_active=True).count(),
        layout={"text": "col-12", "section": "col-4", "order_index": "col-2",
                "is_active": "col-3"},
        **COMMON, **CLINICAL,
    ),
    AuxTable(
        key="tubos", title="Tubos y envases", singular="tubo", icon="test-tube",
        group=GROUP_LAB,
        description="Tubos de toma: color, aditivo y orden de extracción.",
        form_class=f.ContainerForm, queryset=q.containers,
        get=lambda pk: ContainerType.objects.get(pk=pk), new=ContainerType,
        columns=["Tubo", "Código", "Etiqueta", "Aditivo", "Muestra", "Orden", "Exámenes"],
        row=lambda c: [_tube(c), c.code, c.short_name, c.get_additive_display(),
                       c.get_sample_type_display(), c.draw_order, c.test_count],
        save=svc.save_record, count=_active(ContainerType),
        form_kwargs=lambda c: {"code_locked": q.container_in_use(container=c)},
        layout={"code": "col-3", "name": "col-5", "short_name": "col-2", "color": "col-2",
                "additive": "col-3", "sample_type": "col-3", "volume_ml": "col-2",
                "draw_order": "col-2", "max_tests": "col-2", "is_active": "col-3"},
        **COMMON, **ADMIN,
    ),
    AuxTable(
        key="lotes", title="Lotes de reactivos", singular="lote", icon="droplet",
        group=GROUP_LAB,
        description="Lote vigente de cada reactivo con sus datos de cálculo (ISI del INR).",
        form_class=f.LotForm, queryset=q.lots, get=lambda pk: ReagentLot.objects.get(pk=pk),
        new=ReagentLot, columns=["Lote", "Reactivo", "Marca", "ISI", "Vence", "Vigente"],
        row=lambda lot: [lot.lot_number, lot.get_reagent_display(), _dash(lot.brand),
                         _dash(lot.isi), _dash(lot.expires_on and
                                               lot.expires_on.strftime("%d/%m/%Y")),
                         "Vigente" if lot.is_current else "—"],
        save=svc.save_lot, count=_active(ReagentLot),
        layout={"reagent": "col-4", "lot_number": "col-4", "brand": "col-4",
                "isi": "col-3", "expires_on": "col-3", "is_current": "col-4",
                "is_active": "col-2"},
        note="Los resultados ya guardados conservan el lote y el ISI con que se calcularon.",
        can_edit=_roles(*LOT_EDIT_ROLES), editors="Administrador, bioanalista y técnico",
        **COMMON,
    ),
)
