# 02 — Estructura del Proyecto (VS Code)

```
biolife/
├── .vscode/
│   ├── settings.json              # intérprete del venv, formatOnSave, ruff
│   ├── extensions.json            # recomendadas: Python, Ruff, Django, Thunder Client
│   └── launch.json                # runserver + attach al debugger
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── CLAUDE.md                      ← contexto permanente (raíz, no en docs/)
├── README.md
├── pyproject.toml                 # ruff, black, pytest, coverage
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
├── Procfile                       # Railway
├── railway.json
├── manage.py
│
├── config/                        # proyecto Django (NO "biolife" — evita colisión de import)
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── local.py
│   │   ├── staging.py
│   │   └── production.py
│   ├── urls_public.py             # rutas del esquema public (landing, panel SaaS)
│   ├── urls_tenant.py             # rutas dentro de un laboratorio
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── core/                      # base transversal. NO importa otras apps.
│   │   ├── models.py              # TenantBaseModel, TimeStampedModel, SoftDeleteQuerySet
│   │   ├── exceptions.py          # ApplicationError, ValidationError de dominio
│   │   ├── formulas/
│   │   │   ├── evaluator.py       # AST restringido
│   │   │   ├── parser.py          # extrae variables {XX} y {@yy}
│   │   │   └── graph.py           # orden topológico + detección de ciclos
│   │   ├── utils/
│   │   │   ├── dates.py           # edad en días, edad declarada, formato 12 h
│   │   │   ├── numbers.py         # separador decimal por tenant
│   │   │   └── hashing.py
│   │   ├── middleware.py          # activa timezone del tenant
│   │   ├── templatetags/core_tags.py
│   │   └── tests/
│   │
│   ├── tenants/                   # SHARED — public schema
│   │   ├── models.py              # Tenant, Domain, Plan, Subscription, SaaSInvoice
│   │   ├── services/
│   │   │   ├── provisioning.py    # crea esquema + siembra catálogo + admin inicial
│   │   │   ├── subscription.py
│   │   │   └── suspension.py
│   │   ├── selectors/metrics.py
│   │   ├── admin.py
│   │   ├── views.py               # panel SuperAdmin
│   │   └── tests/
│   │
│   ├── masterdata/                # SHARED — catálogos semilla
│   │   ├── models.py              # MasterSection, MasterUnit, MasterMethod, MasterAnalyte, Locality
│   │   ├── fixtures/
│   │   │   ├── localidades.json
│   │   │   ├── unidades.json
│   │   │   ├── metodos.json
│   │   │   └── catalogo_base.json
│   │   └── services/seeding.py    # copia el catálogo maestro al esquema de un tenant nuevo
│   │
│   ├── accounts/                  # TENANT
│   │   ├── models.py              # User, Role, Membership, AuditLog
│   │   ├── services/{user_management,auth,audit}.py
│   │   ├── selectors/user_queries.py
│   │   ├── permissions.py
│   │   └── tests/
│   │
│   ├── settings_lab/              # TENANT — configuración del laboratorio
│   │   ├── models.py              # TenantSettings
│   │   ├── services/branding.py
│   │   └── tests/
│   │
│   ├── patients/                  # TENANT
│   │   ├── models.py              # Patient, Guardian, PatientGuardian
│   │   ├── services/{patient_creation,guardian_linking,merge}.py
│   │   ├── selectors/patient_search.py
│   │   ├── forms.py · views.py · urls.py
│   │   └── tests/
│   │
│   ├── catalog/                   # TENANT — el núcleo configurable
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── structure.py       # Section, Unit, Method, Test, ParameterGroup
│   │   │   ├── parameters.py      # Parameter, CodedOptionSet, CodedOption
│   │   │   ├── references.py      # ReferenceRange
│   │   │   ├── profiles.py        # Profile, ProfileTest
│   │   │   └── observations.py    # ObservationTemplate
│   │   ├── services/
│   │   │   ├── test_builder.py
│   │   │   ├── formula_binding.py # parsea formula → depends_on, valida ciclos
│   │   │   ├── reference_resolver.py
│   │   │   └── import_export.py   # catálogo a/desde Excel
│   │   ├── selectors/catalog_queries.py
│   │   └── tests/
│   │
│   ├── orders/                    # TENANT
│   │   ├── models.py              # Order, OrderItem, Sample
│   │   ├── services/{order_creation,sampling,numbering,status}.py
│   │   ├── selectors/{worklist,order_queries}.py
│   │   └── tests/
│   │
│   ├── results/                   # TENANT
│   │   ├── models.py              # Result, ResultValue, ResultAmendment, ResultSignature
│   │   ├── services/
│   │   │   ├── result_entry.py
│   │   │   ├── calculation.py     # ejecuta el motor de fórmulas sobre una orden
│   │   │   ├── flagging.py        # ALTO/BAJO/CRÍTICO contra el rango resuelto
│   │   │   ├── validation.py      # validación médica + congelado de referencias
│   │   │   └── amendment.py
│   │   ├── selectors/pending.py
│   │   └── tests/
│   │
│   ├── reporting/                 # TENANT
│   │   ├── models.py              # Report
│   │   ├── services/{pdf_builder,delivery,verification}.py
│   │   ├── templates/reporting/   # informe_base.html, secciones parciales
│   │   └── tests/
│   │
│   ├── billing/                   # TENANT — cobro al paciente (fase tardía)
│   │   ├── models.py              # PriceList, Payment, PatientInvoice
│   │   └── services/
│   │
│   ├── integrations/              # TENANT — analizadores
│   │   ├── models.py              # Instrument, InstrumentMessage, InstrumentResult
│   │   ├── drivers/
│   │   │   ├── base.py            # Protocol InstrumentDriver
│   │   │   ├── astm.py
│   │   │   ├── hl7v2.py
│   │   │   └── registry.py
│   │   ├── services/{ingestion,mapping}.py
│   │   └── tests/fixtures/        # mensajes crudos reales de cada analizador
│   │
│   └── sync/                      # TENANT — offline
│       ├── models.py              # SyncQueueEntry, SyncConflict
│       ├── services/{apply,conflict}.py
│       ├── api/views.py           # POST /api/sync/push, GET /api/sync/pull
│       └── tests/
│
├── static/
│   ├── src/                       # fuentes (tailwind input, js modules)
│   ├── dist/                      # compilado
│   ├── pwa/
│   │   ├── manifest.webmanifest
│   │   ├── service-worker.js
│   │   └── db/dexie-schema.js
│   └── img/biolife-logo.png
│
├── templates/
│   ├── base_public.html
│   ├── base_tenant.html           # aplica branding del tenant
│   ├── components/
│   └── partials/                  # fragmentos HTMX
│
├── locale/es/LC_MESSAGES/
├── scripts/
│   ├── seed_demo_tenant.py
│   ├── import_catalog_from_excel.py
│   └── check_tenant_isolation.py  # prueba de humo de aislamiento
│
├── gateway/                       # agente local — se despliega aparte del SaaS
│   ├── README.md
│   ├── main.py
│   └── drivers/
│
└── docs/
    ├── 00_ARQUITECTURA.md
    ├── 01_MODELO_DATOS.md
    ├── 02_ESTRUCTURA_PROYECTO.md
    ├── 03_CONVENCIONES.md
    ├── 04_HALLAZGOS_FORMATOS.md
    ├── DECISIONES.md
    ├── ESTADO.md
    ├── COWORK_Y_CONTEXTO.md
    └── roadmap/
        ├── 00_INDICE.md
        ├── _PLANTILLA_FASE.md
        ├── 01_setup_y_tenants.md
        ├── 02_accounts_y_roles.md
        └── ... (una por fase)
```

## Notas de diseño de la estructura

**`config/` y no `biolife/`** — si el paquete del proyecto se llama igual que el producto,
tarde o temprano alguien escribe `from biolife import ...` esperando una app y obtiene el
módulo de settings. `config/` es inequívoco.

**`apps/catalog/models/` como paquete y no archivo único** — el catálogo tiene ~12 modelos.
Un `models.py` de 900 líneas es exactamente lo que el requisito de "cero monolito" busca evitar.
Las demás apps mantienen `models.py` plano hasta superar ~300 líneas.

**`gateway/` dentro del repo pero fuera del deploy** — comparte los esquemas de mensajes
con el backend, así que conviene versionarlo junto. Se excluye del build de Railway.

**`scripts/check_tenant_isolation.py`** — script que crea dos tenants, inserta datos en
ambos y verifica que ninguna consulta cruce. Se corre en CI. Es la red de seguridad más
importante del proyecto.
