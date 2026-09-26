"""Fórmulas sembradas (Fase 07).

Desde la Fase 08 los parámetros calculados se declaran junto con su examen en
`services/seeding_base_catalog.py` (fuente única, ADR-019). Este módulo conserva la
entrada pública `seed_formulas()` y la lista de las 16 fórmulas de
`docs/04_HALLAZGOS_FORMATOS.md` §4 que usa el test del criterio de salida de la Fase 07.

Superficie corporal = Mosteller: es la fórmula literal de la celda de la hoja DEPURACIÓN
(`=SQRT((K24*K25)/3600)`), confirmado en la Fase 08 (ADR-017/019).
"""
from apps.catalog.services.seeding_base_catalog import seed_base_catalog

# Los 16 calculados de 04_HALLAZGOS_FORMATOS.md, sección 4 (en ese orden).
FORMULA_CODES_04_HALLAZGOS: tuple[str, ...] = (
    "HEM_CHCM", "QUIM_GLOBULINAS", "QUIM_REL_ALB_GLO", "QUIM_BILIRRUBINA_INDIRECTA",
    "LIP_VLDL", "LIP_LDL", "LIP_CASTELLI_I", "LIP_CASTELLI_II",
    "COAG_PT_RAZON", "COAG_INR", "COAG_PTT_DIFERENCIA",
    "DEP_SUPERFICIE_CORPORAL", "DEP_DEPURACION_SIN_CORR", "DEP_DEPURACION_CORREGIDA",
    "DEP_VOLUMEN_MINUTO", "DEP_CREAT_URINARIA_24H",
)
# Encontradas al leer las celdas de las hojas en la Fase 08 (no estaban en 04_HALLAZGOS).
FORMULA_CODES_ADICIONALES: tuple[str, ...] = ("HOR_HOMA_IR",)


def seed_formulas() -> None:
    """Siembra el catálogo base, que incluye todos los parámetros calculados.
    Idempotente. Debe correr dentro del `schema_context()` del tenant."""
    seed_base_catalog()
