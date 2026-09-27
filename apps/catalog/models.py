from django.db import models

from apps.core.models import TenantBaseModel

# value_type que requieren un CodedOptionSet asociado (usado en el CheckConstraint de
# Parameter.Meta). Nivel de módulo a propósito: una clase anidada (Meta, ValueType) no ve
# los atributos de la clase que la contiene, sólo el scope del módulo — referenciar
# `ValueType.CODED` o `OPTION_BASED_VALUE_TYPES` como atributo de Parameter dentro de
# `class Meta` lanzaría NameError al importar el módulo.
OPTION_BASED_VALUE_TYPES = (
    "CODED", "SEMIQUANTITATIVE", "QUALITATIVE", "TITER", "MULTI_CATALOG",
)


class Section(TenantBaseModel):
    """Sección del catálogo de exámenes (HEMATOLOGÍA, QUÍMICA SANGUÍNEA, ORINA...)."""

    code = models.CharField("Código", max_length=30, unique=True)
    name = models.CharField("Nombre", max_length=100)
    order_index = models.PositiveIntegerField("Orden", default=0)
    print_page_break = models.BooleanField(
        "Salto de página al imprimir", default=False
    )

    class Meta:
        verbose_name = "Sección"
        verbose_name_plural = "Secciones"
        ordering = ["order_index", "name"]

    def __str__(self) -> str:
        return self.name


class Unit(TenantBaseModel):
    """Unidad de medida (g/dL, mg/dL, %, /mm3...)."""

    symbol = models.CharField("Símbolo", max_length=20, unique=True)
    description = models.CharField("Descripción", max_length=100, blank=True, default="")

    class Meta:
        verbose_name = "Unidad"
        verbose_name_plural = "Unidades"
        ordering = ["symbol"]

    def __str__(self) -> str:
        return self.symbol


