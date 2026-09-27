"""Agrupación de exámenes en tubos (ADR-024).

Reglas:
1. Cada examen pide uno o más tubos (`SampleRequirement`).
2. Los pedidos con el mismo tubo y la misma toma (`collection_label`) comparten tubo.
3. Van aparte: `own_container` (tubo propio) y lo que exceda `ContainerType.max_tests`.
4. Al agregar exámenes a una orden, se reutiliza un tubo **por tomar** compatible; si ya
   se tomó, se crea uno nuevo.
5. Los tubos nuevos se numeran en el orden de extracción (azul → rojo → … → frascos).

`plan_tubes()` es pura (sin base de datos) y la usa también la vista previa de la orden.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from apps.catalog.selectors.catalog_queries import sample_requirements_by_test
from apps.orders.models import Order, OrderItem, Sample
from apps.orders.services.numbering import sample_identifiers


@dataclass(frozen=True)
class TubeNeed:
    """Un examen necesita este tubo (con esta toma)."""

    item_key: object  # OrderItem o código del examen en la vista previa
    container_type: object  # catalog.ContainerType
    collection_label: str = ""
    own_container: bool = False


@dataclass
class PlannedTube:
    container_type: object
    collection_label: str = ""
    exclusive: bool = False
    item_keys: list = field(default_factory=list)
    existing: object = None  # Sample ya guardada que se reutiliza

    def accepts(self, need: TubeNeed) -> bool:
        if self.exclusive or need.own_container:
            return False
        if self.container_type.pk != need.container_type.pk:
            return False
        if self.collection_label != need.collection_label:
            return False
        limit = self.container_type.max_tests
        return not limit or len(self.item_keys) < limit


def plan_tubes(needs: Iterable[TubeNeed], *, existing: Sequence[PlannedTube] = ()) -> list[
    PlannedTube
]:
    """Reparte las necesidades en tubos. `existing` son tubos por tomar reutilizables."""
    tubes = list(existing)
    for need in needs:
        tube = next((t for t in tubes if t.accepts(need)), None)
        if tube is None:
            tube = PlannedTube(container_type=need.container_type,
                               collection_label=need.collection_label,
                               exclusive=need.own_container)
            tubes.append(tube)
        tube.item_keys.append(need.item_key)
    return tubes


def draw_order_key(tube: PlannedTube) -> tuple:
    ct = tube.container_type
    return (ct.draw_order, ct.name, tube.collection_label)


def needs_for_tests(tests_with_keys: Iterable[tuple[object, object]]) -> tuple[
    list[TubeNeed], list[str]
]:
    """[(clave, Test)] → necesidades de tubo y avisos de exámenes sin tubo asignado."""
    pairs = list(tests_with_keys)
    requirements = sample_requirements_by_test(tests=[test for _, test in pairs])
    needs, warnings = [], []
    for key, test in pairs:
        test_requirements = requirements.get(test.id, [])
        if not test_requirements:
            warnings.append(
                f"{test.name} no tiene tubo asignado en el catálogo: no se generó etiqueta."
            )
        for requirement in test_requirements:
            needs.append(TubeNeed(
                item_key=key, container_type=requirement.container_type,
                collection_label=requirement.collection_label,
                own_container=requirement.own_container,
            ))
    return needs, warnings


def assign_samples(*, order: Order, items: Sequence[OrderItem], created_by=None) -> list[str]:
    """Crea (o reutiliza) las muestras de `items` en la orden. Devuelve avisos."""
    needs, warnings = needs_for_tests((item, item.test) for item in items)
    open_samples = list(
        order.samples.filter(status=Sample.Status.PENDIENTE)
        .select_related("container_type").prefetch_related("order_items")
    )
    existing = [
        PlannedTube(container_type=s.container_type, collection_label=s.collection_label,
                    exclusive=s.is_exclusive, item_keys=list(s.order_items.all()),
                    existing=s)
        for s in open_samples
    ]
    before = {id(t): len(t.item_keys) for t in existing}
    tubes = plan_tubes(needs, existing=existing)

    next_sequence = (order.samples.order_by("-sequence")
                     .values_list("sequence", flat=True).first() or 0) + 1
    for tube in sorted(tubes, key=draw_order_key):
        if tube.existing is not None:
            added = tube.item_keys[before[id(tube)]:]
            if added:
                tube.existing.order_items.add(*added)
            continue
        number, barcode = sample_identifiers(order_number=order.number,
                                             sequence=next_sequence)
        sample = Sample.objects.create(
            order=order, sequence=next_sequence, number=number, barcode=barcode,
            container_type=tube.container_type, collection_label=tube.collection_label,
            is_exclusive=tube.exclusive, created_by=created_by,
        )
        sample.order_items.add(*tube.item_keys)
        next_sequence += 1
    return warnings
