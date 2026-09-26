# Fase 07 — Motor de fórmulas

**Depende de:** Fase 06 (rangos de referencia) · **Modelo sugerido:** Opus
**Criterio de salida (roadmap):** Las 16 fórmulas de `04_HALLAZGOS` reproducen los valores reales.

## Objetivo

Implementar el motor de parámetros calculados (`Parameter.value_type = NUMERIC_CALCULATED`)
descrito en `docs/00_ARQUITECTURA.md` §"Motor de fórmulas": evaluación segura con AST
restringido, dependencias en `Parameter.depends_on`, orden topológico, detección de ciclos
al guardar, variables de la orden (`{@peso}`…) y cálculo parcial cuando falta un insumo.
Sembrar y verificar las 16 fórmulas de `docs/04_HALLAZGOS_FORMATOS.md` §4.

## Decisiones tomadas con Darwin al iniciar

1. **Sintaxis `{CODIGO}` / `{@variable}`**, la de la arquitectura. Las 2 fórmulas ya
   sembradas con códigos sueltos (`COAG_PTT_DIFERENCIA`, `URO_INDICE_PROT_CREAT`) se
   reescriben con la migración de datos `0004_formula_sintaxis_llaves`.
2. **ISI como variable de contexto `{@isi}`.** El motor lo recibe igual que peso/talla.
   Dónde se guarda (TenantSettings, por lote de reactivo) se decide en la Fase 10.
3. **Precisión completa en los intermedios** (como Excel). Se redondea sólo para mostrar,
   con `quantize_for_display()` (mitad hacia arriba) a `Parameter.decimals`.
4. **Entrega:** archivos escritos directo en `C:\proyectos\biolife`, construidos y probados
   antes contra PostgreSQL 16 real; Darwin corre `migrate_schemas`/`pytest`/`ruff` en su
   máquina y confirma.

## Hallazgo durante la fase: superficie corporal es Mosteller, no DuBois

`04_HALLAZGOS_FORMATOS.md` documenta DuBois (`0.007184 × talla^0.725 × peso^0.425`) y
afirma que reproduce la hoja `DEPURACIÓN`. **No la reproduce:** con talla 165 cm y peso
62 kg DuBois da 1,6819 m² → depuración corregida 67,76 mL/min; la hoja imprime 1,6857 m²
→ 67,61 mL/min. Ese 1,6857 es exactamente **Mosteller**: `sqrt(talla × peso / 3600)`.
Se sembró Mosteller (reproduce el dato real) y se agregó la pregunta a Angelus. Ver ADR-017.

## Alcance

**Incluye:**
- `services/formula_engine.py` (puro, sin ORM): `parse_formula`, `evaluate_formula`,
  `calculation_order`, `evaluate_calculated_parameters`, `quantize_for_display`,
  `CONTEXT_VARIABLES`, excepciones `FormulaSyntaxError` / `FormulaEvaluationError` /
  `MissingInputError` (todas `ApplicationError`).
- `services/formula_validation.py`: `validate_formula` (códigos existentes, sólo
  numéricos, sin autorreferencia, sin ciclos), `set_parameter_formula` (único camino para
  asignar fórmula; sincroniza `depends_on`), `sync_parameter_dependencies`.
- Migración de datos `0004_formula_sintaxis_llaves` (reversible).
- `services/seeding_formulas.py`: parámetros de entrada faltantes + los 16 calculados +
  examen nuevo `DEPURACION` (`ORINA_24H`, `requires_anthropometry=True`).
- Management command `seed_formulas` (corre antes las siembras de las Fases 05 y 06).
- Admin: `ParameterAdminForm` valida la fórmula; `depends_on` de sólo lectura.
- Tests: motor puro, validación/ciclos/migración, y las 16 fórmulas.

**No incluye (fases posteriores):**
- Cálculo en vivo durante la captura, `ResultValue.is_calculated`/`source=CALCULADO` y
  registro persistente del motivo de un calculado vacío (Fase 10).
- Origen persistente del ISI (Fase 10).
- Rangos de referencia de los nuevos parámetros (CHCM, globulinas, LDL, INR…) — los
  valores de `04_HALLAZGOS` §1-2 están disponibles; sembrarlos cuando la Fase 10 los use.
- Fórmulas con parámetros de **otro examen** de la misma orden: el motor lo permite (los
  códigos son únicos por tenant), pero la Fase 10 debe decidir si se toman valores de
  otros `Result` de la orden.

## Tareas

1. [x] `formula_engine.py` con lista blanca de nodos AST, `Decimal`, orden topológico.
2. [x] `formula_validation.py` + detección de ciclos al guardar + `depends_on`.
3. [x] Migración `0004` (códigos sueltos → llaves) y actualización de las 2 siembras.
4. [x] `seeding_formulas.py` + command `seed_formulas`.
5. [x] Admin con validación de fórmula.
6. [x] Tests (51 nuevos, 107/107).
7. [x] Cierre: `docs/ESTADO.md`, ADR-017, errata en `04_HALLAZGOS_FORMATOS.md`.

## Criterios de salida

- [ ] `python manage.py migrate_schemas` aplica `catalog.0004` en los 3 tenants sin errores.
- [ ] `python manage.py makemigrations --check --dry-run` → "No changes detected".
- [ ] `python manage.py tenant_command seed_formulas --schema=demo_uno` dos veces sin errores.
- [ ] `pytest -q` → 107 passed. `ruff check .` limpio.
- [x] Las 16 fórmulas reproducen los valores (test `test_las_16_formulas_reproducen_los_valores`):
      las 3 de depuración con valor impreso (1,6857 / 65,88 / 67,61) contra datos **reales**;
      las otras 13 contra valores calculados a mano (el doc de hallazgos no trae ejemplos).

(Los 4 primeros los verificó Claude en un Postgres 16 limpio; falta la corrida en la
máquina de Darwin.)

## Riesgos y trampas

- **Nunca `eval()`**: cualquier nodo fuera de la lista blanca se rechaza al parsear.
- **`Decimal(float)` arrastra el error binario**: `_to_decimal` convierte vía `str`.
- **El pk UUID existe antes de guardar**: en el admin se usa `obj._state.adding`, no `obj.pk`.
- **`validate_formula` parsea todas las fórmulas del tenant** para detectar ciclos: una
  fórmula inválida guardada por fuera del service (ORM directo) hace fallar la validación
  de las demás. Asignar fórmulas siempre con `set_parameter_formula()` o el admin.

## Entrega sugerida

```
git add apps/catalog docs/roadmap/07_motor_de_formulas.md docs/ESTADO.md \
    docs/DECISIONES.md docs/04_HALLAZGOS_FORMATOS.md TASKS.md
git commit -m "feat(catalog): motor de formulas con AST restringido, 16 formulas sembradas (Fase 07)"
```
