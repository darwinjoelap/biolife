"""Consultas públicas del catálogo. Otras apps (billing, orders) leen el catálogo por
aquí, no importando modelos de `apps.catalog` directamente (CLAUDE.md, regla 3)."""
from collections.abc import Iterable

from django.db.models import Prefetch, Q, QuerySet

from apps.catalog.models import (
    ContainerType,
    Parameter,
    Profile,
    ProfileTest,
    SampleRequirement,
    Test,
)


def active_profiles() -> list[Profile]:
    """Perfiles activos con sus exámenes precargados, en orden de presentación."""
    return list(
        Profile.objects.filter(is_active=True).prefetch_related(
            Prefetch(
                "profile_tests",
                queryset=ProfileTest.objects.select_related("test").order_by("order_index"),
            )
        )
    )


def profile_tests(*, profile: Profile) -> list[Test]:
    """Exámenes de un perfil, en el orden definido por el laboratorio."""
    return [
        pt.test
        for pt in profile.profile_tests.select_related("test", "test__section").order_by(
            "order_index"
        )
    ]


def tests_by_codes(*, codes: Iterable[str]) -> dict[str, Test]:
    return {t.code: t for t in Test.objects.filter(code__in=list(codes))}


def profiles_by_codes(*, codes: Iterable[str]) -> dict[str, Profile]:
    return {p.code: p for p in Profile.objects.filter(code__in=list(codes))}


def calculation_input_tests(*, tests: Iterable[Test]) -> set[Test]:
    """Exámenes que faltan para poder calcular los parámetros calculados de `tests`.

    Recorre `depends_on` transitivamente (LDL → VLDL → TRIGLICÉRIDOS) y devuelve los
    exámenes dueños de esos insumos que **no** están en `tests`. Vacío = el conjunto es
    autosuficiente. Las variables de la orden (`{@peso}`, `{@isi}`) no cuentan aquí."""
    test_ids = {t.id for t in tests}
    pending = list(
        Parameter.objects.filter(
            test_id__in=test_ids, value_type=Parameter.ValueType.NUMERIC_CALCULATED
        ).prefetch_related("depends_on")
    )
    seen: set = set()
    missing_test_ids: set = set()
    while pending:
        parameter = pending.pop()
        if parameter.id in seen:
            continue
        seen.add(parameter.id)
        for dependency in parameter.depends_on.all():
            if dependency.test_id not in test_ids:
                missing_test_ids.add(dependency.test_id)
            if dependency.value_type == Parameter.ValueType.NUMERIC_CALCULATED:
                pending.append(
                    Parameter.objects.prefetch_related("depends_on").get(pk=dependency.pk)
                )
    return set(Test.objects.filter(id__in=missing_test_ids))


def sample_requirements_by_test(*, tests: Iterable[Test]) -> dict:
    """{test_id: [SampleRequirement...]} con su tubo precargado (Fase 09)."""
    result: dict = {}
    requirements = (
        SampleRequirement.objects.filter(
            test_id__in=[t.id for t in tests], is_active=True,
            container_type__is_active=True,
        )
        .select_related("container_type")
        .order_by("order_index")
    )
    for requirement in requirements:
        result.setdefault(requirement.test_id, []).append(requirement)
    return result


def container_types() -> list[ContainerType]:
    return list(ContainerType.objects.filter(is_active=True))


def search_orderables(*, query: str, limit: int = 12) -> tuple[list[Profile], list[Test]]:
    """Perfiles y exámenes activos cuyo código o nombre contiene `query`."""
    query = query.strip()
    if not query:
        return [], []
    match = Q(code__icontains=query) | Q(name__icontains=query)
    profiles = list(Profile.objects.filter(match, is_active=True)[:limit])
    tests = list(
        Test.objects.filter(match, is_active=True).select_related("section")[:limit]
    )
    return profiles, tests


def active_tests_by_ids(*, ids: Iterable) -> list[Test]:
    return list(Test.objects.filter(id__in=list(ids), is_active=True))


def active_profiles_by_ids(*, ids: Iterable) -> list[Profile]:
    return list(Profile.objects.filter(id__in=list(ids), is_active=True))


def orderable_tests() -> QuerySet[Test]:
    return Test.objects.filter(is_active=True)


def orderable_profiles() -> QuerySet[Profile]:
    return Profile.objects.filter(is_active=True)
