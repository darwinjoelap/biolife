# 00 — Arquitectura del Sistema Biolife

## 1. Estrategia de Multi-Tenancy

### Decisión: `django-tenants` con esquemas de PostgreSQL

**Opciones evaluadas**

| Estrategia | Aislamiento | Costo operativo | Riesgo de fuga de datos | Veredicto |
|---|---|---|---|---|
| Base de datos por tenant | Máximo | Muy alto (N conexiones, N backups) | Nulo | Descartada — inviable en Railway |
| **Esquema por tenant (`django-tenants`)** | Alto | Medio | Muy bajo | **Elegida** |
| Discriminador `tenant_id` + `django-scopes` | Medio | Bajo | Medio-alto (un `filter()` olvidado expone datos de otro laboratorio) | Descartada |

**Por qué esquemas:** son datos clínicos. Un error de un desarrollador junior con un
`Model.objects.all()` sin filtrar en la estrategia de discriminador expone historias
clínicas de otro laboratorio. Con esquemas, ese error es físicamente imposible: el
`search_path` de la conexión ya está acotado al tenant. También simplifica
restaurar/exportar un laboratorio individual y borrarlo cuando cancela la suscripción.

**Costo que aceptamos:** las migraciones corren N veces (una por esquema). Con 200
tenants una migración puede tardar minutos. Mitigación: `migrate_schemas --executor=multiprocessing`
y ventana de mantenimiento programada.

### Enrutamiento

Por subdominio: `angelus.biolife.app`, `sanjose.biolife.app`.
El esquema `public` aloja `Client` (tenant) y `Domain`. Middleware de `django-tenants`
resuelve el esquema desde el `Host` header.

Dominio propio del laboratorio (`lab.midominio.com`) se soporta agregando un `Domain`
adicional al mismo tenant. Es un diferenciador comercial barato — vale la pena desde el día 1.

### ⚠️ Advertencia crítica sobre Railway y pooling

`django-tenants` cambia de esquema con `SET search_path`, que es **estado de sesión**.
Un pooler en modo *transaction* (PgBouncer, el pooler de Supabase, y algunos add-ons de
Railway) reasigna conexiones entre transacciones y romperá el aislamiento de forma
silenciosa e intermitente — el peor tipo de bug posible en este dominio.

**Regla:** conectarse siempre a PostgreSQL en modo *session pooling* o directo.
Documentar la cadena de conexión exacta en `docs/DECISIONES.md` y verificarlo en el
health check de arranque (ver Fase 01, tarea 7).

### Reparto de modelos

**Esquema `public` (SHARED_APPS)**
`Client/Tenant`, `Domain`, `Plan`, `Subscription`, `Invoice` (SaaS), `PlatformUser`
(super-admin), `AuditLogGlobal`, y **catálogos maestros de referencia**: unidades de
medida, métodos analíticos, secciones de laboratorio, localidades/municipios, y un
catálogo semilla de analitos. Los tenants **copian** de este catálogo al crearse; no lo
comparten por FK. Así cada laboratorio puede renombrar "GLICEMIA" a "GLUCOSA EN AYUNAS"
sin afectar a nadie.

**Esquema por tenant (TENANT_APPS)**
`accounts`, `patients`, `catalog`, `orders`, `results`, `reporting`, `integrations`, `sync`.

---

## 2. Capas de la aplicación (Services & Selectors)

```
HTTP / API
   │
   ▼
views.py / api/views.py      ← orquestación, ~25 líneas máx, sin ORM
   │
   ├──► forms.py / serializers.py    ← validación de forma
   │
   ├──► services/                    ← escritura, transacciones, reglas de negocio
   │        └── usa selectors + models
   │
   └──► selectors/                   ← lectura, queries complejas, agregaciones
            └── usa models

models.py                    ← estructura, constraints, clean(), sin reglas de negocio
```

**Contrato de un service**

```python
# apps/orders/services/order_creation.py
def create_order(*, patient: Patient, profile_ids: list[UUID],
                 requested_by: User, priority: str = "NORMAL") -> Order:
    """Crea la orden, expande perfiles a exámenes, genera muestras requeridas."""
```

- Argumentos siempre *keyword-only* (`*`). Hace el call-site legible y evita bugs de orden.
- Un service es una función, no una clase, salvo que tenga estado real.
- Un service que escribe se envuelve en `transaction.atomic()`.
- Devuelve objetos de dominio, nunca `HttpResponse`.

**Contrato de un selector**

```python
# apps/orders/selectors/order_queries.py
def pending_validation_orders(*, section: Section | None = None) -> QuerySet[Order]:
```

