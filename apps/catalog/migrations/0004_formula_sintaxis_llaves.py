"""Fase 07 (ADR-017): las fórmulas pasan a referenciar parámetros como `{CODIGO}`.

Reescribe las fórmulas sembradas en las Fases 05/06 con códigos sueltos
(`COAG_PTT_PACIENTE - COAG_PTT_CONTROL` → `{COAG_PTT_PACIENTE} - {COAG_PTT_CONTROL}`) y
puebla `depends_on`, que hasta ahora estaba vacío. Corre en cada esquema de tenant.
"""
import re

from django.db import migrations

# Un código suelto: mayúsculas/dígitos/_ que no esté ya entre llaves.
_BARE_CODE = re.compile(r"(?<![{@A-Za-z0-9_])([A-Z][A-Z0-9_]*)(?![A-Za-z0-9_}])")
_BRACED_CODE = re.compile(r"\{([A-Z][A-Z0-9_]*)\}")


def a_llaves(apps, schema_editor):
    Parameter = apps.get_model("catalog", "Parameter")
    calculated = Parameter.objects.filter(value_type="NUMERIC_CALCULATED").exclude(formula="")
    for parameter in calculated:
        parameter.formula = _BARE_CODE.sub(r"{\1}", parameter.formula)
        parameter.save(update_fields=["formula"])
        codes = set(_BRACED_CODE.findall(parameter.formula))
        parameter.depends_on.set(Parameter.objects.filter(code__in=codes))


def a_codigos_sueltos(apps, schema_editor):
    Parameter = apps.get_model("catalog", "Parameter")
    calculated = Parameter.objects.filter(value_type="NUMERIC_CALCULATED").exclude(formula="")
    for parameter in calculated:
        parameter.formula = _BRACED_CODE.sub(r"\1", parameter.formula)
        parameter.save(update_fields=["formula"])
        parameter.depends_on.clear()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_referencerange"),
    ]

    operations = [
        migrations.RunPython(a_llaves, a_codigos_sueltos),
    ]
