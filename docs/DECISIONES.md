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


## ADR-010 — `User` personalizado (`accounts.User`) en vez de `auth.User`
**Fecha:** 2026-09-20 · **Estado:** Aceptada

**Contexto.** `docs/02_ESTRUCTURA_PROYECTO.md` lista `User` como modelo propio dentro de
`apps/accounts/`, pero la Fase 01 había migrado `django.contrib.auth` con su `User` por
defecto en los tenants demo. Adoptar un modelo propio permite campos específicos del
dominio (`phone`, `professional_license`) sin depender de un `Profile` aparte, y es
coherente con la documentación de arquitectura.

**Decisión.** `AUTH_USER_MODEL = "accounts.User"`, extendiendo `AbstractUser`. Como
consecuencia, hubo que **recrear la base de datos local completa** (`dropdb`/`createdb`)
porque `public`, `demo_uno` y `demo_dos` ya tenían el historial de migraciones de `auth`
aplicado con el `User` por defecto — no hay forma limpia de cambiar `AUTH_USER_MODEL`
sobre un historial de migraciones ya aplicado sin recrear el esquema. Al ser sólo datos
de prueba, no hubo pérdida real.

**Consecuencias.**
- Cualquier referencia a un usuario en el código usa `"accounts.User"` (string) o
  `django.contrib.auth.get_user_model()`, nunca `django.contrib.auth.models.User`
  directamente — esa tabla ya no se migra.
- `TenantBaseModel.created_by` apunta a `"accounts.User"` (Fase 02, Tarea 7).
- Cambiar `AUTH_USER_MODEL` de nuevo en el futuro, con datos reales en producción, sería
  una migración de datos mayor — **no se vuelve a tocar sin ADR nuevo**.

---

## ADR-011 — `apps.accounts` es SHARED_APP y TENANT_APP a la vez
**Fecha:** 2026-09-20 · **Estado:** Aceptada

**Contexto.** `django.contrib.admin` (SHARED_APP, vive en `public` para el panel de
Django admin) depende de `AUTH_USER_MODEL` a través de
`migrations.swappable_dependency(settings.AUTH_USER_MODEL)`. Con `apps.accounts` sólo en
`TENANT_APPS`, `public` nunca migra `accounts`, y `admin.0001_initial` no puede resolver
su dependencia — error real encontrado: `InconsistentMigrationHistory`.

**Decisión.** `apps.accounts` se agrega también a `SHARED_APPS`, exactamente el mismo
patrón que ya usan `auth`, `contenttypes`, `sessions` y `messages` en este proyecto: la
app migra tanto en `public` como en cada esquema de tenant, cada uno con su propia tabla
de usuarios independiente.

**Consecuencias.**
- `public` tiene su propia tabla `accounts_user`, hoy usada sólo por el superusuario de
  `/admin/` (`darwinjoelap`). No se cruza con los usuarios de los tenants — aislamiento
  intacto, es la misma garantía que ya vale para `auth` desde la Fase 01.
- El `PlatformUser` de la Fase 12 (`SUPERADMIN_PLATAFORMA`) seguirá siendo un modelo
  aparte, no reutiliza esta tabla — ver nota de alcance en
  `docs/roadmap/02_usuarios_roles_auditoria.md`.
- Cualquier app nueva que dependa de `AUTH_USER_MODEL` y deba ser visible desde `public`
  (paneles de superadmin, por ejemplo) debe seguir este mismo patrón dual, no asumir que
  "tenant app" basta.


---

## ADR-012 — `TenantTimezoneMiddleware` se muda de `apps.core` a `apps.settings_lab`
**Fecha:** 2026-09-26 · **Estado:** Aceptada

**Contexto.** El middleware necesita leer la zona horaria real del laboratorio desde
`TenantSettings`, un modelo de `apps.settings_lab`. `CLAUDE.md` es explícito:
*"`core/` puede ser importado por todos; `core/` no importa a nadie."* Dejarlo en
`apps.core` habría forzado a `core` a importar `settings_lab`, rompiendo esa regla.

**Decisión.** `TenantTimezoneMiddleware` vive en `apps.settings_lab.middleware`.
`apps/core/middleware.py` queda vacío (con nota explicando la mudanza), y
`config/settings/base.py::MIDDLEWARE` apunta al nuevo path.

**Corrección real encontrada durante la implementación (no estaba en el roadmap
original de la Fase 03).** El middleware, tal como estaba especificado, llamaba a
`TenantSettings.get_solo()` incondicionalmente en cada request. Como `apps.settings_lab`
es `TENANT_APP` y no `SHARED_APP`, la tabla `settings_lab_tenantsettings` **no existe**
en el esquema `public` — el middleware habría roto con `relation does not exist` en
*cualquier* request al dominio `localhost` (incluido `/admin/`), ya que el `MIDDLEWARE`
corre para todos los esquemas, sin importar qué `ROOT_URLCONF`/`PUBLIC_SCHEMA_URLCONF`
se use después. Se agregó una guarda: si `request.tenant.schema_name ==
get_public_schema_name()`, el middleware activa `settings.TIME_ZONE` en vez de tocar
`TenantSettings`. Verificado en navegador: `/admin/` en `localhost` sigue funcionando
después del cambio, y cubierto por test (`test_middleware_usa_time_zone_por_defecto_en_public`).