- Sólo lectura. Nunca escribe.
- Devuelve `QuerySet` cuando es posible (permite componer y paginar).

---

## 3. Motor de parámetros dinámicos

El corazón del sistema. Un examen no es un campo: es una colección de parámetros con
tipos heterogéneos. Del análisis de los formatos reales (ver `docs/04_HALLAZGOS_FORMATOS.md`)
se identificaron **9 tipos de valor**:

| Tipo | Ejemplo real | Almacenamiento |
|---|---|---|
| `NUMERIC` | Hemoglobina 12.9 g/dL | `value_numeric` |
| `NUMERIC_CALCULATED` | CHCM, VLDL, Índice de Castelli, INR | `value_numeric` + `formula` |
| `CODED` | COLOR: AMARILLO / ROJO / ÁMBAR | FK a `CodedOption` |
| `SEMIQUANTITATIVE` | ESCASAS / MODERADAS / ABUNDANTES | FK a `CodedOption` con `ordinal` |
| `QUALITATIVE` | NEGATIVO / POSITIVO, REACTIVO / NO REACTIVO | FK a `CodedOption` |
| `TITER` | PCR: POSITIVO 1/8 = 48 mg/L | `CodedOption` con `ordinal` + `numeric_equivalent` |
| `COUNT_RANGE` | LEUCOCITOS: 0 - 1 P/C | `value_low` + `value_high` |
| `NARRATIVE` | Examen microscópico de heces | `value_text` |
| `MULTI_CATALOG` | Hallazgos parasitarios (frases de catálogo, multi-selección) | M2M a `CodedOption` |

**Decisión de almacenamiento:** una tabla `ResultValue` con columnas nullable por tipo
(`value_numeric`, `value_text`, `value_low`, `value_high`, `coded_option_id`) más un
`CheckConstraint` que obliga a que la columna poblada corresponda al `value_type` del
parámetro. Se descartó JSONB como almacén primario: los resultados se consultan,
grafican y comparan históricamente, y eso en JSONB se vuelve lento e imposible de indexar bien.

### Motor de fórmulas

Requisito real de los formatos: CHCM, Globulinas, Relación A/G, VLDL, LDL, Índices de
Castelli I y II, Razón de PT, INR, Diferencia de PTT, Depuración de creatinina corregida
por superficie corporal (fórmula de DuBois), volumen/minuto, creatinina urinaria en 24 h.

**Diseño:**
- `Parameter.formula`: expresión en texto, variables = `code` de otros parámetros del
  mismo tenant (`{HB}`, `{HTO}`, `{COL_TOT}`).
- `Parameter.depends_on`: M2M autoreferencial, poblada automáticamente al parsear la fórmula.
- Evaluación con AST restringido (whitelist de operadores y funciones: `+ - * / ** round sqrt min max abs`).
  **Nunca `eval()` crudo.** Es entrada de usuario del tenant.
- Resolución en orden topológico. Detección de ciclos al guardar, no en tiempo de cálculo.
- Fórmulas que dependen de datos del paciente o de la orden (peso, talla, volumen de
  orina 24 h, hora de recolección) leen de un espacio de nombres separado: `{@peso}`, `{@talla}`.
- Si falta un insumo, el parámetro calculado queda vacío con motivo registrado; no se
  bloquea el resto del informe.

---

## 4. Rangos de referencia

Los formatos muestran seis formas distintas de expresar un rango. El modelo las cubre con
un `range_type`:

| `range_type` | Ejemplo | Campos usados |
|---|---|---|
| `CLOSED` | 13,0 - 15,0 g/dL | `low`, `high` |
| `UPPER_BOUND` | MENOR A 200 mg/dL | `high` |
| `LOWER_BOUND` | MAYOR 40 mg/dL | `low` |
| `TOLERANCE` | ± 6,0 segundos | `center`, `tolerance` |
| `QUALITATIVE` | NEGATIVO / NO REACTIVO / SUI-GENERIS | `expected_option` |
| `INTERPRETIVE` | Procalcitonina: 4 bandas con texto interpretativo | `bands` (JSONB, sólo aquí) |

Segmentación por `sex` (M/F/ANY) y por edad en **días** (`age_min_days`, `age_max_days`).
Normalizar a días resuelve de un golpe recién nacidos, lactantes en meses y adultos en años,
que es exactamente lo que muestran los formatos (edad en AÑOS / MESES / DÍAS).

