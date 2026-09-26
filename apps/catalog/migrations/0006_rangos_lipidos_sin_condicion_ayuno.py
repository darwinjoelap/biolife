"""ADR-021: los rangos de colesterol, triglicéridos y HDL sembrados en la Fase 06 tenían
condición AYUNO. Como el resolver busca por defecto la condición NINGUNA, ningún paciente
los recibía. El ayuno es requisito del examen (`Test.requires_fasting`), no un rango
distinto: se pasan a NINGUNA salvo que el tenant ya tenga uno en NINGUNA para el mismo
sexo y tramo de edad."""
from django.db import migrations

LIPIDOS = ("LIP_COLESTEROL_TOTAL", "LIP_TRIGLICERIDOS", "LIP_HDL")


def ayuno_a_ninguna(apps, schema_editor):
    ReferenceRange = apps.get_model("catalog", "ReferenceRange")
    for rr in ReferenceRange.objects.filter(parameter__code__in=LIPIDOS, condition="AYUNO"):
        ya_existe = ReferenceRange.objects.filter(
            parameter_id=rr.parameter_id, sex=rr.sex, age_min_days=rr.age_min_days,
            age_max_days=rr.age_max_days, condition="NINGUNA", range_type=rr.range_type,
        ).exists()
        if not ya_existe:
            rr.condition = "NINGUNA"
            rr.save(update_fields=["condition"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_profiles_y_sin_precio_en_test"),
    ]

    operations = [
        migrations.RunPython(ayuno_a_ninguna, migrations.RunPython.noop),
    ]
