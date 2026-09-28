"""Pantallas de las tablas auxiliares (Fase 11d). Sólo orquestan: la consulta, los
permisos y el guardado los aporta cada app en su `AuxTable`."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import redirect, render

from apps.core.aux_tables import get_table, visible_tables
from apps.core.exceptions import ApplicationError


def _table(request, key):
    table = get_table(key)
    if table is None:
        raise Http404("Tabla no encontrada.")
    if not table.can_view(request.user):
        raise PermissionDenied("Su rol no puede consultar esta tabla.")
    return table


@login_required
def hub(request):
    groups = visible_tables(request.user)
    if not groups:
        raise PermissionDenied("Su rol no puede consultar las tablas auxiliares.")
    return render(request, "core/tablas/hub.html", {"groups": groups})


@login_required
def table_list(request, key):
    table = _table(request, key)
    show_inactive, query = request.GET.get("inactivos") == "1", request.GET.get("q", "")
    rows = [(obj, table.row(obj)) for obj in table.queryset(show_inactive=show_inactive,
                                                             query=query)]
    return render(request, "core/tablas/list.html", {
        "table": table, "rows": rows, "show_inactive": show_inactive, "query": query,
        "can_edit": table.can_edit(request.user),
    })


def _forms(table, request, instance):
    data = request.POST if request.method == "POST" else None
    files = request.FILES if request.method == "POST" else None
    form = table.form_class(data, files, instance=instance, **table.form_kwargs(instance))
    return form, table.formsets(data, instance)


@login_required
def table_edit(request, key, pk=None):
    table = _table(request, key)
    can_edit = table.can_edit(request.user)
    if pk is None and not (can_edit and table.allow_new):
        raise PermissionDenied("Su rol no puede crear registros en esta tabla.")
    try:
        instance = table.get(pk) if pk else table.new()
    except (ObjectDoesNotExist, ValidationError) as exc:
        raise Http404("No encontrado.") from exc
    form, formsets = _forms(table, request, instance)
    if not can_edit:
        for item in [form, *[fs for _, fs, _ in formsets]]:
            for f in getattr(item, "forms", [item]):
                for bound in f.fields.values():
                    bound.disabled = True
    if request.method == "POST":
        if not can_edit:
            raise PermissionDenied("Su rol no puede editar esta tabla.")
        if form.is_valid() and all(fs.is_valid() for _, fs, _ in formsets):
            try:
                saved = table.save(form=form, formsets=[fs for _, fs, _ in formsets],
                                   by=request.user)
            except ApplicationError as exc:
                messages.error(request, exc.message)
            else:
                messages.success(request, f"Guardado: {saved}.")
                return redirect("core:aux-edit", key=table.key, pk=saved.pk)
    return render(request, "core/tablas/edit.html", {
        "table": table, "obj": instance if pk else None, "form": form,
        "formsets": formsets, "can_edit": can_edit, "fields": _layout(table, form),
    })


def _layout(table, form):
    """(campo, columnas, es_casilla) en el orden del formulario."""
    return [(bound, table.layout.get(bound.name, "col-4"),
             getattr(bound.field.widget, "input_type", "") == "checkbox")
            for bound in form.visible_fields()]
