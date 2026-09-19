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
documentado, con respaldo previo obligatorio. La única excepción es código de pruebas
explícito que llama `tenant.delete(force_drop=True)` para limpiar tenants temporales de
test — nunca el flujo normal de la aplicación ni el admin.

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
- Verificado en la Fase 01: `django-tenants==3.7.*`, `psycopg[binary]==3.2.*` y el resto de
  `requirements/base.txt` instalan y corren limpio en Python 3.13.7. El riesgo de
  compatibilidad anticipado no se materializó.
- Sin impacto conocido en PostgreSQL, Cloudinary, Railway ni el resto del stack.

---

## ADR-007 — `provision_tenant()` fuerza el esquema `public` internamente
**Fecha:** 2026-09-19 · **Estado:** Aceptada

**Contexto.** `django-tenants` exige crear un `Tenant` únicamente con la conexión activa en
el esquema `public` — si se invoca desde cualquier otro esquema, `Tenant.save()` lanza
`Exception("Can't create tenant outside the public schema")`. Esto se manifestó al escribir
los tests de la Fase 01 (`pytest-django` no garantiza que la conexión esté en `public` al
llamar al service), y es un riesgo real también en producción si `provision_tenant()` llega
a invocarse alguna vez desde un contexto de request ya resuelto a un tenant.

**Decisión.** `provision_tenant()` envuelve toda su lógica en
`with schema_context(get_public_schema_name())`, sin importar el esquema activo del llamador.

**Consecuencias.**
- El service es seguro de invocar desde cualquier contexto.
- Cualquier código que borre un tenant de prueba (`tenant.delete(force_drop=True)`) debe
  hacer el mismo `schema_context(get_public_schema_name())` explícito — no lo hace el
  modelo `Tenant` por sí solo.

---

## ADR-008 — Tests que crean/borran esquemas de tenant requieren `transaction=True`
**Fecha:** 2026-09-19 · **Estado:** Aceptada

**Contexto.** `@pytest.mark.django_db` (sin `transaction=True`) envuelve cada test en una
transacción que `pytest-django` revierte al final. Un `DROP SCHEMA ... CASCADE` ejecutado
dentro de esa transacción falla con `ObjectInUse: ... tiene eventos de disparador
pendientes`, porque los triggers de FK diferidos no se han resuelto todavía.

**Decisión.** Todo test que llame a `provision_tenant()` y luego borre el tenant
(`tenant.delete(force_drop=True)`) debe usar `@pytest.mark.django_db(transaction=True)`.
Los tests de aislamiento basados en `django_tenants.test.cases.TenantTestCase` no necesitan
este marcador — la clase ya maneja sus propias transacciones.

**Consecuencias.** Estos tests son más lentos (no hay rollback automático; cada uno limpia
su propio esquema explícitamente) pero son los únicos que reflejan correctamente el
comportamiento real de creación/eliminación de esquemas.

---

## ADR-009 — El esquema `public` necesita su propio `Tenant` + `Domain`
**Fecha:** 2026-09-19 · **Estado:** Aceptada

**Contexto.** `TenantMainMiddleware` busca un `Domain` para **cada** hostname entrante,
incluido `localhost` quien sirve el panel SuperAdmin y el admin de Django. Sin un `Tenant`
con `schema_name="public"` y un `Domain(domain="localhost")` asociado, cualquier request a
`localhost` devuelve 404 ("No tenant for hostname").

**Decisión.** Como parte del setup local (y del script de despliegue en Fase 17), se crea
explícitamente:
```python
tenant, _ = Tenant.objects.get_or_create(schema_name="public", defaults={"name": "Biolife Plataforma"})
Domain.objects.get_or_create(domain="localhost", tenant=tenant, defaults={"is_primary": True})
```
`Tenant.save()` no intenta crear el esquema `public` (ya existe) — es un caso especial que
`django-tenants` maneja internamente.

**Consecuencias.** Este paso debe repetirse (con el dominio real, no `localhost`) en cada
entorno nuevo — staging y producción — antes de que el panel SuperAdmin sea alcanzable.
Pendiente: automatizarlo como parte del script de despliegue de la Fase 17.
