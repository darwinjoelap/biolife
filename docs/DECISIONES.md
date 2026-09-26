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


---

## ADR-016 — Rangos de referencia: 4 exámenes mínimos nuevos, 6 parámetros pendientes de confirmar
**Fecha:** 2026-09-26 · **Estado:** Aceptada

**Contexto.** El criterio de salida de la Fase 06 exige que `ReferenceRange` demuestre
resolución por sexo y edad en días con los 6 `range_type` del modelo de datos (`CLOSED`,
`UPPER_BOUND`, `LOWER_BOUND`, `TOLERANCE`, `QUALITATIVE`, `INTERPRETIVE`). El Uroanálisis
sembrado en la Fase 05 sólo tiene datos naturales para `QUALITATIVE`; los demás tipos sí
tienen datos numéricos reales en `docs/04_HALLAZGOS_FORMATOS.md`, pero de exámenes que
todavía no existían en el catálogo (hematología, perfil lipídico, coagulación).

**Decisión — 4 exámenes nuevos, mínimos.** Se sembraron `HEM_COMP`, `PERFIL_LIPIDICO`,
`COAGUL` y `QUIM`, cada uno **sólo con los parámetros necesarios** para colgarles un
rango real (no la lista completa de cada examen — ver `services/seeding_reference_ranges.py`
y `docs/roadmap/06_rangos_de_referencia.md`). `QUALITATIVE` se resolvió reutilizando
`URO_NITRITOS` de la Fase 05, sin sembrar nada nuevo para ese tipo.

**Decisión — 6 parámetros con rango contradictorio, sembrados con un valor marcado
pendiente.** `docs/04_HALLAZGOS_FORMATOS.md` reporta GLICEMIA, ÚREA, CREATININA, ÁCIDO
ÚRICO, BILIRRUBINA TOTAL y BILIRRUBINA DIRECTA con dos valores distintos según la hoja del
formato. Angelus no ha confirmado cuál es el correcto (pregunta abierta, ver
`docs/ESTADO.md`). Se sembró un valor de cada par — el clínicamente más citado, o el que
no es un error de tipeo evidente (ácido úrico) — documentado con su justificación en
`docs/roadmap/06_rangos_de_referencia.md`. El `display_text` de cada uno incluye
"(PENDIENTE DE CONFIRMAR)" para que sea visible también en el admin, no sólo en el código.

**Decisión — sexo y edad, cada uno con su propio ejemplo.** HEMOGLOBINA demuestra
resolución por sexo con dos valores que el propio `04_HALLAZGOS_FORMATOS.md` documenta:
13,0-15,0 g/dL (lo que trae el formato actual de Angelus, incorrectamente para ambos
sexos) y 12,0-16,0 g/dL (el valor femenino que el mismo documento señala como el
clínicamente correcto). GLÓBULOS BLANCOS demuestra resolución por edad con una fila para
recién nacido (0-28 días) marcada explícitamente **no confirmada** (los rangos
neonatales/pediátricos reales son otra pregunta abierta al laboratorio) y una fila para el
resto con el valor confirmado (4.500-10.000/mm3).

**Decisión — validación por `CheckConstraint`.** Igual criterio que `Parameter` en la
Fase 05: cada `range_type` exige sus propios campos (`low`/`high` para `CLOSED`, `high`
para `UPPER_BOUND`, `low` para `LOWER_BOUND`, `center`+`tolerance` para `TOLERANCE`,
`expected_option` para `QUALITATIVE`, `bands` para `INTERPRETIVE`) validados con
`CheckConstraint` de base de datos, más `age_min_days <= age_max_days`.

**Consecuencias.**
- Ningún `ReferenceRange` marcado "PENDIENTE DE CONFIRMAR" o "NO CONFIRMADO" debe usarse
  en un informe real hasta que Angelus responda — queda explícito en `docs/ESTADO.md`.
