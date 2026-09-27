"""Tubos y envases de toma, y qué tubo necesita cada examen del catálogo base (Fase 09,
ADR-024). Idempotente: crea lo que falta y **nunca** pisa lo que el laboratorio editó; un
examen que ya tiene tubos asignados no se toca.

Regla por defecto según el tipo de muestra del examen (morado = sangre total, rojo =
suero, azul = plasma de coagulación, frascos para orina y heces), con excepciones en
`REQUIREMENT_OVERRIDES`. Cada laboratorio cambia la asignación en el admin (p. ej.
glicemia en tubo gris en vez de rojo).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction

from apps.catalog.models import ContainerType, SampleRequirement, Test

ST = Test.SampleType
AD = ContainerType.Additive


@dataclass(frozen=True)
class C:
    code: str
    name: str
    short_name: str
    color: str
    additive: str
    sample_type: str
    volume_ml: str | None
    draw_order: int


# Orden de extracción CLSI GP41: citrato → suero → heparina → EDTA → fluoruro.
CONTAINERS: tuple[C, ...] = (
    C("AZUL_CITRATO", "Tubo azul (citrato de sodio)", "AZUL", "#2563eb", AD.CITRATO,
      ST.PLASMA, "2.7", 10),
    C("ROJO_SECO", "Tubo rojo (seco)", "ROJO", "#dc2626", AD.NINGUNO, ST.SUERO, "5.0", 20),
    C("AMARILLO_GEL", "Tubo amarillo (gel separador)", "AMARILLO", "#eab308", AD.GEL,
      ST.SUERO, "5.0", 25),
    C("VERDE_HEPARINA", "Tubo verde (heparina)", "VERDE", "#16a34a", AD.HEPARINA,
      ST.PLASMA, "4.0", 30),
    C("MORADO_EDTA", "Tubo morado (EDTA)", "MORADO", "#7c3aed", AD.EDTA, ST.SANGRE_TOTAL,
      "3.0", 40),
    C("GRIS_FLUORURO", "Tubo gris (fluoruro)", "GRIS", "#6b7280", AD.FLUORURO, ST.PLASMA,
      "2.0", 50),
    C("FRASCO_ORINA", "Frasco de orina", "ORINA", "#d97706", AD.NO_APLICA, ST.ORINA,
      None, 80),
    C("ENVASE_ORINA_24H", "Envase de orina de 24 horas", "ORINA 24H", "#b45309",
      AD.NO_APLICA, ST.ORINA_24H, None, 81),
    C("FRASCO_HECES", "Frasco de heces", "HECES", "#78350f", AD.NO_APLICA, ST.HECES,
      None, 82),
)

DEFAULT_BY_SAMPLE_TYPE = {
    ST.SANGRE_TOTAL: "MORADO_EDTA",
    ST.SUERO: "ROJO_SECO",
    ST.PLASMA: "AZUL_CITRATO",  # en el catálogo base, todo el plasma es coagulación
    ST.ORINA: "FRASCO_ORINA",
    ST.ORINA_24H: "ENVASE_ORINA_24H",
    ST.HECES: "FRASCO_HECES",
}

POST_PRANDIAL = "Post-prandial 2 h"
POST_CARGA = "Post-carga 2 h"

# (tubo, toma, tubo propio) por examen, cuando la regla por defecto no alcanza.
REQUIREMENT_OVERRIDES: dict[str, tuple[tuple[str, str, bool], ...]] = {
    # Orina de 24 h + creatinina sérica (comparte el tubo rojo con la química).
    "DEPURACION": (("ENVASE_ORINA_24H", "", False), ("ROJO_SECO", "", False)),
    # Tomas por tiempo: tubo aparte del basal, compartido entre glicemia e insulina.
    "GLICEMIA_PP": (("ROJO_SECO", POST_PRANDIAL, False),),
    "INSULINA_PP": (("ROJO_SECO", POST_PRANDIAL, False),),
    "GLICEMIA_POST_CARGA": (("ROJO_SECO", POST_CARGA, False),),
    "INSULINA_POST_CARGA": (("ROJO_SECO", POST_CARGA, False),),
}


def seed_container_types() -> dict[str, ContainerType]:
    containers = {}
    for spec in CONTAINERS:
        containers[spec.code], _ = ContainerType.objects.get_or_create(
            code=spec.code,
            defaults={
                "name": spec.name, "short_name": spec.short_name, "color": spec.color,
                "additive": spec.additive, "sample_type": spec.sample_type,
                "volume_ml": Decimal(spec.volume_ml) if spec.volume_ml else None,
                "draw_order": spec.draw_order,
            },
        )
    return containers


def _requirements_for(test: Test) -> tuple[tuple[str, str, bool], ...]:
    if test.code in REQUIREMENT_OVERRIDES:
        return REQUIREMENT_OVERRIDES[test.code]
    default = DEFAULT_BY_SAMPLE_TYPE.get(test.sample_type)
    return ((default, "", False),) if default else ()


@transaction.atomic
def seed_containers() -> None:
    """Siembra los tubos y asigna tubo a cada examen que todavía no tiene. Debe correr
    dentro del esquema del tenant."""
    containers = seed_container_types()
    tests = Test.objects.filter(sample_requirements__isnull=True)
    for test in tests:
        for index, (code, label, own) in enumerate(_requirements_for(test)):
            SampleRequirement.objects.create(
                test=test, container_type=containers[code], collection_label=label,
                own_container=own, order_index=index,
            )
