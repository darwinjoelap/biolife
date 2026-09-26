"""Siembra de exámenes mínimos + rangos de referencia para la Fase 06. Sólo lo necesario
para ejercitar los 6 `range_type` con datos reales de `docs/04_HALLAZGOS_FORMATOS.md` —
no es el catálogo completo de cada examen (eso se completa fase a fase, igual que
Uroanálisis en la Fase 05).

Idempotente: todo se crea con `get_or_create` por campos naturales (nunca por PK, que es
un UUID generado).

**Rangos marcados "PENDIENTE DE CONFIRMAR" abajo** corresponden a los 6 parámetros que
`docs/04_HALLAZGOS_FORMATOS.md` reporta con dos valores distintos según la hoja del
formato actual (glicemia, úrea, creatinina, ácido úrico, bilirrubina total y directa).
Angelus no ha confirmado cuál es el correcto — se sembró uno de los dos, documentado en
`docs/roadmap/06_rangos_de_referencia.md`. **No usar en un informe real sin confirmación.**

**El rango de GLÓBULOS BLANCOS para recién nacido está marcado "NO CONFIRMADO"** — es
ilustrativo, sólo para demostrar que el resolver filtra por edad en días; los rangos
pediátricos/neonatales reales son una pregunta abierta al laboratorio (ver
`docs/ESTADO.md`).
"""
from decimal import Decimal

from apps.catalog.models import (
    CodedOption,
    Parameter,
    ParameterGroup,
    ReferenceRange,
    Section,
    Test,
    Unit,
)
from apps.core.exceptions import ApplicationError

DIAS_POR_ANO = 365
EDAD_MAXIMA_DIAS = 54750  # ~150 años, igual que el default del modelo


def _parametro(
    *, test: Test, code: str, name: str, value_type: str, unit: Unit | None = None,
    formula: str = "", decimals: int = 2, order_index: int = 0,
    group: ParameterGroup | None = None,
) -> Parameter:
    parameter, _ = Parameter.objects.get_or_create(
        code=code,
        defaults={
            "test": test, "group": group, "name": name, "value_type": value_type,
            "unit": unit, "formula": formula, "decimals": decimals,
            "order_index": order_index,
        },
    )
    return parameter


def _rango(
    *, parameter: Parameter, range_type: str, display_text: str,
    sex: str = ReferenceRange.Sex.ANY, age_min_days: int = 0,
    age_max_days: int = EDAD_MAXIMA_DIAS,
    condition: str = ReferenceRange.Condition.NINGUNA,
    low: Decimal | None = None, high: Decimal | None = None,
    center: Decimal | None = None, tolerance: Decimal | None = None,
    expected_option: CodedOption | None = None, bands: list | None = None,
    unit: Unit | None = None, priority: int = 0,
) -> ReferenceRange:
    reference_range, _ = ReferenceRange.objects.get_or_create(
        parameter=parameter, sex=sex, age_min_days=age_min_days, age_max_days=age_max_days,
        condition=condition, range_type=range_type,
        defaults={
            "display_text": display_text, "low": low, "high": high, "center": center,
            "tolerance": tolerance, "expected_option": expected_option, "bands": bands,
            "unit": unit, "priority": priority,
        },
    )
    return reference_range


