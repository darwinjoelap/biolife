# Fase 08b — Ficha del examen: rangos por sexo, edad y condición

**Depende de:** Fase 06 (rangos) y 08 · **Modelo usado:** Opus
**Origen:** pedido de Darwin al cerrar la Fase 08 — que cada examen tenga su ficha donde el
laboratorio ajuste los rangos por edad y sexo. ("Perfil" ya significa grupo de exámenes;
por eso se llama **ficha del examen**.)

## Decisión con Darwin

La **lógica** se hace ahora (no depende del diseño) y se engancha en el **admin de Django**
como pantalla provisional. La pantalla definitiva se hace en la fase de **estilo visual y
pantallas base** (pendiente de ubicar en el roadmap, antes de la primera pantalla real) y
reutiliza los mismos services.

## Qué se hizo

- `core/utils/dates.py`: `age_parts_to_days`, `days_to_age_parts`, `format_age_days`
  (año = 365,25 días, mes = 1/12 de año; ida y vuelta exacta; "12 meses" = "1 año").
- `catalog/services/reference_range_management.py`:
  - `find_range_issues()` — **ERROR** si dos rangos se solapan con igual sexo compatible,
    condición, prioridad y ancho (no hay cómo decidir); **AVISO** si se solapan con ancho
    distinto (gana el más estrecho) y por **huecos** de edad/sexo sin rango (el informe
    imprimiría la referencia vacía). Los huecos se revisan por condición y sólo para los
    sexos que el parámetro cubre en esa condición.
  - `parameter_range_issues()` y `explain_resolution()` (probador: qué rango aplica y por qué
    se descartan los demás; el elegido es siempre el de `resolve_reference_range()`).
- `resolve_reference_range()` ahora ignora rangos desactivados (`is_active=False`).
- Admin (provisional):
  - **Ficha del examen** (`Examen`): cada parámetro muestra sus rangos y "Editar rangos →".
  - **Ficha del parámetro**: rangos en línea con edad en años/meses/días, "Hasta" exclusivo
    y vacío = sin límite; valida campos por tipo de rango; bloquea ERROR, muestra AVISOS al
    guardar; "Cobertura de rangos"; enlace al **probador**.
  - La opción esperada (cualitativos) se limita al conjunto de opciones del parámetro.
- **Bug corregido:** `django.contrib.admin` estaba sólo en `SHARED_APPS`; guardar en el
  admin de un laboratorio escribía la bitácora en `public` con un usuario que allí no existe
  (error de clave foránea, o peor, el id de otro usuario). Ahora también es `TENANT_APP` y
  `accounts.0004_admin_log_por_tenant` crea la tabla en los tenants existentes.
- Tests: 22 nuevos (171/171), incluido un guardado real por el admin.

## No incluye

- Pantalla definitiva con el estilo del sistema (fase de estilo visual).
- Historial de cambios de rangos visible en la ficha (la bitácora del admin sí lo registra;
  los resultados validados ya congelan su rango, ADR-005).
- Rangos críticos/de pánico (siguen como pregunta abierta).

## Criterios de salida

- [ ] `migrate_schemas` aplica `accounts.0004_admin_log_por_tenant` en los 3 tenants.
- [ ] `pytest -q` → 171 passed; `ruff check .` limpio.
- [ ] En `/admin/` de `demo_uno`: abrir un examen → "Editar rangos" → agregar un rango de
      recién nacido y guardar (debe mostrar AVISO) → "Probar qué rango aplica".

## Entrega sugerida

```
git add apps/core apps/accounts apps/catalog config/settings/base.py docs TASKS.md
git commit -F commit_msg.txt
```