class Method(TenantBaseModel):
    """Método analítico impreso bajo el resultado (Colorimétrico Jaffé modificado...)."""

    name = models.CharField("Nombre", max_length=150, unique=True)
    description = models.CharField("Descripción", max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "Método"
        verbose_name_plural = "Métodos"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class CodedOptionSet(TenantBaseModel):
    """Conjunto de opciones codificadas (COLOR_ORINA, NEG_POS_CRUCES...)."""

    code = models.CharField("Código", max_length=40, unique=True)
    name = models.CharField("Nombre", max_length=100)

    class Meta:
        verbose_name = "Conjunto de opciones"
        verbose_name_plural = "Conjuntos de opciones"
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name


class CodedOption(TenantBaseModel):
    """Una opción concreta dentro de un `CodedOptionSet` (NEGATIVO, POSITIVO (++)...)."""

    option_set = models.ForeignKey(
        CodedOptionSet, on_delete=models.PROTECT, related_name="options"
    )
    value = models.CharField("Valor", max_length=150)
    ordinal = models.PositiveIntegerField(
        "Orden clínico", null=True, blank=True
    )
    numeric_equivalent = models.DecimalField(
        # max_digits=12 (no 10): recuentos bacterianos de screening llegan a 1.000.000.
        "Equivalente numérico", max_digits=12, decimal_places=4, null=True, blank=True
    )
    is_pathological = models.BooleanField("Marca resultado patológico", default=False)
    order_index = models.PositiveIntegerField("Orden de presentación", default=0)

    class Meta:
        verbose_name = "Opción codificada"
        verbose_name_plural = "Opciones codificadas"
        ordering = ["option_set", "order_index"]
        unique_together = [("option_set", "value")]

    def __str__(self) -> str:
        return f"{self.option_set.code}: {self.value}"


class Test(TenantBaseModel):
    """Examen individual — la unidad que se ordena y se cobra (HEM_COMP, URO, COPRO...)."""

    class SampleType(models.TextChoices):
        SANGRE_TOTAL = "SANGRE_TOTAL", "Sangre total"
        SUERO = "SUERO", "Suero"
        PLASMA = "PLASMA", "Plasma"
        ORINA = "ORINA", "Orina"
        ORINA_24H = "ORINA_24H", "Orina 24 horas"
        HECES = "HECES", "Heces"
        OTRO = "OTRO", "Otro"

    code = models.CharField("Código", max_length=30, unique=True)
    name = models.CharField("Nombre", max_length=150)
    section = models.ForeignKey(Section, on_delete=models.PROTECT, related_name="tests")
    method = models.ForeignKey(
        Method, on_delete=models.PROTECT, related_name="tests", null=True, blank=True
    )
    sample_type = models.CharField(
        "Tipo de muestra", max_length=15, choices=SampleType.choices
    )
    process_hours = models.PositiveIntegerField(
        "Horas de proceso", null=True, blank=True
    )
    # Sin `price`: los precios viven en billing.PriceListItem (ADR-019).
    requires_fasting = models.BooleanField("Requiere ayuno", default=False)
    requires_anthropometry = models.BooleanField(
        "Requiere datos antropométricos", default=False
    )

    class Meta:
        verbose_name = "Examen"
        verbose_name_plural = "Exámenes"
        ordering = ["section__order_index", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class ParameterGroup(TenantBaseModel):
    """Subtítulo de presentación dentro de un examen (EXAMEN FÍSICO, SERIE ROJA...)."""

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="parameter_groups")
    name = models.CharField("Nombre", max_length=100)
    order_index = models.PositiveIntegerField("Orden", default=0)

    class Meta:
        verbose_name = "Grupo de parámetros"
        verbose_name_plural = "Grupos de parámetros"
        ordering = ["test", "order_index"]
        unique_together = [("test", "name")]

    def __str__(self) -> str:
        return f"{self.test.code} — {self.name}"


class Parameter(TenantBaseModel):
    """Un parámetro/analito reportado dentro de un examen (HEMOGLOBINA, COLOR, PROTEÍNAS...)."""

    class ValueType(models.TextChoices):
        NUMERIC = "NUMERIC", "Numérico"
        NUMERIC_CALCULATED = "NUMERIC_CALCULATED", "Numérico calculado"
        CODED = "CODED", "Codificado"
        SEMIQUANTITATIVE = "SEMIQUANTITATIVE", "Semicuantitativo"
        QUALITATIVE = "QUALITATIVE", "Cualitativo"
        TITER = "TITER", "Título/dilución"
        COUNT_RANGE = "COUNT_RANGE", "Rango de conteo"
        NARRATIVE = "NARRATIVE", "Narrativo"
        MULTI_CATALOG = "MULTI_CATALOG", "Catálogo multi-selección"

    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="parameters")
    group = models.ForeignKey(
        ParameterGroup, on_delete=models.SET_NULL, related_name="parameters",
        null=True, blank=True,
    )
    code = models.CharField("Código", max_length=40, unique=True)
    name = models.CharField("Nombre", max_length=150)
    value_type = models.CharField(
        "Tipo de valor", max_length=20, choices=ValueType.choices
    )
    unit = models.ForeignKey(
        Unit, on_delete=models.PROTECT, related_name="parameters", null=True, blank=True
    )
    decimals = models.PositiveSmallIntegerField("Decimales", default=2)
    order_index = models.PositiveIntegerField("Orden", default=0)
    option_set = models.ForeignKey(
        CodedOptionSet, on_delete=models.PROTECT, related_name="parameters",
        null=True, blank=True,
    )
    formula = models.TextField("Fórmula", blank=True, default="")
    depends_on = models.ManyToManyField(
        "self", symmetrical=False, related_name="depended_by", blank=True
    )
    is_printable = models.BooleanField("Se imprime en el informe", default=True)
    is_optional = models.BooleanField("Opcional (puede quedar en blanco)", default=False)
    instrument_code = models.CharField(
        "Código del instrumento", max_length=40, blank=True, default=""
    )

    class Meta:
        verbose_name = "Parámetro"
        verbose_name_plural = "Parámetros"
        ordering = ["test", "group__order_index", "order_index"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(value_type__in=OPTION_BASED_VALUE_TYPES)
                    & models.Q(option_set__isnull=False)
                )
                | ~models.Q(value_type__in=OPTION_BASED_VALUE_TYPES),
                name="parameter_option_set_required_for_coded_types",
            ),
            models.CheckConstraint(
                condition=~models.Q(value_type="NUMERIC_CALCULATED") | ~models.Q(formula=""),
                name="parameter_formula_required_when_calculated",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.test.code} — {self.name}"