def seed_hematologia() -> Test:
    section, _ = Section.objects.get_or_create(
        code="HEMATOLOGIA", defaults={"name": "HEMATOLOGÍA", "order_index": 10}
    )
    test, _ = Test.objects.get_or_create(
        code="HEM_COMP",
        defaults={
            "name": "HEMATOLOGÍA COMPLETA", "section": section, "sample_type": "SANGRE_TOTAL",
        },
    )
    unit_g_dl, _ = Unit.objects.get_or_create(symbol="g/dL")
    unit_pct, _ = Unit.objects.get_or_create(symbol="%")
    unit_mm3, _ = Unit.objects.get_or_create(symbol="/mm3")

    hemoglobina = _parametro(
        test=test, code="HEM_HEMOGLOBINA", name="HEMOGLOBINA",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_g_dl, decimals=1, order_index=1,
    )
    hematocrito = _parametro(
        test=test, code="HEM_HEMATOCRITO", name="HEMATOCRITO",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_pct, decimals=0, order_index=2,
    )
    globulos_blancos = _parametro(
        test=test, code="HEM_GLOBULOS_BLANCOS", name="GLÓBULOS BLANCOS",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_mm3, decimals=0, order_index=3,
    )

    # Sexo: el formato actual de Angelus usa 13,0-15,0 para ambos sexos. El propio
    # 04_HALLAZGOS_FORMATOS.md señala que eso es clínicamente incorrecto y da el valor
    # femenino correcto (12,0-16,0) — se siembran ambos, cada uno confirmado/justificado
    # por el documento de hallazgos.
    _rango(
        parameter=hemoglobina, range_type=ReferenceRange.RangeType.CLOSED,
        display_text="13,0 - 15,0 g/dL", sex=ReferenceRange.Sex.M,
        low=Decimal("13.0"), high=Decimal("15.0"), unit=unit_g_dl,
    )
    _rango(
        parameter=hemoglobina, range_type=ReferenceRange.RangeType.CLOSED,
        display_text="12,0 - 16,0 g/dL", sex=ReferenceRange.Sex.F,
        low=Decimal("12.0"), high=Decimal("16.0"), unit=unit_g_dl,
    )
    _rango(
        parameter=hematocrito, range_type=ReferenceRange.RangeType.CLOSED,
        display_text="41 - 50 %", low=Decimal("41"), high=Decimal("50"), unit=unit_pct,
    )

    # Edad: recién nacido (0-28 días) vs. el resto. El valor de recién nacido es
    # ilustrativo/NO CONFIRMADO (ver docstring del módulo); el del resto sí es el
    # confirmado en 04_HALLAZGOS_FORMATOS.md.
    _rango(
        parameter=globulos_blancos, range_type=ReferenceRange.RangeType.CLOSED,
        display_text="9.000 - 30.000/mm3 (NO CONFIRMADO)",
        age_min_days=0, age_max_days=28,
        low=Decimal("9000"), high=Decimal("30000"), unit=unit_mm3, priority=1,
    )
    _rango(
        parameter=globulos_blancos, range_type=ReferenceRange.RangeType.CLOSED,
        display_text="4.500 - 10.000/mm3",
        age_min_days=29, age_max_days=EDAD_MAXIMA_DIAS,
        low=Decimal("4500"), high=Decimal("10000"), unit=unit_mm3,
    )
    return test


def seed_perfil_lipidico() -> Test:
    section, _ = Section.objects.get_or_create(
        code="QUIMICA_SANGUINEA", defaults={"name": "QUÍMICA SANGUÍNEA", "order_index": 20}
    )
    test, _ = Test.objects.get_or_create(
        code="PERFIL_LIPIDICO",
        defaults={
            "name": "PERFIL LIPÍDICO", "section": section, "sample_type": "SUERO",
            "requires_fasting": True,
        },
    )
    unit_mg_dl, _ = Unit.objects.get_or_create(symbol="mg/dL")

    colesterol = _parametro(
        test=test, code="LIP_COLESTEROL_TOTAL", name="COLESTEROL TOTAL",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_mg_dl, decimals=0, order_index=1,
    )
    hdl = _parametro(
        test=test, code="LIP_HDL", name="HDL-c",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_mg_dl, decimals=0, order_index=2,
    )
    trigliceridos = _parametro(
        test=test, code="LIP_TRIGLICERIDOS", name="TRIGLICÉRIDOS",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_mg_dl, decimals=0, order_index=3,
    )

    _rango(
        parameter=colesterol, range_type=ReferenceRange.RangeType.UPPER_BOUND,
        display_text="MENOR A 200 mg/dL", condition=ReferenceRange.Condition.AYUNO,
        high=Decimal("200"), unit=unit_mg_dl,
    )
    _rango(
        parameter=hdl, range_type=ReferenceRange.RangeType.LOWER_BOUND,
        display_text="MAYOR 40 mg/dL", condition=ReferenceRange.Condition.AYUNO,
        low=Decimal("40"), unit=unit_mg_dl,
    )
    _rango(
        parameter=trigliceridos, range_type=ReferenceRange.RangeType.UPPER_BOUND,
        display_text="MENOR A 150 mg/dL", condition=ReferenceRange.Condition.AYUNO,
        high=Decimal("150"), unit=unit_mg_dl,
    )
    return test


