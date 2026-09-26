# 01 — Modelo de Datos (ER)

Notación: `PK` clave primaria, `FK` foránea, `U` único, `N` nullable, `[idx]` indexado.
Todos los modelos de tenant heredan `TenantBaseModel`: `id (UUID, PK)`, `created_at`,
`updated_at`, `created_by (FK User, N)`, `is_active (bool)`.

---

## A. ESQUEMA PUBLIC — Plataforma SaaS

### `Tenant` (tabla `tenants_client`)
```
id                  PK
schema_name         U, slug validado [a-z0-9_]
name                razón social del laboratorio
rif                 U, N          # J-508257340
legal_name          N
status              ENUM: DEMO | ACTIVO | SUSPENDIDO | MOROSO | CANCELADO
onboarded_at
trial_ends_at       N
paid_until          N             # usado por django-tenants para bloqueo automático
notes               N
```

### `Domain` (django-tenants)
```
id PK · domain U · tenant FK→Tenant · is_primary bool
```

### `Plan`
```
id PK · code U · name · price_monthly · currency
max_users           int        # 0 = ilimitado
max_orders_month    int
max_storage_mb      int
features            JSONB      # {"instrumentos": true, "pwa_offline": true, "api": false}
is_public           bool       # visible en la página de precios
```

### `Subscription`
```
id PK · tenant FK→Tenant · plan FK→Plan
status         ENUM: TRIAL | ACTIVA | VENCIDA | CANCELADA
started_at · current_period_start · current_period_end
cancel_at_period_end bool
```
> Histórico de planes = múltiples filas. **No** sobreescribir el plan en `Tenant`.

### `SaaSInvoice`
```
id PK · subscription FK · period_start · period_end
amount · currency · status ENUM: PENDIENTE|PAGADA|VENCIDA|ANULADA
issued_at · paid_at N · payment_reference N
```

### `TenantUsageSnapshot`
```
id PK · tenant FK · date [idx]
active_users · orders_count · patients_count · storage_mb · api_calls
```
> Snapshot diario por tarea programada. Alimenta el panel global y la facturación por
> consumo sin tener que contar sobre las tablas del tenant en tiempo real.

### Catálogos maestros (semilla, se **copian** al tenant)
```
MasterSection        # HEMATOLOGÍA, QUÍMICA SANGUÍNEA, ORINA, HECES, SEROLOGÍA, COAGULACIÓN...
MasterUnit           # g/dL, mg/dL, %, /mm3, U/L, mm/h, mL/min, seg, ng/mL, m2
MasterMethod         # Aglutinación látex semicuantitativo, Inmunocromatografía cualitativa,
                     # Floculación, Colorimétrico Jaffé modificado
MasterAnalyte        # catálogo base con loinc_code N
Locality             # municipios/ciudades — ALTAGRACIA DE ORITUCO, CALABOZO, ...
```

### `PlatformUser`
Super-administradores de Biolife. Tabla separada del `User` de tenant. Sin acceso a datos
clínicos: sólo métricas, suscripciones y estado. **Regla explícita:** el personal de Biolife
no puede leer resultados de pacientes desde el panel global.

---

## B. ESQUEMA TENANT — Configuración

### `TenantSettings` (singleton por tenant)
```
id PK
# Identidad visual
logo                  Cloudinary, N
banner                Cloudinary, N
color_primary         #RRGGBB, default #1B5FA8
color_secondary
report_header_html    N      # cabecera del informe
report_footer_text    N      # "Los resultados requieren firma y sello húmedo..."
report_disclaimer     N      # "El laboratorio es garante de la fase preanalítica..."
# Contacto (impreso en el informe)
phone · address · email · instagram · website   (todos N)
# Localización
timezone              default 'America/Caracas'
time_format           ENUM: H12 | H24, default H12
date_format           default 'dd/MM/yyyy'
decimal_separator     ENUM: COMA | PUNTO, default COMA
# Operación
order_number_prefix   N
order_number_next     int
require_second_validation  bool, default False
```

