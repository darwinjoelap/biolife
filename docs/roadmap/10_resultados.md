# Fase 10 — Captura y validación de resultados

**Depende de:** 07, 09 · **Modelo usado:** Opus · **Criterio de salida:** captura con cálculo
en vivo, marcado alto/bajo, validación que congela referencias.

## Decisiones (Darwin, 2026-09-27)

- **ISI por lote de reactivo:** modelo `ReagentLot` con un solo lote vigente de
  tromboplastina; el INR usa su ISI y el resultado copia lote e ISI.
- **Valores críticos:** umbrales por rango (sexo/edad) en la ficha del examen; se siembran
  los de uso común marcados **PROPUESTO**, editables por el laboratorio.
- **Toma previa:** se puede cargar un resultado sin el tubo marcado como tomado, **con aviso**.

## Qué se hizo

- [x] Catálogo: `ReferenceRange.critical_low/high/note` (en el admin, sección «Valores
  críticos»), `ReagentLot` (admin con acción «Marcar como lote vigente»), siembra
  `seed_criticos` (13 rangos; no toca neonatos ni lo cargado por el laboratorio).
- [x] App `apps.results`: `Result` (1:1 con el examen de la orden), `ResultValue`,
  `CriticalNotification`.
- [x] Lectura de valores por tipo: coma decimal y punto de miles (`150.000`, `13,4`),
  calificadores (`< 0,5`), conteos (`0 - 2`, `INCONTABLES`), opciones, multi-selección,
  narrativos.
- [x] Marcas: crítico primero; alto/bajo por rango cerrado o límite; tolerancia (± 6 s);
  cualitativo distinto al esperado = anormal; bandas interpretativas (HOMA, HbA1c,
  procalcitonina) con su texto; opción «patológica» sin rango = anormal.
- [x] Cálculo en vivo con el motor de fórmulas (CHCM, lípidos, globulinas, bilirrubina
  indirecta, INR con el ISI del lote, depuración con peso/talla/orina de la orden, HOMA).
- [x] Rangos por sexo + edad en días + **condición del paciente** (embarazo; si no hay
  rango para la condición, se usa el general).
- [x] Validación: exige todos los parámetros obligatorios; bloquea valores críticos sin
  aviso confirmado **del mismo valor**; doble validación opcional (quien valida ≠ quien
  cargó, `TenantSettings.require_second_validation`); recalcula y **congela** rango y texto.
  Validado = inmutable, incluidos los insumos de un calculado validado.
- [x] Avance de la orden: En proceso → Resultados cargados → Validada.
- [x] Pantallas: bandeja *Resultados* (por cargar / por validar / validados, por sección y
  búsqueda), captura por orden (datos del paciente, lote de ISI, marcas y referencias en
  vivo, valor anterior del paciente, Enter = siguiente campo), aviso de críticos, validar por
  examen o todo lo cargado. Inicio muestra «Por validar».
- [x] Permisos: cargan técnico, bioanalista y administrador; validan quienes tienen
  `puede_validar_resultados` (bioanalista, administrador).
- [x] **Observaciones por examen** (ADR-026): cada examen tiene su observación (se imprime
  debajo de él) y una nota interna (no se imprime); botones con las predefinidas del examen,
  su sección y generales (`seed_observaciones`, 16 textos de las hojas); `__` queda
  seleccionado para escribir. Admin → *Observaciones predefinidas*.
- [x] Tests: +35 (246 en total).

## Verificación en la máquina de Darwin (2026-09-27: OK, commits `f934aaf` y `bac4352`)

- [x] `migrate_schemas` (catalog.0008, orders.0002, results.0001) y `seed_criticos`;
  243 passed (verificado por Darwin, antes de agregar las observaciones).
- [x] `migrate_schemas` (catalog.0009, results.0002) y `seed_observaciones` (16 textos).
- [ ] Admin → *Lotes de reactivos*: crear un lote de tromboplastina con su ISI y marcarlo
  vigente.
- [x] `pytest -q` → 246 passed · `ruff check .` limpio.
- [x] `runserver`: en una orden con tubos tomados → *Resultados*: cargar hematología,
  electrolitos (potasio 6,8 = crítico), perfil lipídico y PT; ver marcas y calculados al
  escribir; registrar el aviso del crítico; validar.

## No incluye

- Informe PDF, firma y QR (Fase 11). Rectificaciones de un validado (Fase 15).
- Reglas de delta (alertar si cambia mucho respecto al anterior): hoy sólo se muestra el
  valor anterior.
- Críticos confirmados por el laboratorio: los sembrados son propuestos.