def seed_coagulacion() -> Test:
    section, _ = Section.objects.get_or_create(
        code="COAGULACION", defaults={"name": "COAGULACIÓN", "order_index": 40}
    )
    test, _ = Test.objects.get_or_create(
        code="COAGUL",
        defaults={"name": "COAGULACIÓN", "section": section, "sample_type": "PLASMA"},
    )
    unit_seg, _ = Unit.objects.get_or_create(symbol="seg")

    _parametro(
        test=test, code="COAG_PTT_PACIENTE", name="PTT PACIENTE",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_seg, decimals=1, order_index=1,
    )
    _parametro(
        test=test, code="COAG_PTT_CONTROL", name="PTT CONTROL",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_seg, decimals=1, order_index=2,
    )
    ptt_diferencia = _parametro(
        test=test, code="COAG_PTT_DIFERENCIA", name="DIFERENCIA PTT (paciente - control)",
        value_type=Parameter.ValueType.NUMERIC_CALCULATED, unit=unit_seg, decimals=1,
        formula="COAG_PTT_PACIENTE - COAG_PTT_CONTROL", order_index=3,
    )

    _rango(
        parameter=ptt_diferencia, range_type=ReferenceRange.RangeType.TOLERANCE,
        display_text="± 6,0 segundos", center=Decimal("0"), tolerance=Decimal("6.0"),
        unit=unit_seg,
    )
    return test