- Si "PERFIL LIPÍDICO" termina siendo un `Profile` que agrupa `Test`s en vez de un `Test`
  único (decisión de la Fase 08), el `Test` `PERFIL_LIPIDICO` sembrado aquí puede
  renombrarse o descomponerse sin perder los `ReferenceRange` — éstos cuelgan de
  `Parameter`, no de `Test` ni `Profile`.
- `resolve_reference_range()` (en `services/reference_resolver.py`) es, desde ahora, el
  único punto permitido para resolver un rango — ninguna vista o service futuro debe
  filtrar `ReferenceRange` directamente (mismo criterio que `services/`, regla 3 de
  `docs/03_CONVENCIONES.md`: ninguna vista toca el ORM directo).
- La resolución de `bands` (`INTERPRETIVE`) a un texto según el valor medido, y el
  congelamiento de `reference_used`/`reference_text` en `ResultValue`, quedan para la
  Fase 10 (captura y validación de resultados) — aquí sólo se guarda el dato.


---

## ADR-017 — Motor de fórmulas: sintaxis `{CODIGO}`/`{@var}`, AST restringido, precisión completa, Mosteller
**Fecha:** 2026-09-26 · **Estado:** Aceptada

**Contexto.** La Fase 07 implementa los parámetros `NUMERIC_CALCULATED`. `00_ARQUITECTURA.md`
fijaba la sintaxis `{HB}` / `{@peso}`, pero las 2 fórmulas sembradas en las Fases 05/06
(`URO_INDICE_PROT_CREAT`, `COAG_PTT_DIFERENCIA`) usaban códigos sueltos y `depends_on`
estaba vacío. Faltaba decidir el origen del ISI (INR) y la precisión de los intermedios, y
el criterio de salida exige reproducir los valores reales de `04_HALLAZGOS_FORMATOS.md`.

**Decisión — sintaxis y seguridad.** `{CODIGO}` referencia otro parámetro del tenant y
`{@variable}` un dato de la orden (lista cerrada `CONTEXT_VARIABLES`: `peso`, `talla`,
`volumen_orina_24h`, `isi`). Las llaves se traducen a identificadores y la expresión se
parsea con `ast` en modo `eval`, recorriendo una **lista blanca** de nodos (`+ - * / **`,
signo, literales numéricos, `round/sqrt/min/max/abs`). Nunca `eval()`. Exponente acotado a
|10|, fórmula ≤ 500 caracteres. La migración de datos `catalog.0004_formula_sintaxis_llaves`
reescribe las fórmulas existentes y puebla `depends_on`.

**Decisión — dónde viven las cosas.** `services/formula_engine.py` es puro (sin ORM): la
Fase 10 lo llama con `{código: fórmula}`, `{código: valor}` y el contexto de la orden.
`services/formula_validation.py::set_parameter_formula()` es el único camino para asignar
una fórmula: valida existencia y tipo numérico de las referencias, autorreferencia y
**ciclos al guardar** (orden topológico con `graphlib` sobre todas las fórmulas del
tenant), y sincroniza `depends_on`. El admin usa la misma validación.

**Decisión — ISI como `{@isi}`.** Angelus no ha confirmado el ISI del lote. El motor lo
recibe como variable de contexto; dónde se persiste (TenantSettings o por lote) se decide
en la Fase 10. Sin ISI, el INR queda vacío con motivo y el resto se calcula.

**Decisión — precisión completa.** Todo en `Decimal` (precisión 28). Los calculados que
alimentan a otros (VLDL→LDL, SC→depuración corregida) pasan sin redondear, como Excel. El
redondeo (mitad hacia arriba, `Parameter.decimals`) es sólo para mostrar/guardar.

**Decisión — superficie corporal con Mosteller.** `04_HALLAZGOS_FORMATOS.md` anotaba DuBois
y afirmaba que reproducía la hoja `DEPURACIÓN`. No es así: DuBois da 1,6819 m² y 67,76
mL/min; la hoja imprime 1,6857 m² y 67,61 mL/min, que es exactamente Mosteller
(`sqrt(talla × peso / 3600)`). Se sembró Mosteller y se agregó errata al documento de
hallazgos.

