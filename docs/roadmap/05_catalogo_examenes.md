# Fase 05 — Catálogo: secciones, unidades, parámetros

**Depende de:** Fase 03 (`TenantSettings`) · **Modelo sugerido:** Sonnet
**Criterio de salida (roadmap):** Uroanálisis completo cargado con sus 9 tipos de valor.

## Objetivo

Construir el motor de catálogo de exámenes (`Section`, `Unit`, `Method`, `Test`,
`ParameterGroup`, `Parameter`, `CodedOptionSet`, `CodedOption` — sección D de
`docs/01_MODELO_DATOS.md`) y demostrarlo cargando un examen real completo: **Uroanálisis**,
ejercitando los 9 `value_type` que el modelo soporta.

Este catálogo es la base de las Fases 06 (rangos de referencia), 07 (motor de fórmulas),
08 (perfiles) y 09 (órdenes) — pero **esas fases no se tocan aquí**. Fase 05 sólo construye
la estructura y la siembra de un examen, no rangos de referencia, no perfiles ni precios
reales.

## Contexto y decisiones tomadas antes de implementar

**1. Catálogos maestros (public) — pospuestos.** `docs/01_MODELO_DATOS.md` (sección A)
describe `MasterSection`/`MasterUnit`/`MasterMethod`/`MasterAnalyte` en el esquema `public`
que se "copiarían" a cada tenant nuevo. Con un solo laboratorio real (Angelus), ese
mecanismo es trabajo especulativo: se decidió **sembrar el catálogo directo en cada tenant**
(service + management command, mismo patrón que `seed_system_roles()` en
`apps.accounts`), y dejar Master*+copia documentado como pendiente para cuando se
incorpore un segundo laboratorio real (ver ADR-015).

**2. Cobertura de los 9 `value_type` en un solo examen.** El uroanálisis real de Angelus
(según `docs/04_HALLAZGOS_FORMATOS.md`) no trae de forma confirmada un parámetro calculado
(`NUMERIC_CALCULATED`) ni uno de selección múltiple (`MULTI_CATALOG` — en los formatos sólo
aparece en heces/parásitos, no en orina). Se decidió **agregar parámetros plausibles pero no
confirmados por el laboratorio** para cubrir los tipos faltantes, marcados explícitamente
como tales en este documento y en el `help_text`/docstring del service de siembra. **Ningún
parámetro no confirmado debe imprimirse en un informe real hasta que Angelus lo confirme.**

Parámetros de Uroanálisis **no confirmados**, agregados sólo para ejercitar el `value_type`:
- `PROTEÍNA EN ORINA (cuantitativa)` y `CREATININA EN ORINA` (`NUMERIC`) + `ÍNDICE
  PROTEÍNA/CREATININA` (`NUMERIC_CALCULATED`, `formula = "PROT_ORINA / CREAT_ORINA"`).
- `CRISTALES EN SEDIMENTO` (`MULTI_CATALOG`, catálogo típico: oxalato de calcio, ácido
  úrico, fosfatos amorfos, uratos amorfos, triple fosfato, cistina).
- `RECUENTO BACTERIANO (screening)` (`TITER`, 3 escalones: <10.000 / 10.000–100.000 /
  >100.000 UFC/mL) — en la práctica esto es parte de un urocultivo, no del uroanálisis de
  rutina; se incluye aquí sólo como ejemplo ilustrativo del tipo `TITER` fuera de
  PCR/VDRL, que pertenecen a otros exámenes.

Todo lo demás (color, aspecto, olor, densidad, pH, químico por tiras reactivas, sedimento)
viene directo de `docs/04_HALLAZGOS_FORMATOS.md` secciones 1 y 5.

**3. `DENSIDAD` y `pH` de orina como `CODED`, no `NUMERIC`.** El propio
`04_HALLAZGOS_FORMATOS.md` (nota bajo la sección 5) ya resuelve esta aparente contradicción
con la sección 1: se modelan como `CODED` con `numeric_equivalent` poblado (reflejan los
escalones fijos de la tira reactiva), no como `NUMERIC` de rango abierto.

**4. `depends_on` (M2M de `Parameter` a sí mismo) se deja vacío por ahora.** Resolver
automáticamente las dependencias a partir del texto de `formula` es trabajo de la Fase 07
(motor de fórmulas). Aquí sólo se guarda `formula` como texto.