### `Role` / `Membership`
```
Role:        id PK · code · name · permissions JSONB · is_system bool
Membership:  id PK · user FK→User · role FK→Role · is_active
```

### `AuditLog` (append-only, sin update ni delete)
```
id PK · user FK N · action · model_name · object_id
changes JSONB N · ip · user_agent · created_at [idx]
```

---

## C. ESQUEMA TENANT — Pacientes

### `Patient`
```
id              PK
internal_code   U, [idx]     # SIEMPRE generado. Es la identidad real del no cedulado.
document_type   ENUM: V | E | J | P | SIN_DOCUMENTO
document_number N, [idx]
first_name · last_name
sex             ENUM: M | F
birth_date      N, [idx]
# Edad declarada — cuando no se conoce la fecha de nacimiento
declared_age_value  int N
declared_age_unit   ENUM: DIAS | MESES | AÑOS, N
declared_age_at     date N       # fecha en que se declaró; permite recalcular después
locality        FK→Locality, N
address · phone · email          (N)
is_minor        propiedad calculada, no columna
```

**Constraints**
```sql
-- documento único por tipo cuando existe
UNIQUE (document_type, document_number) WHERE document_number IS NOT NULL
-- se conoce la edad por una vía o por la otra
CHECK (birth_date IS NOT NULL OR declared_age_value IS NOT NULL)
```

> **Caso borde resuelto:** paciente "RN SUTIL" (recién nacido sin nombre propio aún ni
> cédula) aparece literalmente en los formatos. `internal_code` + representante lo cubre.

### `Guardian` (Representante / Tutor legal)
```
id PK
document_type ENUM: V|E|J|P   # obligatorio, el representante SÍ debe estar identificado
document_number   [idx]
first_name · last_name · phone · address N · email N
UNIQUE (document_type, document_number)
```

### `PatientGuardian`
```
id PK · patient FK→Patient · guardian FK→Guardian
relationship  ENUM: MADRE | PADRE | ABUELO | TIO | HERMANO | TUTOR_LEGAL | OTRO
relationship_detail N        # obligatorio si relationship = OTRO
is_primary    bool
legal_doc_ref N              # nº de sentencia o documento de tutela
UNIQUE (patient, guardian)
```

**Regla de negocio (en `services/patient_creation.py`, no en el modelo):**
si el paciente es menor de 18 años **y** `document_number` es nulo, debe existir al menos
un `PatientGuardian` con `is_primary=True`. Se valida en el service porque requiere
consultar la relación, que no existe aún al momento del `clean()` del paciente.

---

## D. ESQUEMA TENANT — Catálogo de exámenes

```
Section        id PK · code U · name · order_index · print_page_break bool
Unit           id PK · symbol U · description N
Method         id PK · name · description N     # "Aglutinación látex semicuantitativo"
```

### `Test` (examen individual — la unidad que se ordena y se cobra)
```
id PK
code            U, [idx]      # HEM_COMP, QUIM_GLI, URO, COPRO, PCR
name                          # "HEMATOLOGÍA COMPLETA"
section         FK→Section
method          FK→Method, N  # se imprime bajo el resultado
sample_type     ENUM: SANGRE_TOTAL | SUERO | PLASMA | ORINA | ORINA_24H | HECES | OTRO
container       N             # "Tubo lila EDTA", "Tubo azul citrato"
process_hours   int N         # tiempo de respuesta estimado
price           decimal N
requires_fasting        bool
requires_anthropometry  bool  # peso/talla — depuración de creatinina
is_active       bool
```

### `ParameterGroup` (subtítulos dentro de un examen)
```
id PK · test FK→Test · name · order_index
```
> Cubre "SERIE ROJA" / "SERIE BLANCA" en hematología, "EXAMEN FÍSICO" / "EXAMEN QUÍMICO" /
> "EXAMEN MICROSCÓPICO" en uroanálisis, "ÍNDICE DE CASTELLI - I" en el perfil lipídico.
> Es puramente de presentación, pero sin él el informe no reproduce los formatos del cliente.

