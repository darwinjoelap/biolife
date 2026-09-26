"""Siembra del catálogo de exámenes. Fase 05: sólo Uroanálisis, como prueba de concepto
del motor de catálogo (Section/Unit/Method/Test/ParameterGroup/Parameter/CodedOptionSet/
CodedOption). El resto de los exámenes reales de Angelus se siembra fase a fase, ligado a
cuando se necesiten (rangos de referencia, fórmulas, perfiles).

Idempotente: todo se crea con `get_or_create` por el campo `code`/`value` natural de cada
modelo — nunca por PK, que es un UUID generado y no sirve como clave de idempotencia.

**Parámetros marcados "NO CONFIRMADO" abajo no vienen de los formatos reales de Angelus**
(`docs/04_HALLAZGOS_FORMATOS.md`). Se agregaron únicamente para que el Uroanálisis
ejercite los 9 `value_type` del catálogo (decisión tomada con Darwin al iniciar la Fase 05,
ver `docs/roadmap/05_catalogo_examenes.md`). No deben imprimirse en un informe real hasta
que el laboratorio los confirme.
"""
from decimal import Decimal

from apps.catalog.models import (
    CodedOption,
    CodedOptionSet,
    Parameter,
    ParameterGroup,
    Section,
    Test,
    Unit,
)


def _get_or_create_option_set(*, code: str, name: str, options: list[dict]) -> CodedOptionSet:
    option_set, _ = CodedOptionSet.objects.get_or_create(code=code, defaults={"name": name})
    for option in options:
        CodedOption.objects.get_or_create(
            option_set=option_set,
            value=option["value"],
            defaults={
                "ordinal": option.get("ordinal"),
                "numeric_equivalent": option.get("numeric_equivalent"),
                "is_pathological": option.get("is_pathological", False),
                "order_index": option.get("ordinal") or 0,
            },
        )
    return option_set


def _get_or_create_parameter(
    *,
    test: Test,
    group: ParameterGroup,
    code: str,
    name: str,
    value_type: str,
    order_index: int,
    unit: Unit | None = None,
    option_set: CodedOptionSet | None = None,
    formula: str = "",
    decimals: int = 2,
) -> Parameter:
    parameter, _ = Parameter.objects.get_or_create(
        code=code,
        defaults={
            "test": test,
            "group": group,
            "name": name,
            "value_type": value_type,
            "unit": unit,
            "option_set": option_set,
            "formula": formula,
            "decimals": decimals,
            "order_index": order_index,
        },
    )
    return parameter