**5. Validación de reglas del catálogo: en `CheckConstraint`, no en el service.** A
diferencia de la regla de representante legal (Fase 04, que necesita consultar una relación
que no existe aún), las reglas de `Parameter` sólo dependen de sus propios campos
(`value_type`, `option_set`, `formula`), así que se expresan como `CheckConstraint` de base
de datos:
  - Si `value_type` es `CODED`/`SEMIQUANTITATIVE`/`QUALITATIVE`/`TITER`/`MULTI_CATALOG` →
    `option_set` es obligatorio.
  - Si `value_type` es `NUMERIC_CALCULATED` → `formula` no puede estar vacío.

## Alcance

**Incluye:**
- App `apps.catalog` (TENANT_APP): `Section`, `Unit`, `Method`, `Test`, `ParameterGroup`,
  `Parameter`, `CodedOptionSet`, `CodedOption`.
- `apps/catalog/services/seeding.py::seed_uroanalisis()` — siembra idempotente
  (`get_or_create` por `code`) de todo el árbol Sección→Test→Grupos→Parámetros→Opciones.
- Management command `seed_uroanalisis` (ejecutable vía
  `python manage.py tenant_command seed_uroanalisis --schema=<tenant>`).
- Admin de solo-lectura/consulta para los 8 modelos (sin flujo de edición todavía — la UI
  de mantenimiento de catálogo es de una fase posterior).
- Tests: constraints de `Parameter` (option_set/formula obligatorios según `value_type`),
  `seed_uroanalisis()` crea exactamente 1 `Test`, cubre los 9 `value_type`, es idempotente.

**No incluye (fases posteriores):**
- `ReferenceRange` (Fase 06).
- `Profile`/`ProfileTest`, precios reales (Fase 08).
- `ObservationTemplate` (se deja para cuando se construya la captura de resultados,
  Fase 10, que es donde realmente se usa).
- Motor de fórmulas / resolución de `depends_on` (Fase 07).
- Vistas, formularios, URLs de mantenimiento de catálogo (posterior, junto con el resto de
  la UI de administración operativa).
- Mecanismo Master*+copia al aprovisionar (pospuesto, ver decisión 1 arriba).
- Sembrar el resto de los exámenes reales de Angelus (hematología, química, heces,
  serología, coagulación) — Uroanálisis es la prueba de concepto de esta fase; el resto se
  siembra fase a fase según se necesite (ligado a Fase 06/07/08).

## Tareas

1. App `apps.catalog` + modelos base: `Section`, `Unit`, `Method`, `CodedOptionSet`,
   `CodedOption`.
2. Modelos `Test`, `ParameterGroup`, `Parameter` con los `CheckConstraint` de la decisión 5.
3. `services/seeding.py::seed_uroanalisis()` — construye el árbol completo con datos de
   `docs/04_HALLAZGOS_FORMATOS.md` + los parámetros no confirmados de la decisión 2.
4. Management command `seed_uroanalisis`.
5. Admin de consulta (`list_display`/`search_fields`, sin lógica de negocio).
6. Tests: constraints + siembra (cobertura de los 9 tipos + idempotencia).
7. Cierre: `docs/ESTADO.md`, ADR-015 en `docs/DECISIONES.md`.

## Criterios de salida

- [ ] `python manage.py makemigrations catalog` sin cambios pendientes tras aplicar.
- [ ] `python manage.py tenant_command seed_uroanalisis --schema=demo_uno` crea el examen
      completo sin errores y es idempotente (correrlo dos veces no duplica nada).
- [ ] Los 9 `value_type` están representados entre los parámetros del `Test` "URO".
- [ ] `pytest -q` y `ruff check .` en verde.
- [ ] `docs/ESTADO.md` y ADR-015 actualizados.

## Riesgos y trampas

- **No confundir "catálogo cargado" con "catálogo confirmado".** Los parámetros marcados
  como no confirmados en la decisión 2 deben quedar visibles como tales (comentario en el
  service, y en `docs/ESTADO.md`) para que nadie los imprima en un informe real sin pasar
  primero por el laboratorio.
- **`CodedOption.numeric_equivalent`** para `DENSIDAD_ORINA`/`PH_ORINA` debe guardarse como
  `Decimal`, no float (regla 9 de `docs/03_CONVENCIONES.md`).
- **Idempotencia de la siembra.** `seed_uroanalisis()` debe poder correrse varias veces
  sobre el mismo tenant sin crear duplicados — usar `get_or_create` por el campo `code`
  natural de cada modelo, no por PK (los PK son UUID generados, no sirven como clave
  natural para idempotencia).

## Entrega sugerida

```
git add apps/catalog config/settings/base.py docs/roadmap/05_catalogo_examenes.md \
    docs/ESTADO.md docs/DECISIONES.md TASKS.md
git commit -m "feat(catalog): motor de catalogo de examenes, uroanalisis con los 9 tipos de valor (Fase 05)"
```