### `Parameter`
```
id PK
test            FK→Test
group           FK→ParameterGroup, N
code            [idx]         # HB, HTO, CHCM, COL_TOT — único por tenant
name                          # "HEMOGLOBINA"
value_type      ENUM: NUMERIC | NUMERIC_CALCULATED | CODED | SEMIQUANTITATIVE |
                      QUALITATIVE | TITER | COUNT_RANGE | NARRATIVE | MULTI_CATALOG
unit            FK→Unit, N
decimals        int, default 2
order_index
option_set      FK→CodedOptionSet, N   # obligatorio si value_type es codificado
formula         text N                 # obligatorio si NUMERIC_CALCULATED
depends_on      M2M→Parameter (self)   # derivado de formula, no editable a mano
is_printable    bool, default True     # algunos parámetros son sólo insumo de cálculo
is_optional     bool                   # AMILASA/LIPASA aparecen en blanco en los formatos
instrument_code N, [idx]               # mapeo con el analizador — desde ya
UNIQUE (tenant implícito, code)
```

### `CodedOptionSet` / `CodedOption`
```
CodedOptionSet: id PK · code U · name
                # COLOR_ORINA, ASPECTO, ABUNDANCIA, NEG_POS, REACTIVIDAD,
                # TITULO_PCR, TITULO_VDRL, PARASITOS

CodedOption:    id PK · option_set FK · value ("POSITIVO (++)")
                ordinal int N          # orden clínico: NEGATIVO=0, TRAZAS=1, +=2...
                numeric_equivalent N   # PCR 1/8 → 48.0 mg/L
                is_pathological bool   # marca el resultado en el informe
                order_index
```

Sets a sembrar (extraídos de los formatos reales):
| Set | Valores |
|---|---|
| `ABUNDANCIA` | AUSENTES · ESCASAS · MODERADAS · ABUNDANTES |
| `NEG_POS_CRUCES` | NEGATIVO · TRAZAS · POSITIVO (+) · (++) · (+++) · (++++) |
| `NEG_POS` | NEGATIVO · POSITIVO |
| `REACTIVIDAD` | NO REACTIVO · REACTIVO |
| `UROBILINOGENO` | NORMAL · AUMENTADO |
| `COLOR_ORINA` | AMARILLO · ROJO · ÁMBAR · TRANSPARENTE · CLARO |
| `ASPECTO_ORINA` | CLARO · LIGERAMENTE TURBIO · TURBIO |
| `OLOR_ORINA` | SUI-GENERIS · AMONIACAL |
| `COLOR_HECES` | MARRÓN · AMARILLO · VERDE · ROJO · NEGRO |
| `CONSISTENCIA_HECES` | BLANDA · DURA · LÍQUIDA |
| `TITULO_PCR` | NEGATIVO: Menor a 6,0 mg/L · 1/1=6,0 · 1/2=12 … 1/256=1536 mg/L |
| `TITULO_VDRL` | NO REACTIVO · REACTIVO: 2 Dils … 256 Dils |
| `PARASITOS` | ~18 frases, multi-selección (ver `04_HALLAZGOS_FORMATOS.md`) |

### `ReferenceRange`
```
id PK
parameter       FK→Parameter
sex             ENUM: M | F | ANY, default ANY
age_min_days    int, default 0
age_max_days    int, default 54750   # ~150 años
condition       ENUM: NINGUNA | EMBARAZO | AYUNO | POST_PRANDIAL, default NINGUNA
range_type      ENUM: CLOSED | UPPER_BOUND | LOWER_BOUND | TOLERANCE |
                      QUALITATIVE | INTERPRETIVE
low · high · center · tolerance     decimal N
expected_option FK→CodedOption, N
bands           JSONB N             # sólo INTERPRETIVE (procalcitonina)
display_text                        # OBLIGATORIO. Se imprime literal.
unit            FK→Unit, N
priority        int                 # desempate cuando varios rangos coinciden
```
Resolución en `services/reference_resolver.py`: filtra por sexo y edad-en-días, ordena por
`priority` desc y por rango etario más estrecho primero, devuelve el primero. Si no hay
coincidencia devuelve `None` y el informe imprime la celda de referencia vacía — que es
exactamente lo que hacen los formatos actuales con MONOCITOS y BASÓFILOS.

