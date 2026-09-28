"""Siembra los antecedentes de ejemplo en los laboratorios existentes (Fase 11e)."""
from django.db import migrations

DEFAULTS = [
    ("DIABETES", "Diabetes", "Control glicémico y función renal.",
     ["QUIM_GLICEMIA", "ESP_HBA1C", "QUIM_GLICEMIA_PP", "QUIM_CREATININA"]),
    ("HIPERTENSION", "Hipertensión arterial", "Función renal y electrolitos.",
     ["QUIM_CREATININA", "QUIM_UREA", "QUIM_POTASIO", "QUIM_SODIO"]),
    ("ANTICOAGULADO", "Tratamiento anticoagulante", "Control del INR.",
     ["COAG_INR", "COAG_PT_PACIENTE"]),
    ("ENF_RENAL", "Enfermedad renal", "Seguimiento de la función renal.",
     ["QUIM_CREATININA", "QUIM_UREA", "QUIM_POTASIO", "QUIM_ACIDO_URICO"]),
    ("DISLIPIDEMIA", "Dislipidemia", "Perfil lipídico.",
     ["LIP_COLESTEROL_TOTAL", "LIP_TRIGLICERIDOS", "LIP_LDL", "LIP_HDL"]),
    ("ANEMIA", "Anemia", "Seguimiento de la hemoglobina.", ["HEM_HEMOGLOBINA"]),
    ("HEPATOPATIA", "Enfermedad hepática", "Transaminasas.", ["QUIM_TGO", "QUIM_TGP"]),
    ("HIPERURICEMIA", "Hiperuricemia / gota", "Ácido úrico.", ["QUIM_ACIDO_URICO"]),
]


def seed(apps, schema_editor):
    Antecedent = apps.get_model("patients", "Antecedent")
    Parameter = apps.get_model("catalog", "Parameter")
    if not Parameter.objects.exists():
        return  # laboratorio sin catálogo (o esquema public): lo siembra la provisión
    for index, (code, name, description, codes) in enumerate(DEFAULTS):
        antecedent, created = Antecedent.objects.get_or_create(
            code=code, defaults={"name": name, "description": description,
                                 "order_index": index})
        if created:
            antecedent.suggested_parameters.set(Parameter.objects.filter(code__in=codes))


class Migration(migrations.Migration):
    dependencies = [
        ("patients", "0002_antecedentes"),
        ("catalog", "0009_observaciones_predefinidas"),
    ]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
