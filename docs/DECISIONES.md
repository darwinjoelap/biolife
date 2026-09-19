# DECISIONES (ADR ligero)

**Append-only.** Nunca se edita ni se borra una entrada. Si una decisión se revierte, se
agrega una entrada nueva que la supersede y se marca la anterior con `SUPERSEDIDA POR ADR-NNN`.

Formato: contexto → decisión → consecuencias.

---

## ADR-001 — Multi-tenancy por esquemas de PostgreSQL
**Fecha:** 2026-09-19 · **Estado:** Aceptada

**Contexto.** Biolife maneja historias clínicas de múltiples laboratorios independientes.
Se evaluaron tres estrategias: base de datos por tenant, esquema por tenant, y discriminador
`tenant_id` en tabla compartida.

**Decisión.** Esquema por tenant usando `django-tenants`, con enrutamiento por subdominio.

**Consecuencias.**
- Un `Model.objects.all()` sin filtro no puede exponer datos de otro laboratorio.
- Backup, exportación y eliminación por laboratorio son operaciones directas.
- Las migraciones corren N veces. Con muchos tenants requiere ventana de mantenimiento
  y `migrate_schemas --executor=multiprocessing`.
- **Restricción dura:** la conexión a PostgreSQL debe ser directa o en modo *session
  pooling*. Un pooler en modo *transaction* rompe el aislamiento silenciosamente.

---

## ADR-002 — El paquete del proyecto Django se llama `config`
**Fecha:** 2026-09-19 · **Estado:** Aceptada

**Contexto.** `django-admin startproject biolife .` crearía un paquete homónimo del producto.

**Decisión.** El paquete se llama `config`.

**Consecuencias.** `from biolife import ...` deja de ser ambiguo porque no existe. Las apps
viven todas bajo `apps/`.

---

## ADR-003 — `auto_drop_schema = False` en el modelo Tenant
**Fecha:** 2026-09-19 · **Estado:** Aceptada

**Contexto.** `django-tenants` permite borrar el esquema automáticamente al borrar el tenant.

**Decisión.** Queda en `False`. La eliminación de un esquema es un procedimiento manual
documentado, con respaldo previo obligatorio.

**Consecuencias.** Un borrado accidental desde el admin de Django deja el esquema huérfano
en lugar de destruir historias clínicas. La limpieza de esquemas huérfanos es una tarea
operativa periódica.

---

## ADR-004 — `display_text` obligatorio en los rangos de referencia
**Fecha:** 2026-09-19 · **Estado:** Aceptada

**Contexto.** Los formatos del laboratorio imprimen rangos con formato propio
("4.500 - 10.000/mm3"). Derivar ese texto desde los campos numéricos produce una cadena
distinta a la que el laboratorio espera ver.

**Decisión.** `ReferenceRange.display_text` es obligatorio y se imprime literal. Los campos
`low`/`high`/etc. sirven sólo para marcar alto/bajo y para graficar históricos.

**Consecuencias.** Duplicación controlada de información. A cambio, el informe reproduce
exactamente el formato actual del laboratorio, que es requisito de aceptación del cliente.

---

## ADR-005 — Congelado de referencias al validar un resultado
**Fecha:** 2026-09-19 · **Estado:** Aceptada

**Contexto.** Los rangos de referencia cambian con el tiempo (nuevo lote de reactivo,
corrección de un error). Un informe reimpreso años después debe mostrar el rango vigente
al momento del examen.

**Decisión.** Al validar, `ResultValue.reference_used` y `reference_text` se copian desde
el rango resuelto. La impresión nunca vuelve a resolver el rango.

**Consecuencias.** Reimpresiones históricas correctas. Coste: dos columnas adicionales por
valor de resultado.

---

## ADR-006 — Python 3.13 en lugar de 3.12
**Fecha:** 2026-09-19 · **Estado:** Aceptada

**Contexto.** La máquina de desarrollo de Darwin tiene Python 3.13 y 3.14 instalados, pero
no 3.12 (la versión originalmente fijada en `CLAUDE.md`). Django 5.1 soporta oficialmente
hasta Python 3.13; psycopg 3.2 también soporta 3.13. Python 3.14 se descarta por ser
demasiado reciente para confiar en la compatibilidad de `django-tenants` y del resto de
dependencias fijadas en `requirements/base.txt`.

**Decisión.** El proyecto usa **Python 3.13** en vez de 3.12, evitando instalar una versión
adicional. `django-admin startproject` y el venv se crean con `py -3.13`.

**Consecuencias.**
- `CLAUDE.md`, sección "Stack fijo", se actualiza a Python 3.13.
- Si durante la Fase 01 aparece algún error de compatibilidad achacable a 3.13 en
  `django-tenants==3.7.*` o `psycopg[binary]==3.2.*`, la mitigación es instalar 3.12
  explícitamente (`py -3.12`) y revertir este ADR con una entrada nueva que lo marque
  `SUPERSEDIDA POR ADR-007`.
- Sin impacto conocido en PostgreSQL, Cloudinary, Railway ni el resto del stack.