**Consecuencias.**
- Pregunta nueva a Angelus: ¿Mosteller (lo que usa su hoja) o DuBois?
- Sólo 3 de las 16 fórmulas tienen valor impreso real para comparar (las de depuración);
  las otras 13 se verificaron contra cálculos a mano. Validar con una orden real de
  Angelus cuando exista (Fase 10).
- Una fórmula inválida guardada por fuera de `set_parameter_formula()` (ORM directo) hace
  fallar la validación de las demás, porque la detección de ciclos parsea todas.
- `URO_INDICE_PROT_CREAT` (NO CONFIRMADO, Fase 05) multiplica por 100 con unidad `mg/g`;
  mg/dL ÷ mg/dL → mg/g requiere ×1000. Revisar cuando Angelus confirme ese parámetro.


---

## ADR-018 — Angelus es laboratorio de referencia, no el alcance del producto
**Fecha:** 2026-09-26 · **Estado:** Aceptada

**Contexto.** Varios documentos (índice del roadmap, hallazgos, preguntas abiertas) están
redactados como si el objetivo fuera reproducir el método de trabajo del Laboratorio
Angelus. Darwin aclaró al cerrar la Fase 07 que no es así: Angelus facilitó sus hojas de
trabajo como base para arrancar, y Biolife es un SaaS pensado para muchos laboratorios.

**Decisión.**
- Las hojas de Angelus (`docs/04_HALLAZGOS_FORMATOS.md`) son **material de referencia y
  datos de prueba reales**, no una especificación cerrada ni un techo de alcance.
- El producto busca ser **lo más completo posible**, por encima de lo que hoy usa Angelus.
  Cada fase tiene libertad creativa para agregar exámenes, fórmulas, tipos de rango,
  configuraciones o funciones útiles para laboratorios clínicos en general.
- Lo que varía entre laboratorios (rangos, fórmulas alternativas, formato del informe,
  precios, flujo de validación) se modela como **configuración por tenant**.
- Los criterios de salida que nombran a Angelus se interpretan como *demostración con
  datos reales*: el sistema debe poder representarlo, sin limitarse a eso.

**Consecuencias.**
- Las preguntas abiertas "al laboratorio" alimentan los datos del tenant Angelus (o de un
  tenant demo); **no bloquean** decisiones de producto. Ejemplo: Mosteller vs DuBois
  (ADR-017) no es "cuál usa Angelus" sino qué fórmula trae el catálogo por defecto — como
  las fórmulas son por tenant, cada laboratorio puede usar la suya.
- Los valores marcados "PENDIENTE DE CONFIRMAR"/"NO CONFIRMADO" siguen sin usarse en un
  informe real: la regla de no inventar datos clínicos no cambia.
- Futuro catálogo semilla (Master*+copia, ADR-015) puede incluir exámenes que Angelus no
  hace.


---

## ADR-019 — Perfiles como agrupación de exámenes individuales; precios multimoneda en `apps.billing`
**Fecha:** 2026-09-26 · **Estado:** Aceptada

**Contexto.** La Fase 08 exige perfiles y lista de precios. Darwin definió que un perfil
(Lipídico, Perfil 20…) es una agrupación nombrada de exámenes y que los precios deben poder
ordenarse, ajustarse, tener moneda y descuentos por tenant. Las Fases 06/07 habían sembrado
exámenes agregados (`QUIM`, `PERFIL_LIPIDICO`, `COAGUL`) que no se pueden agrupar. Darwin
adjuntó los Excel del laboratorio de referencia, que se leyeron celda por celda.

**Decisión — granularidad.** Cada analito ordenable es un `Test` propio. Los parámetros de
las Fases 06/07 se mudan a su examen individual **conservando su código**, así que fórmulas,
`depends_on` y rangos no cambian. Los agregados viejos se desactivan (no se borran). La
siembra vive en una sola fuente declarativa (`seeding_base_catalog.py`).

