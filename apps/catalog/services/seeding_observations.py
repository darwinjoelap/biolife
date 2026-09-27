"""Observaciones predefinidas (Fase 10, ADR-025), de `04_HALLAZGOS_FORMATOS.md` §9 más
algunas de uso general. Idempotente: crea las que faltan por texto y alcance; nunca borra
ni modifica las del laboratorio."""
from apps.catalog.models import ObservationTemplate, Section, Test

# (código de sección o None = general, código de examen o None, texto)
TEMPLATES: tuple[tuple[str | None, str | None, str], ...] = (
    (None, None, "VALOR VERIFICADO"),
    (None, None, "VALORES VERIFICADOS"),
    (None, None, "MUESTRA REPETIDA PARA CONFIRMAR EL RESULTADO"),
    ("HEMATOLOGIA", "HEM_COMP", "HEMATOLOGÍA COMPLETA VERIFICADA MEDIANTE TÉCNICA MANUAL"),
    ("HEMATOLOGIA", "HEM_COMP", "HEMATOLOGÍA COMPLETA VERIFICADA CON UNA SEGUNDA MUESTRA"),
    ("HEMATOLOGIA", "HEM_COMP", "CONTAJE Y FÓRMULA LEUCOCITARIA VERIFICADOS"),
    ("HEMATOLOGIA", "HEM_COMP", "CONTAJE PLAQUETARIO VERIFICADO"),
    ("QUIMICA_SANGUINEA", None, "SUERO ICTÉRICO"),
    ("QUIMICA_SANGUINEA", None, "SUERO LIPÉMICO"),
    ("QUIMICA_SANGUINEA", None, "SUERO HEMOLIZADO"),
    ("ORINA", "URO", "SE SUGIERE REPETIR UROANÁLISIS MEJORANDO LA TOMA DE MUESTRA"),
    ("ORINA", "URO", "HEMATÍES: EUMÓRFICOS __ % / DISMÓRFICOS __ %"),
    ("HECES", None, "SE SUGIERE REALIZAR EXAMEN DE HECES SERIADO"),
    ("SEROLOGIA", None, "SE SUGIERE REALIZAR β-HCG CUANTIFICADA"),
    ("SEROLOGIA", "VDRL", "SE SUGIERE CONFIRMAR RESULTADO MEDIANTE FTA-Abs"),
    ("HEMATOLOGIA", "GRUPO_SANGUINEO", "SE SUGIERE CONFIRMAR FACTOR Rh MEDIANTE Du"),
)


def seed_observation_templates() -> int:
    sections = {s.code: s for s in Section.objects.all()}
    tests = {t.code: t for t in Test.objects.all()}
    created = 0
    for index, (section_code, test_code, text) in enumerate(TEMPLATES):
        test = tests.get(test_code) if test_code else None
        section = None if test else sections.get(section_code) if section_code else None
        if (test_code and test is None) or (section_code and not test and section is None):
            continue  # el laboratorio no tiene ese examen/sección
        _, was_created = ObservationTemplate.objects.get_or_create(
            text=text, test=test, section=section, defaults={"order_index": index},
        )
        created += was_created
    return created