**`display_text` es obligatorio y se imprime literal.** El laboratorio escribe
"4.500 - 10.000/mm3" con punto de miles y sin espacio; derivar ese texto desde `low`/`high`
produciría "4500 - 10000 /mm3" y el laboratorio lo rechazaría. Los campos numéricos sirven
para marcar el valor como alto/bajo y para graficar; el texto sirve para imprimir.

---

## 5. PWA y modo offline

**Alcance realista — decidir esto ahora evita un desastre después:**

| Operación | Offline |
|---|---|
| Consultar órdenes del día ya descargadas | ✅ Sí |
| Consultar ficha de paciente descargada | ✅ Sí |
| Capturar / editar resultados | ✅ Sí, en cola |
| Registrar paciente nuevo | ✅ Sí, con ID temporal |
| Crear orden | ⚠️ Sí, con número provisional (renumera al sincronizar) |
| **Validación médica de resultados** | ❌ **No.** Requiere estado de servidor. |
| **Emisión de PDF firmado** | ❌ **No.** |
| Cobros / facturación | ❌ No |

**Mecánica**
- Service Worker con estrategia *network-first* para datos, *cache-first* para el shell.
- IndexedDB vía Dexie. Un store por entidad + un store `mutation_queue`.
- Cada mutación offline lleva `client_mutation_id` (UUID v4). El endpoint de sync es
  **idempotente** por ese ID. Reintentar nunca duplica.
- Cada registro lleva `sync_version` (entero). El servidor rechaza escrituras con versión
  vieja y devuelve el estado actual para que el cliente resuelva.
- Conflictos: resolución por campo, last-write-wins, con registro en `SyncConflict` para
  revisión humana. En resultados clínicos **nunca** se descarta silenciosamente: se marca
  el resultado como "requiere revisión".
- TTL de la caché offline: 24 h. Pasado ese lapso la app exige reconexión antes de
  permitir nuevas capturas. Evita trabajar sobre catálogos desactualizados.

---

## 6. Integración con analizadores clínicos

No se implementa en las primeras fases, **pero el modelo se diseña desde ahora** para no
tener que migrar datos después.

**Arquitectura: agente local (Lab Gateway)**

```
Analizador  ──RS232 / TCP──►  Lab Gateway (servicio Python en la LAN del laboratorio)
                                    │
                                    │ HTTPS + token de dispositivo
                                    ▼
                              Biolife API  ──►  InstrumentMessage (crudo, siempre se guarda)
                                                       │
                                                       ▼
                                                  Driver.parse()
                                                       │
                                                       ▼
                                                InstrumentResult (staging)
                                                       │
                                        mapeo instrument_code → Parameter
                                                       │
                                                       ▼
                                          ResultValue (pendiente de validación)
```

**Por qué un agente local y no conexión directa:** los analizadores hablan serial o TCP
crudo en la red interna del laboratorio; exponerlos a internet es inviable y peligroso.
El gateway también amortigua las caídas de conexión, que es justamente el escenario que
motiva la PWA.

**Protocolos objetivo:** ASTM E1381/E1394 (mayoría de analizadores en Venezuela: Mindray,
Wiener, BioSystems) y HL7 v2.5.1 `ORU^R01`. Interfaz común:

```python
class InstrumentDriver(Protocol):
    protocol: str
    def parse(self, raw: bytes) -> list[ParsedResult]: ...
    def build_ack(self, msg: ParsedResult) -> bytes: ...
```

**Regla de oro:** el mensaje crudo se persiste **siempre**, antes de parsear. Si el driver
falla, el dato no se pierde y se puede reprocesar. Esto ha salvado más integraciones LIS
que cualquier otra práctica.

---

## 7. Seguridad y cumplimiento

- Auditoría de acceso a datos clínicos: quién vio qué historia y cuándo (tabla append-only).
- Firma digital = usuario + timestamp + SHA-256 del payload del informe + imagen de firma
  y sello almacenada en Cloudinary con acceso restringido. Cadena de hash entre versiones
  del informe.
- Verificación pública del informe por QR → URL con token opaco de sólo lectura que muestra
  hash y fecha de emisión, **sin exponer resultados** salvo que el laboratorio lo habilite.
- Media en Cloudinary bajo `biolife/{schema}/...` con `type=authenticated` y URLs firmadas
  con expiración para cualquier cosa asociada a un paciente.
- Roles mínimos: `SUPERADMIN_PLATAFORMA`, `ADMIN_LAB`, `BIOANALISTA`, `TECNICO`,
  `RECEPCION`, `FACTURACION`, `SOLO_LECTURA`. Sólo `BIOANALISTA` y `ADMIN_LAB` validan.
- `django-axes` para bloqueo por intentos fallidos. 2FA opcional por tenant (`django-otp`).