**Decisión — perfiles.** `Profile` + `ProfileTest` (orden). `set_profile_tests()` rechaza
perfiles con parámetros calculados sin sus insumos (recorrido transitivo de `depends_on`).
Composición de 13 hojas (14 perfiles: el glicémico tiene variante post-prandial y
post-carga); agregados por Biolife: UROANÁLISIS en el Preeclámptico y un Perfil prenatal.

**Decisión — precios.** App `apps.billing` (nombre previsto en `02_ESTRUCTURA_PROYECTO.md`):
- `Currency` por tenant con una sola moneda base; `ExchangeRate` por fecha (1 origen = tasa
  destino; se usa la más reciente ≤ fecha, o la inversa).
- `PriceList` en una moneda, con vigencia, orden y una sola predeterminada.
- `PriceListItem`: examen **o** perfil; perfil en modo `FIXED` o `SUM_WITH_DISCOUNT`
  (suma de sus exámenes en la misma lista menos %).
- `Discount`: % o monto fijo (con moneda), alcance orden o ítem (con exámenes/perfiles
  destino), vigencia, acumulable o no, y `requires_authorization` (lo exige `quote()`; el rol
  que autoriza se conecta en la Fase 09).
- `Test.price` se elimina: una sola fuente de precio.
- `quote()` no guarda nada: la orden (Fase 09) congela el resultado.

**Reglas de cotización.** Un examen se cobra una vez (si viene suelto y en un perfil, sólo
cuenta el perfil; si dos perfiles lo comparten, el segundo recibe crédito por su precio
individual). Descuentos por línea y luego de orden: el mejor no acumulable + todos los
acumulables, con tope en el monto. Precisión completa, redondeo a los decimales de la
moneda por línea.

**Decisión — Mosteller confirmado.** La celda de la hoja DEPURACIÓN es
`=SQRT((K24*K25)/3600)`: la pregunta abierta de ADR-017 queda resuelta con el dato del
propio laboratorio. Las 17 fórmulas (16 de `04_HALLAZGOS` + HOMA-IR) reproducen valores
reales de las hojas.

**Consecuencias.**
- No hay precios sembrados: `seed_billing` crea USD (base), VES y la lista GENERAL vacía.
- La hoja de Angelus calcula el INR con ISI vacío → siempre 1. Biolife no reproduce eso.
- Rangos nuevos marcados "PENDIENTE DE CONFIRMAR": LDH por sexo (otras hojas usan 90–510),
  TGO/TGP <40 (otras hojas <35), insulina basal (unidad "U/mL" en la hoja). HbA1c con
  bandas ADA marcadas "PROPUESTO". Insulina post-carga sin rango.
- Los rangos de lípidos de la Fase 06 usan condición `AYUNO`; los nuevos usan `NINGUNA`.
  El resolver con condición por defecto no encuentra los de `AYUNO`: decidir en la Fase 10.
- Perfiles anidados y tasa BCV automática quedan fuera.


---

## ADR-020 — Ficha del examen: rangos por edad en años/meses/días, validación de cobertura, admin por tenant
**Fecha:** 2026-09-26 · **Estado:** Aceptada

**Contexto.** Darwin pidió que cada examen tenga una ficha donde el laboratorio ajuste los
rangos por sexo y edad. El modelo (`ReferenceRange`, ADR-004/016) ya lo soportaba, pero la
edad se editaba en días crudos y nada avisaba de solapes o huecos. Todavía no hay estilo
visual definido para las pantallas.

**Decisión.**
- La lógica vive en services independientes de la pantalla
  (`reference_range_management.py`); el admin de Django es la pantalla **provisional**.
- Edad en años/meses/días con año = 365,25 días y mes = 1/12 de año, redondeando al día
  (`core/utils/dates.py`). En el formulario, "Desde" es inclusiva y "Hasta" **exclusiva**
  ("0 a 1 año" = 0–364 días), para que tramos consecutivos encajen sin huecos ni solapes.
- Solape con misma prioridad y mismo ancho = ERROR (bloquea). Solape resuelto por el
  desempate o hueco de edad/sexo = AVISO (se guarda e informa).
