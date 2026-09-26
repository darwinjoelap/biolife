# Fase 06 — Rangos de referencia

**Depende de:** Fase 05 (catálogo) · **Modelo sugerido:** Sonnet
**Criterio de salida (roadmap):** Resolución por sexo + edad en días, 6 `range_type`.

## Objetivo

Construir `ReferenceRange` (sección D de `docs/01_MODELO_DATOS.md`) y
`services/reference_resolver.py`, y demostrarlos con datos reales de
`docs/04_HALLAZGOS_FORMATOS.md` que ejerciten los 6 `range_type`: `CLOSED`,
`UPPER_BOUND`, `LOWER_BOUND`, `TOLERANCE`, `QUALITATIVE`, `INTERPRETIVE`.

## Contexto y decisiones tomadas antes de implementar

**1. Alcance de exámenes.** El Uroanálisis de la Fase 05 sólo cubre bien `QUALITATIVE`
(parámetros `NEG_POS`). Los demás `range_type` sí tienen datos numéricos reales y
confirmados en `04_HALLAZGOS_FORMATOS.md`, pero de otros exámenes. Se decidió **sembrar 4
exámenes nuevos, pequeños, sólo con los parámetros necesarios** para colgarles rangos
reales (no la lista completa de cada examen — eso se completa fase a fase según se
necesite, igual que con Uroanálisis en la Fase 05):
- `HEM_COMP` (Hematología completa): HEMOGLOBINA, HEMATOCRITO, GLÓBULOS BLANCOS.
- `PERFIL_LIPIDICO`: COLESTEROL TOTAL, HDL, TRIGLICÉRIDOS.
- `COAGUL` (Coagulación): PTT PACIENTE, PTT CONTROL, PTT DIFERENCIA (calculado).
- `QUIM` (Química sanguínea): GLICEMIA, ÚREA, CREATININA, ÁCIDO ÚRICO, BILIRRUBINA
  TOTAL, BILIRRUBINA DIRECTA, PROCALCITONINA.

`QUALITATIVE` se demuestra reutilizando un parámetro que ya existe (`URO_NITRITOS` de la
Fase 05, opción esperada `NEGATIVO` de su `CodedOptionSet` `NEG_POS`) — no hace falta
sembrar nada nuevo para ese tipo.

**2. Los 6 parámetros con rangos contradictorios se siembran con un valor, marcado
pendiente.** `04_HALLAZGOS_FORMATOS.md` marca GLICEMIA, ÚREA, CREATININA, ÁCIDO ÚRICO,
BILIRRUBINA TOTAL y BILIRRUBINA DIRECTA con dos valores distintos según la hoja del
formato actual. Angelus todavía no ha confirmado cuál es el correcto (pregunta abierta en
`docs/ESTADO.md` que sigue bloqueando la validación clínica real de esta fase). Se sembró
**un valor de los dos** por cada uno — el más estándar clínicamente o el que no es un
error de tipeo evidente — y queda marcado "PENDIENTE DE CONFIRMAR" en el comentario del
service de siembra y en `docs/ESTADO.md`. **Ningún informe real debe usar estos rangos sin
que el laboratorio confirme el valor correcto.**

| Parámetro | Sembrado | Opción no usada | Motivo de la elección |
|---|---|---|---|
| GLICEMIA | 70 - 100 mg/dL | 70 - 110 mg/dL | Rango de ayuno más citado clínicamente |
| ÚREA | 20 - 45 mg/dL | 10 - 30 mg/dL | Rango de úrea (no BUN) más citado en formatos similares |
| CREATININA | 0,70 - 1,20 mg/dL | 0,50 - 1,30 mg/dL | Rango unisex más citado |
| ÁCIDO ÚRICO | 3,0 - 7,0 mg/dL | 3,4 - 70 mg/dL | La segunda es, con alta probabilidad, error de tipeo por 7,0 (nota de `04_HALLAZGOS_FORMATOS.md`) |
| BILIRRUBINA TOTAL | 0,10 - 1,20 mg/dL | 0,20 - 1,00 mg/dL | Rango "hasta 1,2" es el más común en laboratorios clínicos |
| BILIRRUBINA DIRECTA | 0,05 - 0,30 mg/dL | 0,01 - 0,50 mg/dL | Rango "0 - 0,3" es el más común en laboratorios clínicos |

**3. Resolución por sexo Y por edad, cada una con su propio ejemplo real/realista.**
- **Sexo:** HEMOGLOBINA usa dos filas — hombre 13,0-15,0 g/dL (el valor que trae el
  formato actual de Angelus) y mujer 12,0-16,0 g/dL (el valor que el propio
  `04_HALLAZGOS_FORMATOS.md` señala como clínicamente correcto, en la sección "Lo que los
  formatos NO revelan" — el formato actual usa 13,0-15,0 para ambos sexos, lo cual es
  incorrecto). Ambos confirmados/justificados por el propio documento de hallazgos.