# range_type que requieren low/high/etc. (usado en los CheckConstraint de
# ReferenceRange.Meta — mismo motivo que OPTION_BASED_VALUE_TYPES arriba: una clase
# anidada no ve los atributos de la clase que la contiene, sólo el scope del módulo).
RANGE_TYPES_REQUIRING_LOW = ("CLOSED", "LOWER_BOUND")
RANGE_TYPES_REQUIRING_HIGH = ("CLOSED", "UPPER_BOUND")


class ReferenceRange(TenantBaseModel):
    """Rango de referencia de un parámetro, resuelto por sexo + edad en días +
    condición. Ver `services/reference_resolver.py::resolve_reference_range()`."""

    class Sex(models.TextChoices):
        M = "M", "Masculino"
        F = "F", "Femenino"
        ANY = "ANY", "Ambos"

    class Condition(models.TextChoices):
        NINGUNA = "NINGUNA", "Ninguna"
        EMBARAZO = "EMBARAZO", "Embarazo"
        AYUNO = "AYUNO", "Ayuno"
        POST_PRANDIAL = "POST_PRANDIAL", "Post-prandial"

    class RangeType(models.TextChoices):
        CLOSED = "CLOSED", "Rango cerrado"
        UPPER_BOUND = "UPPER_BOUND", "Límite superior"
        LOWER_BOUND = "LOWER_BOUND", "Límite inferior"
        TOLERANCE = "TOLERANCE", "Tolerancia"
        QUALITATIVE = "QUALITATIVE", "Cualitativo"
        INTERPRETIVE = "INTERPRETIVE", "Interpretativo"

    parameter = models.ForeignKey(
        Parameter, on_delete=models.CASCADE, related_name="reference_ranges"
    )
    sex = models.CharField("Sexo", max_length=3, choices=Sex.choices, default=Sex.ANY)
    age_min_days = models.PositiveIntegerField("Edad mínima (días)", default=0)
    age_max_days = models.PositiveIntegerField("Edad máxima (días)", default=54750)
    condition = models.CharField(
        "Condición", max_length=15, choices=Condition.choices, default=Condition.NINGUNA
    )
    range_type = models.CharField(
        "Tipo de rango", max_length=15, choices=RangeType.choices
    )
    low = models.DecimalField(
        "Límite inferior", max_digits=10, decimal_places=4, null=True, blank=True
    )
    high = models.DecimalField(
        "Límite superior", max_digits=10, decimal_places=4, null=True, blank=True
    )
    center = models.DecimalField(
        "Centro", max_digits=10, decimal_places=4, null=True, blank=True
    )
    tolerance = models.DecimalField(
        "Tolerancia", max_digits=10, decimal_places=4, null=True, blank=True
    )
    expected_option = models.ForeignKey(
        CodedOption, on_delete=models.PROTECT, related_name="+", null=True, blank=True
    )
    bands = models.JSONField("Bandas interpretativas", null=True, blank=True)
    display_text = models.CharField("Texto a imprimir", max_length=255)
    unit = models.ForeignKey(
        Unit, on_delete=models.PROTECT, related_name="+", null=True, blank=True
    )
    priority = models.PositiveIntegerField("Prioridad (desempate)", default=0)
    # Valores críticos / de pánico (Fase 10, ADR-025): fuera de estos límites el resultado
    # se marca CRÍTICO y no se valida sin registrar a quién se notificó.
    critical_low = models.DecimalField(
        "Crítico bajo", max_digits=12, decimal_places=4, null=True, blank=True
    )
    critical_high = models.DecimalField(
        "Crítico alto", max_digits=12, decimal_places=4, null=True, blank=True
    )
    critical_note = models.CharField(
        "Origen de los críticos", max_length=120, blank=True, default="",
        help_text="P. ej. «PROPUESTO (literatura)» o «Confirmado por el laboratorio».",
    )

    class Meta:
        verbose_name = "Rango de referencia"
        verbose_name_plural = "Rangos de referencia"
        ordering = ["parameter", "-priority"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(age_min_days__lte=models.F("age_max_days")),
                name="referencerange_age_min_lte_age_max",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(range_type__in=RANGE_TYPES_REQUIRING_LOW)
                    & models.Q(low__isnull=False)
                )
                | ~models.Q(range_type__in=RANGE_TYPES_REQUIRING_LOW),
                name="referencerange_low_required",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(range_type__in=RANGE_TYPES_REQUIRING_HIGH)
                    & models.Q(high__isnull=False)
                )
                | ~models.Q(range_type__in=RANGE_TYPES_REQUIRING_HIGH),
                name="referencerange_high_required",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(range_type="TOLERANCE")
                    & models.Q(center__isnull=False)
                    & models.Q(tolerance__isnull=False)
                )
                | ~models.Q(range_type="TOLERANCE"),
                name="referencerange_tolerance_requires_center_and_tolerance",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(range_type="QUALITATIVE")
                    & models.Q(expected_option__isnull=False)
                )
                | ~models.Q(range_type="QUALITATIVE"),
                name="referencerange_qualitative_requires_expected_option",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(range_type="INTERPRETIVE") & models.Q(bands__isnull=False)
                )
                | ~models.Q(range_type="INTERPRETIVE"),
                name="referencerange_interpretive_requires_bands",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.parameter.code} — {self.display_text}"


