"""Alta y edición de perfiles (agrupaciones nombradas de exámenes)."""
from collections.abc import Sequence

from django.db import transaction

from apps.catalog.models import Profile, ProfileTest, Test
from apps.catalog.selectors.catalog_queries import calculation_input_tests
from apps.core.exceptions import ApplicationError


@transaction.atomic
def set_profile_tests(
    *, profile: Profile, tests: Sequence[Test], allow_incomplete: bool = False
) -> Profile:
    """Reemplaza la composición del perfil respetando el orden de `tests`.

    Rechaza perfiles vacíos, exámenes repetidos o inactivos y — salvo
    `allow_incomplete=True` — perfiles donde un parámetro calculado no tendría sus
    insumos (p. ej. ÍNDICES DE CASTELLI sin HDL)."""
    if not tests:
        raise ApplicationError(f"El perfil {profile.code} debe tener al menos un examen.")
    codes = [t.code for t in tests]
    duplicated = sorted({c for c in codes if codes.count(c) > 1})
    if duplicated:
        raise ApplicationError("Exámenes repetidos en el perfil: " + ", ".join(duplicated))
    inactive = sorted(t.code for t in tests if not t.is_active)
    if inactive:
        raise ApplicationError("Exámenes inactivos en el perfil: " + ", ".join(inactive))
    if not allow_incomplete:
        missing = calculation_input_tests(tests=tests)
        if missing:
            raise ApplicationError(
                f"Al perfil {profile.code} le faltan exámenes que alimentan sus cálculos: "
                + ", ".join(sorted(t.code for t in missing)),
                extra={"missing": sorted(t.code for t in missing)},
            )

    profile.profile_tests.all().delete()
    ProfileTest.objects.bulk_create(
        [
            ProfileTest(profile=profile, test=test, order_index=index)
            for index, test in enumerate(tests, start=1)
        ]
    )
    return profile


@transaction.atomic
def create_profile(
    *,
    code: str,
    name: str,
    tests: Sequence[Test],
    description: str = "",
    order_index: int = 0,
    allow_incomplete: bool = False,
) -> Profile:
    if Profile.objects.filter(code=code).exists():
        raise ApplicationError(f"Ya existe un perfil con el código {code}.")
    profile = Profile.objects.create(
        code=code, name=name, description=description, order_index=order_index
    )
    return set_profile_tests(profile=profile, tests=tests, allow_incomplete=allow_incomplete)
