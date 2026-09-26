# Fase 08 — Perfiles y lista de precios

**Depende de:** Fase 05 (catálogo) · **Modelo usado:** Opus (el índice sugería Haiku; la fase
terminó con decisiones de diseño — granularidad de exámenes, multimoneda, descuentos)
**Criterio de salida (roadmap):** Los 13 perfiles de Angelus cargados — leído según ADR-018:
el sistema representa esos 13 **y más**, configurable por tenant.

## Decisiones tomadas con Darwin al iniciar

1. **Un perfil agrupa exámenes individuales** (Perfil lipídico = colesterol + triglicéridos
   + HDL + LDL/VLDL + índices). Se separaron los exámenes agregados de las Fases 06/07
   (`QUIM`, `PERFIL_LIPIDICO`, `COAGUL`) en exámenes ordenables; los códigos de parámetro no
   cambian, así que fórmulas y rangos siguen intactos.
2. **Composición de los perfiles: desde los Excel** (`Perfiles.xlsx`, `Formato de resultados -
   Angelus.xlsx`, adjuntados por Darwin), con libertad para agregar o ajustar.
3. **Multimoneda + tasa de cambio**: monedas por tenant con una moneda base, tasas por fecha,
   cada lista de precios en su moneda, total convertible a la moneda de cobro.
4. **Precio de perfil: fijo, o suma de exámenes menos %** — el laboratorio elige por perfil
   y por lista.

## Hallazgos al leer las celdas de los Excel

- **Superficie corporal: Mosteller confirmado.** La celda es `=SQRT((talla*peso)/3600)`.
  Las 5 fórmulas de depuración reproducen los valores de la hoja a 12 decimales.
- **Bug del INR en la hoja:** `=RAZÓN^ISI` con ISI vacío → `RAZÓN^0 = 1`; el INR impreso es
  siempre 1. Biolife deja el INR vacío con motivo cuando falta el ISI.
- **Fórmula nueva:** HOMA-IR = glicemia × insulina basal / 405 (hoja P. GLICÉMICO), con 4
  bandas interpretativas. Total: 17 fórmulas, todas verificadas contra datos reales.
- **~55 exámenes** en las hojas (antes había 6). Contradicciones nuevas: LDH (90–510 vs. por
  sexo), insulina en "U/mL" (clínicamente µU/mL), insulina post-carga "40 – 230 U/mL"
  (no se sembró), ácido úrico en "g/dL" en el Preeclámptico.

## Alcance

**Incluye:**
- `catalog.Profile` / `catalog.ProfileTest` (orden por examen). `Test.price` eliminado: el
  precio vive sólo en `billing` (una fuente de verdad).
- `catalog/selectors/catalog_queries.py`: `profile_tests`, `active_profiles`,
  `tests_by_codes`, `calculation_input_tests` (exámenes que faltan para calcular, transitivo).
- `catalog/services/profiles.py`: `create_profile`, `set_profile_tests` (rechaza vacíos,
  repetidos, inactivos y perfiles sin los insumos de sus cálculos).
- `catalog/services/seeding_base_catalog.py`: **fuente única** del catálogo base (58 exámenes
  activos con URO, ~140 parámetros, ~85 rangos). `seeding_reference_ranges.py` y
  `seeding_formulas.py` quedan como envoltorios de compatibilidad.
- `catalog/services/seeding_profiles.py` + command `seed_profiles`: 15 perfiles (14 de hojas
  + prenatal).
- App nueva **`apps.billing`**: `Currency`, `ExchangeRate`, `PriceList`, `PriceListItem`,
  `Discount`; services `exchange`, `price_lists` (fijar precio, ajuste masivo con redondeo,
  copia a otra moneda, reordenar, lista predeterminada), `quoting.quote()`; selectors;
  commands `seed_billing` y `ajustar_precios`; admin completo.
- Tests: 42 nuevos (149/149).

**No incluye:**
- Precios reales (pregunta abierta: no se inventan). `seed_billing` crea USD/VES y la lista
  GENERAL **vacía**.
- Tasa BCV automática (hoy: carga manual o `register_exchange_rate`).
- Perfiles anidados (perfil dentro de perfil).
- UI propia (fuera del admin) para precios y perfiles — llega con la UI de órdenes.
- Congelar precios en la orden (Fase 09 llama a `quote()` y guarda el resultado).

## Criterios de salida

- [ ] `migrate_schemas` aplica `catalog.0005` y `billing.0001` en los 3 tenants.
- [ ] `makemigrations --check --dry-run` → "No changes detected".
- [ ] `tenant_command seed_profiles --schema=demo_uno` dos veces sin errores (15 perfiles).
- [ ] `tenant_command seed_billing --schema=demo_uno` sin errores.
- [ ] `pytest -q` → 149 passed; `ruff check .` limpio.
- [x] Los 13 perfiles de las hojas cargados (14 con las dos variantes del glicémico), ninguno
      sin los insumos de sus cálculos (test `test_ningun_perfil_queda_sin_insumos...`).

(Verificados por Claude en Postgres 16 limpio y sobre un tenant con datos de la Fase 07;
falta la corrida en la máquina de Darwin.)

## Riesgos y trampas

- **Reglas de cobro:** un examen se cobra una vez aunque venga en dos perfiles (crédito al
  segundo perfil por el precio individual). Si el examen repetido no tiene precio
  individual, no hay crédito y queda un aviso.
- **Siembra no destructiva:** `seed_profiles` no toca perfiles existentes y
  `seed_base_catalog` no pisa fórmulas/nombres editados por el tenant; sólo muda parámetros
  que sigan en los exámenes agregados viejos.
- **Rangos de lípidos con condición `AYUNO`** (heredado de la Fase 06): el resolver con la
  condición por defecto (`NINGUNA`) no los encuentra. Decidir en la Fase 10.

## Entrega sugerida

```
git add apps/catalog apps/billing config/settings/base.py docs TASKS.md
git commit -F commit_msg.txt
```
