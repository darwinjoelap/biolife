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
    container = models.CharField(
        "Contenedor", max_length=100, blank=True, default=""
    )
    process_hours = models.PositiveIntegerField(
        "Horas de proceso", null=True, blank=True
    )
    price = models.DecimalField(
        "Precio", max_digits=10, decimal_places=2, null=True, blank=True
    )
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
                check=(
                    models.Q(value_type__in=OPTION_BASED_VALUE_TYPES)
                    & models.Q(option_set__isnull=False)
                )
                | ~models.Q(value_type__in=OPTION_BASED_VALUE_TYPES),
                name="parameter_option_set_required_for_coded_types",
            ),
            models.CheckConstraint(
                check=~models.Q(value_type="NUMERIC_CALCULATED") | ~models.Q(formula=""),
                name="parameter_formula_required_when_calculated",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.test.code} — {self.name}"