- Un rango desactivado no se resuelve nunca (ajuste a `resolve_reference_range()`).
- `django.contrib.admin` también en `TENANT_APPS`, con la migración
  `accounts.0004_admin_log_por_tenant` para crear `django_admin_log` en los tenants
  existentes (sus migraciones de `admin` figuraban aplicadas sin tabla).

**Consecuencias.**
- La ficha definitiva (fase de estilo visual) reutiliza estos services sin cambios.
- Cualquier `app` compartida cuyo modelo apunte a `accounts.User` debe revisarse con el
  mismo criterio: si guarda datos por laboratorio, debe estar en `TENANT_APPS`.
- El probador hace visible el pendiente de ADR-019: los rangos de lípidos con condición
  `AYUNO` no aplican a un paciente con condición `NINGUNA`.


---

## ADR-021 — Consolidación: laboratorios nacen con catálogo, lípidos sin condición AYUNO, CI
**Fecha:** 2026-09-26 · **Estado:** Aceptada

**Contexto.** Revisión de estado antes de la Fase 09: un laboratorio nuevo nacía vacío (4
comandos manuales), los rangos de lípidos con condición AYUNO no aplicaban a ningún paciente,
los tests sólo corrían a mano y el script de aislamiento estaba roto desde la Fase 02.

**Decisión.**
- `provision_tenant(..., seed_catalog=True)` siembra catálogo base, perfiles, monedas y la
  lista GENERAL vacía. Todo es editable por el laboratorio; `--sin-catalogo` lo omite.
- El ayuno es un requisito del examen (`Test.requires_fasting`), no un rango distinto: los
  rangos de lípidos pasan a condición NINGUNA (migración `catalog.0006`). La condición AYUNO
  queda para parámetros cuyo valor de referencia realmente cambia con el ayuno.
- GitHub Actions corre ruff, migraciones, pytest y el script de aislamiento en cada push.

**Consecuencias.** Crear un laboratorio tarda unos segundos más. Los tests de provisión
también. Si el laboratorio no usa GitHub, el workflow simplemente no corre.

---

## ADR-022 — Sistema visual: CSS plano sin build, denso, con la paleta del logo
**Fecha:** 2026-09-26 · **Estado:** Aceptada (reemplaza "Tailwind vía CLI" de 03_CONVENCIONES)

**Contexto.** Antes de la primera pantalla real (Fase 09) hacía falta un estilo. Darwin pidió
algo moderno y minimalista, sin tener que desplazarse para ver todos los campos, con el logo
de Biolife. Las convenciones preveían Tailwind compilado por CLI.

**Decisión.**
- Un solo `static/css/biolife.css` con tokens en variables CSS y componentes de clases
  cortas. Sin Tailwind ni Node: nada que compilar en Windows ni en CI, un archivo cacheable,
  y la PWA (Fase 13) lo sirve offline.
- Paleta tomada del logo (navy `#0b2e63`, azul `#0d6dc9`, teal `#11ad9b`); `--brand` es el
  color primario de cada laboratorio (`TenantSettings.color_primary`).
- Densidad por diseño: controles de 32 px, texto de 13,5 px, grilla de formulario de 12
  columnas, tablas compactas, barra de acciones fija al pie.
- Inter autoalojada, íconos Lucide en sprite SVG, htmx y Alpine en `static/vendor/`: sin
  dependencias de CDN.
- Guía de estilo viva en `/estilo/` como referencia para las fases siguientes.
- `STORAGES` en lugar de `STATICFILES_STORAGE` (eliminado en Django 5.1: WhiteNoise estaba
  inactivo sin aviso). `TENANT_COLOR_ADMIN_APPS = False` y el admin con la identidad de Biolife.

**Consecuencias.**
- Las pantallas de las Fases 09+ usan `base_tenant.html`, `{% field %}` y los componentes de
  la guía; un componente nuevo se agrega primero a la guía.
- `color-mix()` exige navegadores de 2023 en adelante; en los más viejos sólo se pierden los
  fondos suaves del color del laboratorio.
- Sin modo oscuro por ahora.
