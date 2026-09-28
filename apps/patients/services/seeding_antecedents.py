"""Antecedentes de ejemplo con los parámetros a vigilar (Fase 11e, ADR-032). El
laboratorio los ajusta en Tablas auxiliares → Antecedentes. Un código de parámetro que no
exista en el catálogo del laboratorio simplemente se omite."""
from apps.catalog.selectors.catalog_queries import parameters_by_codes
from apps.patients.models import Antecedent

# (código, nombre, descripción, parámetros a vigilar)
DEFAULT_ANTECEDENTS = [
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


def seed_antecedents() -> int:
    """Crea los antecedentes que falten (idempotente). Devuelve cuántos creó."""
    created = 0
    for index, (code, name, description, codes) in enumerate(DEFAULT_ANTECEDENTS):
        antecedent, was_created = Antecedent.objects.get_or_create(
            code=code, defaults={"name": name, "description": description,
                                 "order_index": index})
        if was_created:
            created += 1
            params = parameters_by_codes(codes=codes)
            antecedent.suggested_parameters.set([params[c] for c in codes if c in params])
    return created