class Profile(TenantBaseModel):
    """Perfil: agrupación nombrada de exámenes que se ordena como un paquete
    (PERFIL LIPÍDICO, PERFIL 20, PRE-OPERATORIO...). El precio NO vive aquí sino en cada
    lista de precios de `apps.billing` (ADR-019)."""

    code = models.CharField("Código", max_length=40, unique=True)
    name = models.CharField("Nombre", max_length=150)
    description = models.TextField("Descripción", blank=True, default="")
    order_index = models.PositiveIntegerField("Orden", default=0)
    tests = models.ManyToManyField(
        Test, through="ProfileTest", related_name="profiles", verbose_name="Exámenes"
    )

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfiles"
        ordering = ["order_index", "name"]

    def __str__(self) -> str:
        return self.name


class ProfileTest(TenantBaseModel):
    """Examen dentro de un perfil, con su orden de presentación."""

    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="profile_tests"
    )
    test = models.ForeignKey(Test, on_delete=models.PROTECT, related_name="profile_tests")
    order_index = models.PositiveIntegerField("Orden", default=0)

    class Meta:
        verbose_name = "Examen del perfil"
        verbose_name_plural = "Exámenes del perfil"
        ordering = ["profile", "order_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "test"], name="profiletest_unique_profile_test"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.profile.code} — {self.test.code}"


class ContainerType(TenantBaseModel):
    """Tubo o envase de toma (Fase 09, ADR-024). Lo define el aditivo: azul citrato, rojo
    seco, morado EDTA... Cada laboratorio ajusta los suyos; `draw_order` es el orden de
    extracción (CLSI GP41) que se muestra al flebotomista."""

    class Additive(models.TextChoices):
        CITRATO = "CITRATO", "Citrato de sodio"
        NINGUNO = "NINGUNO", "Sin aditivo / activador"
        GEL = "GEL", "Gel separador"
        HEPARINA = "HEPARINA", "Heparina"
        EDTA = "EDTA", "EDTA"
        FLUORURO = "FLUORURO", "Fluoruro / oxalato"
        NO_APLICA = "NO_APLICA", "No aplica (envase)"

    code = models.CharField("Código", max_length=30, unique=True)
    name = models.CharField("Nombre", max_length=80)
    short_name = models.CharField(
        "Nombre corto (etiqueta)", max_length=12,
        help_text="Lo que se imprime en la etiqueta: AZUL, ROJO, ORINA…",
    )
    color = models.CharField("Color", max_length=7, default="#94a3b8",
                             help_text="Hexadecimal, p. ej. #2563eb")
    additive = models.CharField("Aditivo", max_length=12, choices=Additive.choices)
    sample_type = models.CharField("Tipo de muestra", max_length=15,
                                   choices=Test.SampleType.choices)
    volume_ml = models.DecimalField("Volumen (mL)", max_digits=6, decimal_places=1,
                                    null=True, blank=True)
    draw_order = models.PositiveSmallIntegerField("Orden de extracción", default=50)
    max_tests = models.PositiveSmallIntegerField(
        "Máx. exámenes por tubo", default=0, help_text="0 = sin límite."
    )

    class Meta:
        verbose_name = "Tubo / envase"
        verbose_name_plural = "Tubos y envases"
        ordering = ["draw_order", "name"]

    def __str__(self) -> str:
        return self.name


class SampleRequirement(TenantBaseModel):
    """Qué tubo(s) necesita un examen. Casi siempre uno; la depuración de creatinina lleva
    envase de 24 h + tubo rojo, y una curva lleva una toma por tiempo (`collection_label`).

    Al planificar los tubos de una orden, los requisitos con el mismo tubo y la misma
    `collection_label` comparten tubo, salvo `own_container` (envío externo, hielo, otra
    área) o si el tubo llega a `ContainerType.max_tests`."""

    test = models.ForeignKey(Test, on_delete=models.CASCADE,
                             related_name="sample_requirements")
    container_type = models.ForeignKey(ContainerType, on_delete=models.PROTECT,
                                       related_name="requirements", verbose_name="Tubo")
    collection_label = models.CharField(
        "Toma", max_length=30, blank=True, default="",
        help_text="Sólo para tomas por tiempo: «Basal», «2 horas post-carga»…",
    )
    own_container = models.BooleanField(
        "Tubo propio", default=False,
        help_text="No compartir el tubo con otros exámenes.",
    )
    order_index = models.PositiveSmallIntegerField("Orden", default=0)

    class Meta:
        verbose_name = "Tubo requerido"
        verbose_name_plural = "Tubos requeridos"
        ordering = ["test", "order_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["test", "container_type", "collection_label"],
                name="samplerequirement_unique",
            ),
        ]

    def __str__(self) -> str:
        label = f" ({self.collection_label})" if self.collection_label else ""
        return f"{self.test.code} → {self.container_type.short_name}{label}"