### `Profile` (perfil / paquete)
```
id PK · code U · name · description · order_index · is_active
```
> Fase 08 (ADR-019): **sin precio** aquí ni en `Test`. Los precios viven en `apps.billing`:
> `Currency`, `ExchangeRate`, `PriceList`, `PriceListItem` (examen o perfil; perfil fijo o
> suma−%), `Discount`.
### `ProfileTest`
```
id PK · profile FK · test FK · order_index · UNIQUE(profile, test)
```
Perfiles reales a sembrar: PERFIL 20, BÁSICO, LIPÍDICO, HEPÁTICO, RENAL, PRE-OPERATORIO,
PRECLÁMPTICO, PEDIÁTRICO, GLICÉMICO, ORINA+HECES, HC+COAG, HIV+VDRL, HC+ORINA.

### `ObservationTemplate`
```
id PK · section FK→Section, N · text · order_index · is_active
```
> Del formato: "SUERO ICTÉRICO", "SE SUGIERE REALIZAR EXAMEN DE HECES SERIADO",
> "HEMATOLOGÍA COMPLETA VERIFICADA CON UNA SEGUNDA MUESTRA". El bioanalista las elige
> de lista o escribe libre.

---

## E. ESQUEMA TENANT — Órdenes y muestras

### `Order`
```
id PK
number          U, [idx]      # correlativo del tenant, con prefijo
patient         FK→Patient
requested_by    N             # médico solicitante (texto libre; no se modela aún)
priority        ENUM: NORMAL | URGENTE
status          ENUM: BORRADOR | REGISTRADA | MUESTRA_TOMADA | EN_PROCESO |
                      RESULTADOS_CARGADOS | VALIDADA | ENTREGADA | ANULADA
ordered_at · delivered_at N
# Datos clínicos del episodio (no del paciente)
weight_kg N · height_cm N          # depuración de creatinina
urine_volume_24h_ml N
collection_start_time N            # "6:00 A.M." → TimeField, se renderiza en 12 h
notes N
total_amount N · is_paid bool
client_mutation_id  UUID N, U      # idempotencia offline
sync_version        int, default 1
```
> Peso, talla y volumen de orina viven en la **orden**, no en el paciente: cambian entre
> visitas y la depuración de creatinina debe calcularse con los del día de la muestra.

### `OrderItem`
```
id PK · order FK · test FK→Test · profile FK→Profile N
unit_price N · status ENUM: PENDIENTE|EN_PROCESO|CARGADO|VALIDADO|ANULADO
UNIQUE (order, test)
```
> `profile` se guarda sólo para saber de qué paquete vino. Un examen ordenado dos veces
> vía dos perfiles se cobra una vez.

### `Sample`
```
id PK · order FK · sample_type · barcode U [idx]
collected_at N · collected_by FK→User N
received_at N · status ENUM: PENDIENTE|TOMADA|RECIBIDA|RECHAZADA
rejection_reason N     # hemólisis, muestra insuficiente, mal rotulada
```

---

## F. ESQUEMA TENANT — Resultados

### `Result` (un examen dentro de una orden)
```
id PK · order_item FK→OrderItem, U
status ENUM: PENDIENTE | CARGADO | VALIDADO | RECTIFICADO
entered_by FK→User N · entered_at N
validated_by FK→User N · validated_at N
observations text N
method_override N               # si se usó un método distinto al del catálogo
sync_version int
```

### `ResultValue`
```
id PK
result          FK→Result
parameter       FK→Parameter
value_numeric   decimal N
value_text      text N
value_low · value_high   decimal N       # COUNT_RANGE: 0 - 1 P/C
coded_option    FK→CodedOption, N
multi_options   M2M→CodedOption          # MULTI_CATALOG (parásitos)
flag            ENUM: NORMAL | BAJO | ALTO | CRITICO_BAJO | CRITICO_ALTO | ANORMAL, N
reference_used  FK→ReferenceRange, N     # congelado al momento de validar
reference_text  N                        # copia literal del display_text
is_calculated   bool
source          ENUM: MANUAL | INSTRUMENTO | CALCULADO | OFFLINE_SYNC
UNIQUE (result, parameter)
```