**Consecuencias.**
- Cualquier middleware o vista que dependa de un modelo `TENANT_APP`-only debe aplicar la
  misma guarda de esquema `public` — no asumir que el request siempre trae un tenant real.
- El `MIDDLEWARE` en `base.py` debe actualizarse junto con cualquier mudanza futura de
  este tipo; verificar siempre con `manage.py check` **y** una visita real a `/admin/`
  en `localhost`, no solo al dominio de un tenant.

---

## ADR-013 — Cloudinary diferido a la Fase 17; storage local mientras tanto
**Fecha:** 2026-09-26 · **Estado:** Aceptada

**Contexto.** Darwin tiene credenciales de Cloudinary reutilizables de otros proyectos y
preguntó si convenía integrarlas ahora, o incluso adelantar el despliegue a Railway antes
de continuar con el roadmap. Se evaluaron las tres opciones (Cloudinary ahora, Railway
ahora, seguir el roadmap sin adelantos) y **Darwin decidió no adelantar ninguna de las
dos**: sin credenciales de producción reales ni un despliegue real donde probarlas, cablear
Cloudinary ahora sería trabajo especulativo.

**Decisión.** `TenantSettings.logo`/`banner` son `ImageField` con el storage local de
Django (`MEDIA_ROOT`/`MEDIA_URL`, servidos en `DEBUG` desde `urls_tenant.py`). La
integración real con Cloudinary queda para la **Fase 17** (despliegue), cuando haya
credenciales de producción y un entorno real donde validarlas. El despliegue a Railway
tampoco se adelanta — se sigue el orden del roadmap.

**Consecuencias.**
- Cambiar el storage de un `ImageField` más adelante no exige tocar el modelo ni generar
  una migración nueva — sólo `DEFAULT_FILE_STORAGE`/`STORAGES` en `production.py`
  (Fase 17).
- Mientras tanto, los logos/banners subidos en desarrollo viven en `media/` local y no
  sobreviven un `dropdb`/recreación de esquema del mismo modo que los datos de BD (son
  archivos en disco, no filas) — sin impacto real hoy porque son solo datos de prueba.
- No se instala `django-cloudinary-storage` ni se agregan sus credenciales a `.env`
  hasta la Fase 17 — evita dependencias y configuración sin uso real.


---

## ADR-014 — Formato de `internal_code`, contador con `select_for_update()` y ubicación de `lab_initials`
**Fecha:** 2026-09-26 · **Estado:** Aceptada

**Contexto.** Cada paciente necesita un código interno único, legible y corto que el
personal de recepción pueda usar en papel/etiquetas sin depender del UUID interno. Se
evaluaron con Darwin el formato exacto y el criterio de reinicio del correlativo.

**Decisión.**
- Formato `{YY}{iniciales_lab}{correlativo:06d}` — ej. `26LDU000001` (año con los dos
  últimos dígitos, siglas del laboratorio, correlativo de 6 dígitos con ceros a la
  izquierda). El correlativo **reinicia en 1 cada año** — el año va embebido en el propio
  código, así que dos años distintos nunca chocan aunque ambos empiecen en `000001`.
- El contador vive en `PatientCodeSequence` (`year` único + `last_value`), un modelo
  auxiliar plano — **no** hereda `TenantBaseModel`, mismo criterio ya usado para
  `Role`/`Membership`/`AuditLog` en `apps.accounts`: es plumbing interno, no un registro
  de dominio con auditoría/soft-delete propios.
- `generate_internal_code()` usa `select_for_update()` + `transaction.atomic()` sobre la
  fila de `PatientCodeSequence` del año actual, para que dos registros de paciente
  simultáneos (dos recepcionistas al mismo tiempo) nunca obtengan el mismo correlativo.
- `lab_initials` vive en `TenantSettings` (config del laboratorio, `apps.settings_lab`) y
  no en `Tenant` (`apps.tenants`, esquema `public`): las siglas son un dato operativo del
  laboratorio que su propio personal administra desde el admin de su tenant, no un dato de
  plataforma/facturación que gestione Biolife. Consistente con por qué `TenantSettings` no
  tiene FK a `Tenant` (ADR de la Fase 03): ya vive aislado dentro del esquema del tenant.