class ReagentLot(TenantBaseModel):
    """Lote de reactivo con sus datos de cálculo (Fase 10, ADR-025). Hoy: el ISI de la
    tromboplastina para el INR. Un solo lote vigente por reactivo; el resultado copia el
    lote y el ISI usados, así un cambio de lote no altera informes anteriores."""

    class Reagent(models.TextChoices):
        TROMBOPLASTINA = "TROMBOPLASTINA", "Tromboplastina (PT / INR)"

    reagent = models.CharField("Reactivo", max_length=20, choices=Reagent.choices)
    lot_number = models.CharField("Lote", max_length=40)
    brand = models.CharField("Marca", max_length=80, blank=True, default="")
    isi = models.DecimalField("ISI", max_digits=6, decimal_places=3, null=True, blank=True)
    expires_on = models.DateField("Vence", null=True, blank=True)
    is_current = models.BooleanField("Vigente", default=False)

    class Meta:
        verbose_name = "Lote de reactivo"
        verbose_name_plural = "Lotes de reactivos"
        ordering = ["reagent", "-is_current", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["reagent"], condition=models.Q(is_current=True),
                                    name="reagentlot_single_current"),
            models.UniqueConstraint(fields=["reagent", "lot_number"],
                                    name="reagentlot_unique_lot"),
        ]

    def __str__(self) -> str:
        return f"{self.get_reagent_display()} — lote {self.lot_number}"


class ObservationTemplate(TenantBaseModel):
    """Observación predefinida para el informe (Fase 10, ADR-025). Se elige al cargar y se
    imprime **debajo del examen** al que corresponde, no al final del informe.

    Alcance: `test` (sólo ese examen), si no `section` (exámenes de esa sección), si no
    general (todos). `__` marca un hueco que se completa al usarla («DISMÓRFICOS __ %»)."""

    text = models.CharField("Texto", max_length=255)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, null=True, blank=True,
                                related_name="observation_templates", verbose_name="Sección")
    test = models.ForeignKey(Test, on_delete=models.CASCADE, null=True, blank=True,
                             related_name="observation_templates", verbose_name="Examen")
    order_index = models.PositiveIntegerField("Orden", default=0)

    class Meta:
        verbose_name = "Observación predefinida"
        verbose_name_plural = "Observaciones predefinidas"
        ordering = ["order_index", "text"]

    def __str__(self) -> str:
        return self.text