**Constraint clave**
```sql
CHECK (
  (value_numeric IS NOT NULL)::int + (value_text IS NOT NULL)::int +
  (coded_option_id IS NOT NULL)::int + (value_low IS NOT NULL)::int >= 1
)
```

> **`reference_used` + `reference_text` se copian al validar, no se resuelven al imprimir.**
> Si el laboratorio cambia un rango en 2027, el informe de 2026 debe seguir mostrando el
> rango que estaba vigente. Sin esto, cualquier reimpresión de un histórico es incorrecta —
> y en un contexto clínico eso es un problema serio, no cosmético.

### `ResultAmendment` (rectificación)
```
id PK · original_result FK→Result · new_result FK→Result
reason text · amended_by FK→User · amended_at
version int
```
> Un resultado validado **jamás** se edita. Se crea un `Result` nuevo, el original pasa a
> `RECTIFICADO`, y el informe se reemite con versión incrementada.

### `ResultSignature`
```
id PK · result FK→Result (o report FK)
signed_by FK→User · signed_at
payload_hash  char(64)        # SHA-256 del contenido firmado
previous_hash char(64) N      # cadena
signature_image N · stamp_image N     # Cloudinary
professional_license          # nº de colegiatura del bioanalista
```

### `Report`
```
id PK · order FK · version int
pdf_url (Cloudinary, authenticated) · generated_at · generated_by FK→User
access_token U [idx]          # verificación por QR
content_hash char(64)
UNIQUE (order, version)
```

---

## G. ESQUEMA TENANT — Integraciones y sincronización

```
Instrument         id PK · name · model · manufacturer · protocol ENUM: ASTM|HL7|CSV|MANUAL
                   connection_type ENUM: SERIAL|TCP|ARCHIVO · is_active · gateway_token U

InstrumentMessage  id PK · instrument FK · raw_payload bytea · received_at [idx]
                   status ENUM: RECIBIDO|PARSEADO|ERROR|DESCARTADO · error_detail N
                   # SIEMPRE se guarda antes de parsear

InstrumentResult   id PK · message FK · instrument_code · raw_value
                   sample_barcode N [idx] · matched_parameter FK→Parameter N
                   matched_result FK→Result N · status ENUM: PENDIENTE|APLICADO|HUERFANO

SyncQueueEntry     id PK · device_id · client_mutation_id UUID U
                   entity · payload JSONB · status ENUM: PENDIENTE|APLICADO|CONFLICTO|ERROR
                   received_at · applied_at N · error_detail N

SyncConflict       id PK · queue_entry FK · entity · object_id · field
                   client_value · server_value · resolution ENUM: CLIENTE|SERVIDOR|MANUAL
                   resolved_by FK→User N · resolved_at N
```

---

## H. Diagrama de relaciones (resumen)

```
PUBLIC
  Tenant ──1:N── Domain
  Tenant ──1:N── Subscription ──N:1── Plan
  Subscription ──1:N── SaaSInvoice
  Tenant ──1:N── TenantUsageSnapshot

TENANT
  Patient ──N:M(PatientGuardian)── Guardian
  Patient ──1:N── Order ──1:N── OrderItem ──1:1── Result ──1:N── ResultValue
                    │                                  │
                    ├──1:N── Sample                    ├──1:N── ResultSignature
                    └──1:N── Report                    └──1:1── ResultAmendment

  Section ──1:N── Test ──1:N── ParameterGroup ──1:N── Parameter
                    │                                     │
                    │                                     ├──1:N── ReferenceRange
                    │                                     ├──N:1── CodedOptionSet ──1:N── CodedOption
                    │                                     └──N:M── Parameter (depends_on)
                    └──N:M(ProfileTest)── Profile

  Instrument ──1:N── InstrumentMessage ──1:N── InstrumentResult ──N:1── Parameter
```