def seed_quimica_sanguinea() -> Test:
    section, _ = Section.objects.get_or_create(
        code="QUIMICA_SANGUINEA", defaults={"name": "QUÍMICA SANGUÍNEA", "order_index": 20}
    )
    test, _ = Test.objects.get_or_create(
        code="QUIM",
        defaults={"name": "QUÍMICA SANGUÍNEA", "section": section, "sample_type": "SUERO"},
    )
    unit_mg_dl, _ = Unit.objects.get_or_create(symbol="mg/dL")
    unit_ng_ml, _ = Unit.objects.get_or_create(symbol="ng/mL")

    glicemia = _parametro(
        test=test, code="QUIM_GLICEMIA", name="GLICEMIA",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_mg_dl, decimals=0, order_index=1,
    )
    urea = _parametro(
        test=test, code="QUIM_UREA", name="ÚREA",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_mg_dl, decimals=0, order_index=2,
    )
    creatinina = _parametro(
        test=test, code="QUIM_CREATININA", name="CREATININA",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_mg_dl, decimals=2, order_index=3,
    )
    acido_urico = _parametro(
        test=test, code="QUIM_ACIDO_URICO", name="ÁCIDO ÚRICO",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_mg_dl, decimals=1, order_index=4,
    )
    bilirrubina_total = _parametro(
        test=test, code="QUIM_BILIRRUBINA_TOTAL", name="BILIRRUBINA TOTAL",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_mg_dl, decimals=2, order_index=5,
    )
    bilirrubina_directa = _parametro(
        test=test, code="QUIM_BILIRRUBINA_DIRECTA", name="BILIRRUBINA DIRECTA",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_mg_dl, decimals=2, order_index=6,
    )
    procalcitonina = _parametro(
        test=test, code="QUIM_PROCALCITONINA", name="PROCALCITONINA",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_ng_ml, decimals=2, order_index=7,
    )

    # PENDIENTE DE CONFIRMAR (ver docstring del módulo y docs/roadmap/06_...md): estos 6
    # parámetros traen dos valores distintos según la hoja del formato actual de Angelus.
    _rango(
        parameter=glicemia, range_type=ReferenceRange.RangeType.CLOSED,
        display_text="70 - 100 mg/dL (PENDIENTE DE CONFIRMAR)",
        low=Decimal("70"), high=Decimal("100"), unit=unit_mg_dl,
    )
    _rango(
        parameter=urea, range_type=ReferenceRange.RangeType.CLOSED,
        display_text="20 - 45 mg/dL (PENDIENTE DE CONFIRMAR)",
        low=Decimal("20"), high=Decimal("45"), unit=unit_mg_dl,
    )
    _rango(
        parameter=creatinina, range_type=ReferenceRange.RangeType.CLOSED,
        display_text="0,70 - 1,20 mg/dL (PENDIENTE DE CONFIRMAR)",
        low=Decimal("0.70"), high=Decimal("1.20"), unit=unit_mg_dl,
    )
    _rango(
        parameter=acido_urico, range_type=ReferenceRange.RangeType.CLOSED,
        display_text="3,0 - 7,0 mg/dL (PENDIENTE DE CONFIRMAR)",
        low=Decimal("3.0"), high=Decimal("7.0"), unit=unit_mg_dl,
    )
    _rango(
        parameter=bilirrubina_total, range_type=ReferenceRange.RangeType.CLOSED,
        display_text="0,10 - 1,20 mg/dL (PENDIENTE DE CONFIRMAR)",
        low=Decimal("0.10"), high=Decimal("1.20"), unit=unit_mg_dl,
    )
    _rango(
        parameter=bilirrubina_directa, range_type=ReferenceRange.RangeType.CLOSED,
        display_text="0,05 - 0,30 mg/dL (PENDIENTE DE CONFIRMAR)",
        low=Decimal("0.05"), high=Decimal("0.30"), unit=unit_mg_dl,
    )
    # Confirmado: bandas literales de 04_HALLAZGOS_FORMATOS.md sección 7.
    _rango(
        parameter=procalcitonina, range_type=ReferenceRange.RangeType.INTERPRETIVE,
        display_text="Interpretación según banda (ver 'bands')",
        bands=[
            {"max": 0.5, "text": "Posible infección localizada."},
            {"min": 0.5, "text": "Posible infección sistémica."},
            {"min": 2.0, "text": "Probable infección sistémica (sepsis)."},
            {"min": 10.0, "text": "Alta probabilidad de shock séptico."},
        ],
        unit=unit_ng_ml,
    )
    return test


def seed_reference_ranges() -> None:
    """Siembra los 4 exámenes mínimos de la Fase 06 y sus `ReferenceRange`, más el
    `ReferenceRange` cualitativo sobre `URO_NITRITOS` (Fase 05) — cubriendo los 6
    `range_type`. Idempotente. Debe llamarse dentro del `schema_context()` del tenant, y
    después de haber corrido `seed_uroanalisis()` (Fase 05) al menos una vez."""
    seed_hematologia()
    seed_perfil_lipidico()
    seed_coagulacion()
    seed_quimica_sanguinea()

    try:
        nitritos = Parameter.objects.get(code="URO_NITRITOS")
        negativo = CodedOption.objects.get(option_set__code="NEG_POS", value="NEGATIVO")
    except (Parameter.DoesNotExist, CodedOption.DoesNotExist) as exc:
        raise ApplicationError(
            "seed_reference_ranges() requiere que seed_uroanalisis() (Fase 05) ya haya "
            "corrido en este tenant — no se encontró URO_NITRITOS o su opción NEGATIVO."
        ) from exc

    _rango(
        parameter=nitritos, range_type=ReferenceRange.RangeType.QUALITATIVE,
        display_text="NEGATIVO", expected_option=negativo,
    )