**Consecuencias.**
- Un laboratorio sin `lab_initials` configurado no puede registrar pacientes:
  `generate_internal_code()` lanza `ApplicationError` explícito en vez de generar un
  código con siglas vacías o inventadas — obliga a completar la configuración primero.
- Cambiar las siglas de un laboratorio ya en producción no reescribe los `internal_code`
  ya emitidos (son inmutables, `editable=False`) — solo afecta a los pacientes nuevos.
- El límite de 999.999 pacientes nuevos por año por laboratorio se considera no
  alcanzable en la práctica para el tamaño de cliente objetivo; no se diseñó manejo de
  overflow.
- Cubierto por tests (`test_code_sequence.py`): correlativos consecutivos dentro del
  mismo año, y aislamiento entre años (un `PatientCodeSequence` de un año anterior con
  valor alto no afecta el correlativo del año actual).


---

## ADR-015 — Catálogo sembrado directo por tenant; Master*+copia pospuesto
**Fecha:** 2026-09-26 · **Estado:** Aceptada

**Contexto.** `docs/01_MODELO_DATOS.md` (sección A) describe catálogos maestros
(`MasterSection`/`MasterUnit`/`MasterMethod`/`MasterAnalyte`) en el esquema `public` que se
"copiarían" a cada tenant nuevo al aprovisionarlo, además de las tablas `Section`/`Unit`/
`Method`/`Test`/`Parameter` propias de cada tenant. Con un solo laboratorio real (Angelus)
por ahora, construir el mecanismo completo de maestros + copia es trabajo especulativo: no
hay un segundo tenant real que lo necesite, y su diseño correcto (qué pasa si un tenant
personaliza un `Test` copiado y el maestro cambia después) depende de decisiones de producto
que no se han tomado.

**Decisión.** Se implementó únicamente el lado tenant del modelo (`apps.catalog`:
`Section`, `Unit`, `Method`, `Test`, `ParameterGroup`, `Parameter`, `CodedOptionSet`,
`CodedOption`), sembrado directo por tenant vía `services/seeding.py` + management command
(mismo patrón que `seed_system_roles()` en `apps.accounts`, Fase 02). El mecanismo
`Master*` + copia al aprovisionar queda **pospuesto** para cuando se incorpore un segundo
laboratorio real y haya un caso concreto que lo justifique.

**Decisión relacionada — cobertura de los 9 `value_type` en un solo examen.** El criterio
de salida de la fase ("Uroanálisis completo cargado con sus 9 tipos de valor") exige que
un único `Test` ejercite los 9 valores de `Parameter.value_type`. El uroanálisis real de
Angelus no trae de forma confirmada un parámetro `NUMERIC_CALCULATED` ni uno
`MULTI_CATALOG` (ese tipo sólo aparece en heces/parásitos en los formatos reales). Se
agregaron parámetros plausibles pero **no confirmados por el laboratorio** —
`PROTEÍNA EN ORINA`/`CREATININA EN ORINA`/`ÍNDICE PROTEÍNA/CREATININA` (numérico y
calculado) y `CRISTALES EN SEDIMENTO` (multi-catálogo), además de un `RECUENTO
BACTERIANO (screening)` ilustrativo para `TITER` (en la práctica parte de un urocultivo, no
del uroanálisis de rutina) — marcados explícitamente como tales en
`docs/roadmap/05_catalogo_examenes.md` y en el docstring de `seed_uroanalisis()`.

**Decisión relacionada — validación en `CheckConstraint`, no en el service.** A diferencia
de la regla de representante legal de pacientes (Fase 04, que depende de una relación que
aún no existe al validar), las reglas de `Parameter` sólo dependen de sus propios campos, así
que se expresan como `CheckConstraint` de base de datos: `option_set` obligatorio para
`CODED`/`SEMIQUANTITATIVE`/`QUALITATIVE`/`TITER`/`MULTI_CATALOG`, y `formula` obligatorio
para `NUMERIC_CALCULATED`.

**Consecuencias.**
- Cargar el catálogo completo de un segundo laboratorio real hoy significa escribir un
  nuevo `services/seeding.py` para ese tenant (o adaptar el de Angelus) — no hay
  reutilización automática entre tenants todavía. Aceptable con un solo cliente.
- Ningún parámetro marcado "no confirmado" debe imprimirse en un informe real hasta que
  Angelus lo confirme — queda como pendiente explícito en `docs/ESTADO.md`.
- `Parameter.depends_on` (M2M a sí mismo) se deja vacío: resolver automáticamente las
  dependencias a partir de `formula` es trabajo de la Fase 07 (motor de fórmulas).
- Cuando se decida construir Master*+copia, el trabajo de esta fase no se pierde: las
  tablas tenant (`Section`/`Unit`/.../`Parameter`) son exactamente las que un mecanismo de
  copia poblaría; sólo faltaría agregar el origen `Master*` en `public` y el paso de copia
  en `provision_tenant()`.