def seed_uroanalisis() -> Test:
    """Crea (o recupera, si ya existe) el examen URO con sus 3 grupos y sus 25
    parámetros — cubriendo los 9 `value_type` del catálogo. Debe llamarse dentro del
    `schema_context()` del tenant."""
    section, _ = Section.objects.get_or_create(
        code="ORINA", defaults={"name": "ORINA", "order_index": 30}
    )

    unit_mg_dl, _ = Unit.objects.get_or_create(symbol="mg/dL")
    unit_mg_g, _ = Unit.objects.get_or_create(symbol="mg/g")  # NO CONFIRMADO
    unit_p_campo, _ = Unit.objects.get_or_create(
        symbol="P/C", defaults={"description": "por campo"}
    )

    color_orina = _get_or_create_option_set(
        code="COLOR_ORINA", name="Color de orina",
        options=[
            {"value": "AMARILLO", "ordinal": 0},
            {"value": "TRANSPARENTE", "ordinal": 1},
            {"value": "CLARO", "ordinal": 2},
            {"value": "ÁMBAR", "ordinal": 3},
            {"value": "ROJO", "ordinal": 4, "is_pathological": True},
        ],
    )
    aspecto_orina = _get_or_create_option_set(
        code="ASPECTO_ORINA", name="Aspecto de orina",
        options=[
            {"value": "CLARO", "ordinal": 0},
            {"value": "LIGERAMENTE TURBIO", "ordinal": 1},
            {"value": "TURBIO", "ordinal": 2, "is_pathological": True},
        ],
    )
    olor_orina = _get_or_create_option_set(
        code="OLOR_ORINA", name="Olor de orina",
        options=[
            {"value": "SUI-GENERIS", "ordinal": 0},
            {"value": "AMONIACAL", "ordinal": 1, "is_pathological": True},
        ],
    )
    densidad_orina = _get_or_create_option_set(
        code="DENSIDAD_ORINA", name="Densidad de orina (tira reactiva)",
        options=[
            {"value": "1010", "ordinal": 0, "numeric_equivalent": Decimal("1010")},
            {"value": "1015", "ordinal": 1, "numeric_equivalent": Decimal("1015")},
            {"value": "1020", "ordinal": 2, "numeric_equivalent": Decimal("1020")},
            {"value": "1025", "ordinal": 3, "numeric_equivalent": Decimal("1025")},
            {"value": "1030", "ordinal": 4, "numeric_equivalent": Decimal("1030")},
        ],
    )
    ph_orina = _get_or_create_option_set(
        code="PH_ORINA", name="pH de orina (tira reactiva)",
        options=[
            {"value": "5", "ordinal": 0, "numeric_equivalent": Decimal("5")},
            {"value": "6", "ordinal": 1, "numeric_equivalent": Decimal("6")},
            {"value": "6,5", "ordinal": 2, "numeric_equivalent": Decimal("6.5")},
            {"value": "7", "ordinal": 3, "numeric_equivalent": Decimal("7")},
            {"value": "8", "ordinal": 4, "numeric_equivalent": Decimal("8")},
            {"value": "9", "ordinal": 5, "numeric_equivalent": Decimal("9")},
        ],
    )
    neg_pos_cruces = _get_or_create_option_set(
        code="NEG_POS_CRUCES", name="Negativo / trazas / positivo en cruces",
        options=[
            {"value": "NEGATIVO", "ordinal": 0},
            {"value": "TRAZAS", "ordinal": 1},
            {"value": "POSITIVO (+)", "ordinal": 2, "is_pathological": True},
            {"value": "POSITIVO (++)", "ordinal": 3, "is_pathological": True},
            {"value": "POSITIVO (+++)", "ordinal": 4, "is_pathological": True},
            {"value": "POSITIVO (++++)", "ordinal": 5, "is_pathological": True},
        ],
    )
    neg_pos = _get_or_create_option_set(
        code="NEG_POS", name="Negativo / positivo",
        options=[
            {"value": "NEGATIVO", "ordinal": 0},
            {"value": "POSITIVO", "ordinal": 1, "is_pathological": True},
        ],
    )
    urobilinogeno = _get_or_create_option_set(
        code="UROBILINOGENO", name="Urobilinógeno",
        options=[
            {"value": "NORMAL", "ordinal": 0},
            {"value": "AUMENTADO", "ordinal": 1, "is_pathological": True},
        ],
    )
    abundancia = _get_or_create_option_set(
        code="ABUNDANCIA", name="Abundancia (sedimento)",
        options=[
            {"value": "AUSENTES", "ordinal": 0},
            {"value": "ESCASAS", "ordinal": 1},
            {"value": "MODERADAS", "ordinal": 2, "is_pathological": True},
            {"value": "ABUNDANTES", "ordinal": 3, "is_pathological": True},
        ],
    )
    # NO CONFIRMADO — catálogo típico de cristales en sedimento urinario, no viene de
    # los formatos de Angelus.
    cristales_orina = _get_or_create_option_set(
        code="CRISTALES_ORINA", name="Cristales en sedimento (no confirmado)",
        options=[
            {"value": "Oxalato de calcio", "ordinal": 0},
            {"value": "Ácido úrico", "ordinal": 1},
            {"value": "Fosfatos amorfos", "ordinal": 2},
            {"value": "Uratos amorfos", "ordinal": 3},
            {"value": "Triple fosfato (estruvita)", "ordinal": 4},
            {"value": "Cistina", "ordinal": 5, "is_pathological": True},
        ],
    )
    # NO CONFIRMADO — recuento bacteriano por screening; en la práctica es parte de un
    # urocultivo, no del uroanálisis de rutina. Se incluye sólo para ejercitar TITER.
    recuento_bacteriano = _get_or_create_option_set(
        code="RECUENTO_BACTERIANO_ORINA", name="Recuento bacteriano — screening (no confirmado)",
        options=[
            {
                "value": "< 10.000 UFC/mL", "ordinal": 0,
                "numeric_equivalent": Decimal("10000"),
            },
            {
                "value": "10.000 - 100.000 UFC/mL", "ordinal": 1,
                "numeric_equivalent": Decimal("100000"),
            },
            {
                "value": "> 100.000 UFC/mL", "ordinal": 2,
                "numeric_equivalent": Decimal("1000000"), "is_pathological": True,
            },
        ],
    )

    test, _ = Test.objects.get_or_create(
        code="URO",
        defaults={
            "name": "UROANÁLISIS",
            "section": section,
            "sample_type": Test.SampleType.ORINA,
            "container": "Envase estéril de boca ancha",
        },
    )

    grupo_fisico, _ = ParameterGroup.objects.get_or_create(
        test=test, name="EXAMEN FÍSICO", defaults={"order_index": 1}
    )
    grupo_quimico, _ = ParameterGroup.objects.get_or_create(
        test=test, name="EXAMEN QUÍMICO", defaults={"order_index": 2}
    )
    grupo_microscopico, _ = ParameterGroup.objects.get_or_create(
        test=test, name="EXAMEN MICROSCÓPICO", defaults={"order_index": 3}
    )

    # EXAMEN FÍSICO
    _get_or_create_parameter(
        test=test, group=grupo_fisico, code="URO_COLOR", name="COLOR",
        value_type=Parameter.ValueType.CODED, option_set=color_orina, order_index=1,
    )
    _get_or_create_parameter(
        test=test, group=grupo_fisico, code="URO_ASPECTO", name="ASPECTO",
        value_type=Parameter.ValueType.CODED, option_set=aspecto_orina, order_index=2,
    )
    _get_or_create_parameter(
        test=test, group=grupo_fisico, code="URO_OLOR", name="OLOR",
        value_type=Parameter.ValueType.CODED, option_set=olor_orina, order_index=3,
    )
    _get_or_create_parameter(
        test=test, group=grupo_fisico, code="URO_DENSIDAD", name="DENSIDAD",
        value_type=Parameter.ValueType.CODED, option_set=densidad_orina, order_index=4,
    )

    # EXAMEN QUÍMICO
    _get_or_create_parameter(
        test=test, group=grupo_quimico, code="URO_PH", name="pH",
        value_type=Parameter.ValueType.CODED, option_set=ph_orina, order_index=1,
    )
    _get_or_create_parameter(
        test=test, group=grupo_quimico, code="URO_PROTEINAS", name="PROTEÍNAS (tira reactiva)",
        value_type=Parameter.ValueType.SEMIQUANTITATIVE, option_set=neg_pos_cruces, order_index=2,
    )
    _get_or_create_parameter(
        test=test, group=grupo_quimico, code="URO_GLUCOSA", name="GLUCOSA",
        value_type=Parameter.ValueType.SEMIQUANTITATIVE, option_set=neg_pos_cruces, order_index=3,
    )
    _get_or_create_parameter(
        test=test, group=grupo_quimico, code="URO_CETONAS", name="CETONAS",
        value_type=Parameter.ValueType.SEMIQUANTITATIVE, option_set=neg_pos_cruces, order_index=4,
    )
    _get_or_create_parameter(
        test=test, group=grupo_quimico, code="URO_BILIRRUBINA", name="BILIRRUBINA",
        value_type=Parameter.ValueType.QUALITATIVE, option_set=neg_pos, order_index=5,
    )
    _get_or_create_parameter(
        test=test, group=grupo_quimico, code="URO_UROBILINOGENO", name="UROBILINÓGENO",
        value_type=Parameter.ValueType.CODED, option_set=urobilinogeno, order_index=6,
    )
    _get_or_create_parameter(
        test=test, group=grupo_quimico, code="URO_SANGRE_HB", name="SANGRE / HEMOGLOBINA",
        value_type=Parameter.ValueType.SEMIQUANTITATIVE, option_set=neg_pos_cruces, order_index=7,
    )
    _get_or_create_parameter(
        test=test, group=grupo_quimico, code="URO_NITRITOS", name="NITRITOS",
        value_type=Parameter.ValueType.QUALITATIVE, option_set=neg_pos, order_index=8,
    )
    _get_or_create_parameter(
        test=test, group=grupo_quimico, code="URO_LEUCOCITOS_TIRA",
        name="LEUCOCITOS (esterasa, tira reactiva)",
        value_type=Parameter.ValueType.SEMIQUANTITATIVE, option_set=neg_pos_cruces, order_index=9,
    )
    # NO CONFIRMADO — cuantificación de proteína/creatinina en orina, no viene de Angelus.
    _get_or_create_parameter(
        test=test, group=grupo_quimico, code="URO_PROT_ORINA",
        name="PROTEÍNA EN ORINA (cuantitativa)",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_mg_dl, order_index=10,
    )
    _get_or_create_parameter(
        test=test, group=grupo_quimico, code="URO_CREAT_ORINA", name="CREATININA EN ORINA",
        value_type=Parameter.ValueType.NUMERIC, unit=unit_mg_dl, order_index=11,
    )
    _get_or_create_parameter(
        test=test, group=grupo_quimico, code="URO_INDICE_PROT_CREAT",
        name="ÍNDICE PROTEÍNA/CREATININA",
        value_type=Parameter.ValueType.NUMERIC_CALCULATED, unit=unit_mg_g,
        formula="{URO_PROT_ORINA} / {URO_CREAT_ORINA} * 100", order_index=12,
    )

    # EXAMEN MICROSCÓPICO
    _get_or_create_parameter(
        test=test, group=grupo_microscopico, code="URO_HEMATIES", name="HEMATÍES",
        value_type=Parameter.ValueType.COUNT_RANGE, unit=unit_p_campo, order_index=1,
    )
    _get_or_create_parameter(
        test=test, group=grupo_microscopico, code="URO_LEUCOCITOS_SEDIMENTO",
        name="LEUCOCITOS",
        value_type=Parameter.ValueType.COUNT_RANGE, unit=unit_p_campo, order_index=2,
    )
    _get_or_create_parameter(
        test=test, group=grupo_microscopico, code="URO_CELULAS_EPITELIALES",
        name="CÉLULAS EPITELIALES",
        value_type=Parameter.ValueType.CODED, option_set=abundancia, order_index=3,
    )
    _get_or_create_parameter(
        test=test, group=grupo_microscopico, code="URO_CILINDROS", name="CILINDROS",
        value_type=Parameter.ValueType.CODED, option_set=abundancia, order_index=4,
    )
    _get_or_create_parameter(
        test=test, group=grupo_microscopico, code="URO_BACTERIAS", name="BACTERIAS",
        value_type=Parameter.ValueType.CODED, option_set=abundancia, order_index=5,
    )
    _get_or_create_parameter(
        test=test, group=grupo_microscopico, code="URO_MUCUS", name="MOCO/MUCUS",
        value_type=Parameter.ValueType.CODED, option_set=abundancia, order_index=6,
    )
    # NO CONFIRMADO
    _get_or_create_parameter(
        test=test, group=grupo_microscopico, code="URO_CRISTALES", name="CRISTALES",
        value_type=Parameter.ValueType.MULTI_CATALOG, option_set=cristales_orina, order_index=7,
    )
    # NO CONFIRMADO
    _get_or_create_parameter(
        test=test, group=grupo_microscopico, code="URO_RECUENTO_BACTERIANO",
        name="RECUENTO BACTERIANO (screening)",
        value_type=Parameter.ValueType.TITER, option_set=recuento_bacteriano, order_index=8,
    )
    _get_or_create_parameter(
        test=test, group=grupo_microscopico, code="URO_OBSERVACIONES",
        name="OBSERVACIONES DEL SEDIMENTO",
        value_type=Parameter.ValueType.NARRATIVE, order_index=9,
    )

    return test