- **Edad:** GLÓBULOS BLANCOS usa dos filas — recién nacido (0-28 días) y el resto
  (29 días en adelante, 4.500-10.000/mm3, el valor confirmado). El valor de recién nacido
  es **ilustrativo, no confirmado** (los rangos pediátricos/neonatales reales son,
  igual que en la Fase 05, una pregunta abierta al laboratorio) — sólo demuestra que el
  resolver filtra correctamente por `age_min_days`/`age_max_days`.

**4. `ReferenceRange` valida sus propios campos obligatorios por `range_type` con
`CheckConstraint`**, mismo criterio que `Parameter` en la Fase 05: `CLOSED` exige
`low`+`high`, `UPPER_BOUND` exige `high`, `LOWER_BOUND` exige `low`, `TOLERANCE` exige
`center`+`tolerance`, `QUALITATIVE` exige `expected_option`, `INTERPRETIVE` exige `bands`.
Se agrega además `age_min_days <= age_max_days`.

**5. `services/reference_resolver.py` sigue exactamente el algoritmo de
`docs/01_MODELO_DATOS.md`:** filtra por `parameter`, sexo (coincidente o `ANY`), el rango
etario que contiene la edad en días, y `condition`; ordena por `priority` descendente y
luego por el rango etario más estrecho; devuelve el primero o `None` si no hay
coincidencia (el informe imprime la celda de referencia vacía — documentado para
MONOCITOS/BASÓFILOS en el modelo de datos, Fase 10 en adelante).

## Alcance

**Incluye:**
- `ReferenceRange` en `apps/catalog/models.py` con sus `CheckConstraint`.
- `services/reference_resolver.py::resolve_reference_range()`.
- `services/seeding_reference_ranges.py` — siembra idempotente de los 4 exámenes nuevos
  (mínimos, sólo lo necesario) + las 17 filas de `ReferenceRange` (una por combinación
  parámetro/sexo/edad/condición necesaria para cubrir los 6 tipos).
- Management command `seed_reference_ranges` (vía `tenant_command`).
- Admin de solo consulta para `ReferenceRange`.
- Tests: constraints de `ReferenceRange`, resolución por sexo, resolución por edad,
  desempate por `priority`, `None` cuando no hay coincidencia, cobertura de los 6
  `range_type`, idempotencia de la siembra.

**No incluye (fases posteriores):**
- Aplicar el resolver durante la captura de resultados o marcar alto/bajo (Fase 10).
- Congelar `reference_used`/`reference_text` en `ResultValue` al validar (Fase 10).
- Resolver `bands` de `INTERPRETIVE` a un texto según el valor medido (Fase 10).
- El resto del catálogo real de Angelus más allá de lo que cada fase necesita.
- `Profile`/`ProfileTest` — si "Perfil lipídico" termina siendo un `Profile` que agrupa
  `Test`s en vez de un `Test` único, se decide en la Fase 08; aquí se modeló como un
  `Test` para tener algo real donde colgar rangos, sin bloquear esta fase por esa decisión.

## Tareas

1. Modelo `ReferenceRange` con sus `CheckConstraint`.
2. `services/reference_resolver.py::resolve_reference_range()`.
3. `services/seeding_reference_ranges.py`: 4 exámenes mínimos + 17 `ReferenceRange`.
4. Management command `seed_reference_ranges`.
5. Admin de consulta.
6. Tests: constraints + resolución (sexo, edad, priority, sin coincidencia) + siembra
   (cobertura de los 6 tipos + idempotencia).
7. Cierre: `docs/ESTADO.md`, ADR-016 en `docs/DECISIONES.md`.

## Criterios de salida

- [ ] `python manage.py makemigrations catalog` sin cambios pendientes tras aplicar.
- [ ] `python manage.py tenant_command seed_reference_ranges --schema=demo_uno` crea todo
      sin errores y es idempotente.
- [ ] Los 6 `range_type` están representados entre los `ReferenceRange` sembrados.
- [ ] `resolve_reference_range()` devuelve la fila correcta por sexo y por edad en días,
      y `None` cuando no hay coincidencia — cubierto por tests.
- [ ] `pytest -q` y `ruff check .` en verde.
- [ ] `docs/ESTADO.md` y ADR-016 actualizados.

## Riesgos y trampas

- **No confundir "rango cargado" con "rango confirmado".** Los 6 parámetros de la tabla
  de la decisión 2 y el rango de recién nacido de GLÓBULOS BLANCOS no deben usarse en un
  informe real hasta que Angelus los confirme.
- **`age_max_days__gte=age_days` en el filtro, no `__gt`** — un paciente con exactamente
  `age_min_days` o `age_max_days` de edad debe caer dentro del rango, no fuera.
- **Decimales, no floats** (regla 9 de `docs/03_CONVENCIONES.md`) — `low`/`high`/`center`/
  `tolerance` son `DecimalField`.

## Entrega sugerida

```
git add apps/catalog docs/roadmap/06_rangos_de_referencia.md docs/ESTADO.md \
    docs/DECISIONES.md TASKS.md
git commit -m "feat(catalog): rangos de referencia, resolucion por sexo y edad, 6 range_type (Fase 06)"
```
