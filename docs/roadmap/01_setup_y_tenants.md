# FASE 01 — Setup del proyecto y Multi-Tenancy

> **Modelo sugerido:** Sonnet
> **Duración estimada:** 1–2 sesiones
> **Depende de:** ninguna
> **Bloquea a:** todas las demás fases

---

## 1. Objetivo

Al terminar esta fase existe un proyecto Django funcional con multi-tenancy por esquemas
de PostgreSQL. Se pueden crear laboratorios (tenants), cada uno con su propio esquema y
subdominio, y está **demostrado con una prueba automatizada** que los datos de un tenant
no son accesibles desde otro. No hay todavía modelos de dominio: sólo la infraestructura
y el panel mínimo para provisionar tenants.

---

## 2. Contexto mínimo necesario

Biolife es un SaaS multi-tenant para laboratorios clínicos en Venezuela. Cada laboratorio
cliente es un tenant aislado. Interfaz y datos en español; código en inglés.

Decisiones ya tomadas, **no renegociar**:

- Multi-tenancy con `django-tenants` usando **esquemas de PostgreSQL**, no discriminador `tenant_id`.
- Enrutamiento por **subdominio**. Esquema `public` para plataforma; un esquema por laboratorio.
- Paquete del proyecto Django: `config/`, **no** `biolife/`.
- Settings dividido: `config/settings/{base,local,staging,production}.py`.
- Zona horaria por defecto `America/Caracas`, `USE_TZ = True`, hora en formato 12 h.
- Arquitectura Services & Selectors: las vistas no tocan el ORM.
- Entorno de desarrollo: **Windows + PowerShell + VS Code**, con múltiples versiones de
  Python instaladas. Verificar el venv activo es siempre el primer paso.

⚠️ **Trampa crítica de esta fase:** `django-tenants` cambia de esquema con `SET search_path`,
que es estado de sesión. Un pooler de PostgreSQL en modo *transaction* rompe el aislamiento
de forma silenciosa e intermitente. La conexión debe ser directa o en modo *session*.

Documentos a leer antes de empezar:
- `CLAUDE.md` (raíz del repo)
- `docs/02_ESTRUCTURA_PROYECTO.md` — árbol completo de carpetas
- `docs/03_CONVENCIONES.md` — secciones "Nomenclatura" y "Reglas de código"
- `docs/01_MODELO_DATOS.md` — **sólo la sección A (esquema public)**

---

## 3. Alcance

### Incluye
- [ ] Estructura de carpetas completa según `docs/02_ESTRUCTURA_PROYECTO.md` (carpetas vacías con `__init__.py` donde aplique)
- [ ] `requirements/` en tres archivos
- [ ] Settings dividido y configurado para `django-tenants`
- [ ] App `apps.core` con `TenantBaseModel` y `ApplicationError`
- [ ] App `apps.tenants` con `Tenant`, `Domain`, `Plan`, `Subscription`
- [ ] App `apps.masterdata` con `Locality` y fixture de localidades
- [ ] Service `provision_tenant()` que crea esquema + dominio + suscripción
- [ ] Comando de management `crear_laboratorio`
- [ ] Middleware que activa la zona horaria del tenant
- [ ] Health check que verifica modo de conexión y aislamiento
- [ ] Test automatizado de aislamiento entre tenants
- [ ] `.env.example`, `.gitignore`, `pyproject.toml`, `.vscode/settings.json`

### NO incluye (explícito)
- ❌ Modelo de usuario personalizado, roles ni autenticación → **Fase 02**
- ❌ `TenantSettings`, branding, logo → **Fase 03**
- ❌ Pacientes, catálogo, órdenes, resultados → Fases 04+
- ❌ Panel visual de SuperAdmin con métricas → **Fase 12** (esta fase sólo deja el `admin.py`)
- ❌ Cloudinary → **Fase 03**
- ❌ Despliegue en Railway → **Fase 17** (esta fase deja `Procfile` y `production.py` listos, sin desplegar)
- ❌ Service Worker, manifest, PWA → **Fase 13**
- ❌ `SaaSInvoice`, `TenantUsageSnapshot` → **Fase 12**
- ❌ Estilos, Tailwind, plantillas más allá de un `base_public.html` mínimo

---

## 4. Pre-requisitos verificables

```powershell
# 1. Crear y activar el entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. VERIFICACIÓN OBLIGATORIA del intérprete
python -c "import sys; print(sys.executable)"
# Esperado: ...\biolife\.venv\Scripts\python.exe
# Si apunta a otra ruta, DETENERSE y corregir antes de continuar.

python --version
# Esperado: Python 3.12.x

# 3. PostgreSQL local accesible
psql --version
# Esperado: psql (PostgreSQL) 16.x
```

Si `Activate.ps1` falla por política de ejecución:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

---

## 5. Tareas

### Tarea 1 — Estructura de carpetas y archivos de configuración

**Archivos:** (crear)
`.gitignore`, `.env.example`, `pyproject.toml`,
`requirements/base.txt`, `requirements/local.txt`, `requirements/production.txt`,
`.vscode/settings.json`, `.vscode/extensions.json`, `Procfile`, `railway.json`

**Qué hacer:** crear el árbol de `docs/02_ESTRUCTURA_PROYECTO.md` limitado a las apps de
esta fase: `core`, `tenants`, `masterdata`. Las demás carpetas de `apps/` **no se crean aún**.

`requirements/base.txt`:
```
Django==5.1.*
django-tenants==3.7.*
psycopg[binary]==3.2.*
python-decouple==3.8
django-environ==0.11.*
whitenoise==6.7.*
gunicorn==23.0.*
```

`requirements/local.txt`:
```
-r base.txt
pytest==8.3.*
pytest-django==4.9.*
factory-boy==3.3.*
ruff==0.7.*
django-debug-toolbar==4.4.*
ipython
```

`requirements/production.txt`:
```
-r base.txt
sentry-sdk==2.*
```

`.env.example`:
```
DJANGO_SETTINGS_MODULE=config.settings.local
SECRET_KEY=cambiar-en-produccion
DEBUG=True
ALLOWED_HOSTS=.localhost,127.0.0.1
DATABASE_URL=postgres://postgres:postgres@localhost:5432/biolife
BASE_DOMAIN=localhost
TIME_ZONE=America/Caracas
```

**Criterio de aceptación:**
```powershell
pip install -r requirements/local.txt
python -c "import django_tenants; print(django_tenants.__version__)"
```

---

### Tarea 2 — Proyecto Django y settings

**Archivos:** `manage.py`, `config/__init__.py`, `config/settings/{__init__,base,local,staging,production}.py`,
`config/{urls_public,urls_tenant,wsgi,asgi}.py` (crear)

**Qué hacer:**

```powershell
django-admin startproject config .
```
Luego convertir `config/settings.py` en el paquete `config/settings/`.

En `config/settings/base.py`:

```python
DATABASES = {
    "default": {
        "ENGINE": "django_tenants.postgresql_backend",
        # resto desde DATABASE_URL
    }
}

DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)

MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",   # PRIMERO, sin excepción
    "apps.core.middleware.TenantTimezoneMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # ... resto estándar
]

SHARED_APPS = [
    "django_tenants",
    "apps.tenants",
    "apps.masterdata",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
]

TENANT_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "apps.core",
]

INSTALLED_APPS = list(SHARED_APPS) + [
    a for a in TENANT_APPS if a not in SHARED_APPS
]

TENANT_MODEL = "tenants.Tenant"
TENANT_DOMAIN_MODEL = "tenants.Domain"

PUBLIC_SCHEMA_URLCONF = "config.urls_public"
ROOT_URLCONF = "config.urls_tenant"

LANGUAGE_CODE = "es-ve"
TIME_ZONE = "America/Caracas"
USE_TZ = True
USE_I18N = True
USE_L10N = True
```

> **Ojo con `INSTALLED_APPS`:** `django_tenants` exige que sea exactamente la unión de
> `SHARED_APPS` y `TENANT_APPS` sin duplicados y respetando el orden. Un error aquí produce
> migraciones que corren en el esquema equivocado.

**Criterio de aceptación:**
```powershell
python manage.py check
# Esperado: System check identified no issues (0 silenced).
```

---

### Tarea 3 — App `apps.core`

**Archivos:** `apps/core/__init__.py`, `apps/core/apps.py`, `apps/core/models.py`,
`apps/core/exceptions.py`, `apps/core/middleware.py`, `apps/core/utils/__init__.py`,
`apps/core/utils/dates.py` (crear)

**`apps/core/models.py`:**
```python
import uuid
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Creado el", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizado el", auto_now=True)

    class Meta:
        abstract = True


class TenantBaseModel(TimeStampedModel):
    """Base de todo modelo que vive dentro del esquema de un laboratorio."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    is_active = models.BooleanField("Activo", default=True)

    class Meta:
        abstract = True
```

> `created_by` se agrega en **Fase 02**, cuando exista el modelo de usuario. No crear
> ahora una FK a `auth.User` que habrá que migrar después.

**`apps/core/exceptions.py`:**
```python
class ApplicationError(Exception):
    """Error de regla de negocio. Mensaje apto para mostrar al usuario."""

    def __init__(self, message: str, extra: dict | None = None):
        super().__init__(message)
        self.message = message
        self.extra = extra or {}
```

**`apps/core/utils/dates.py`:** funciones `age_in_days(birth_date, reference_date)` y
`format_time_12h(dt, tz)` que devuelve `"6:00 A.M."` (con puntos, como en los formatos del
laboratorio). Ambas con tests.

**`apps/core/middleware.py`:** `TenantTimezoneMiddleware` que activa
`django.utils.timezone.activate()` con la zona del tenant. En esta fase lee de
`settings.TIME_ZONE`; en **Fase 03** pasará a leer de `TenantSettings`. Dejar el punto de
extensión comentado con `# FASE 03:`.

**Criterio de aceptación:**
```powershell
pytest apps/core/tests -q
```

---

### Tarea 4 — App `apps.masterdata`

**Archivos:** `apps/masterdata/models.py`, `apps/masterdata/fixtures/localidades.json`,
`apps/masterdata/admin.py` (crear)

**Modelo:**
```python
class Locality(models.Model):
    name = models.CharField("Nombre", max_length=120)
    state = models.CharField("Estado", max_length=80)
    municipality = models.CharField("Municipio", max_length=120, blank=True, default="")

    class Meta:
        verbose_name = "Localidad"
        verbose_name_plural = "Localidades"
        unique_together = [("name", "state")]
        ordering = ["state", "name"]
```

Fixture con las 21 localidades de `docs/04_HALLAZGOS_FORMATOS.md`, sección 12
(estados Guárico y Aragua).

**Criterio de aceptación:**
```powershell
python manage.py loaddata localidades
python manage.py shell -c "from apps.masterdata.models import Locality; print(Locality.objects.count())"
# Esperado: 21
```

---

### Tarea 5 — App `apps.tenants`: modelos

**Archivos:** `apps/tenants/models.py`, `apps/tenants/admin.py` (crear)

```python
from django_tenants.models import TenantMixin, DomainMixin
from django.db import models


class Tenant(TenantMixin):
    class Status(models.TextChoices):
        DEMO = "DEMO", "Demo"
        ACTIVO = "ACTIVO", "Activo"
        SUSPENDIDO = "SUSPENDIDO", "Suspendido"
        MOROSO = "MOROSO", "Moroso"
        CANCELADO = "CANCELADO", "Cancelado"

    name = models.CharField("Nombre del laboratorio", max_length=200)
    legal_name = models.CharField("Razón social", max_length=200, blank=True, default="")
    rif = models.CharField("RIF", max_length=20, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DEMO)
    onboarded_at = models.DateTimeField(auto_now_add=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    paid_until = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    auto_create_schema = True
    auto_drop_schema = False   # NUNCA True: un delete accidental borraría datos clínicos

    class Meta:
        verbose_name = "Laboratorio"
        verbose_name_plural = "Laboratorios"

    def __str__(self) -> str:
        return self.name


class Domain(DomainMixin):
    class Meta:
        verbose_name = "Dominio"
        verbose_name_plural = "Dominios"
```

Más `Plan` y `Subscription` según `docs/01_MODELO_DATOS.md` sección A.

> **`auto_drop_schema = False` no es negociable.** Con `True`, borrar un tenant desde el
> admin de Django elimina el esquema y todas las historias clínicas sin confirmación.

**Criterio de aceptación:**
```powershell
python manage.py makemigrations tenants masterdata
python manage.py migrate_schemas --shared
```

---

### Tarea 6 — Service de provisionamiento

**Archivos:** `apps/tenants/services/__init__.py`, `apps/tenants/services/provisioning.py`,
`apps/tenants/management/commands/crear_laboratorio.py` (crear)

**Firma exacta:**
```python
from apps.tenants.models import Tenant, Plan

def provision_tenant(
    *,
    name: str,
    schema_name: str,
    subdomain: str,
    plan: Plan | None = None,
    rif: str | None = None,
    trial_days: int = 30,
) -> Tenant:
    """
    Crea el laboratorio, su esquema, su dominio primario y su suscripción de prueba.
    Idempotente: si el schema_name ya existe, levanta ApplicationError sin tocar nada.
    """
```

Reglas:
- Validar `schema_name` contra `^[a-z][a-z0-9_]{2,30}$`. Rechazar `public`, `pg_*`, `information_schema`.
- Todo dentro de `transaction.atomic()`. Nota: la creación del esquema por `django-tenants`
  ocurre en el `save()` del tenant; si algo falla después, hay que borrar el esquema
  explícitamente en el manejo de la excepción.
- Devuelve el `Tenant`. No devuelve `HttpResponse` ni imprime nada.

**Comando:**
```powershell
python manage.py crear_laboratorio --nombre "Laboratorio Angelus" --schema angelus --subdominio angelus
```

**Criterio de aceptación:**
```powershell
python manage.py crear_laboratorio --nombre "Lab Demo Uno" --schema demo_uno --subdominio demo1
python manage.py crear_laboratorio --nombre "Lab Demo Dos" --schema demo_dos --subdominio demo2
psql -d biolife -c "\dn"
# Esperado: se listan public, demo_uno, demo_dos
```

---

### Tarea 7 — Health check de conexión y aislamiento

**Archivos:** `apps/core/checks.py`, `scripts/check_tenant_isolation.py` (crear)

**`apps/core/checks.py`:** un `django.core.checks` registrado que, al arrancar, ejecuta:
```sql
SHOW search_path;
SELECT current_setting('server_version_num')::int;
```
y advierte (nivel `Warning`, id `biolife.W001`) si detecta indicios de pooler en modo
transaction — por ejemplo, si `DATABASE_URL` apunta a un puerto de pooler conocido (6543)
o contiene `pgbouncer=true`.

> Esta comprobación existe porque el fallo que previene es silencioso: con un pooler en
> modo transaction todo funciona en desarrollo y falla bajo concurrencia en producción,
> mezclando datos entre laboratorios. Es el peor bug posible en este sistema.

**`scripts/check_tenant_isolation.py`:** crea dos tenants, inserta un registro de prueba
en cada uno, y verifica desde el contexto de cada tenant que no ve el del otro. Salida con
código 0 o 1 para uso en CI.

**Criterio de aceptación:**
```powershell
python scripts/check_tenant_isolation.py
# Esperado: "AISLAMIENTO VERIFICADO" y código de salida 0
```

---

### Tarea 8 — URLs, vista raíz y admin

**Archivos:** `config/urls_public.py`, `config/urls_tenant.py`,
`templates/base_public.html`, `templates/public/home.html` (crear)

- `urls_public.py`: `/admin/` (admin de Django con `Tenant`, `Domain`, `Plan`,
  `Subscription`, `Locality` registrados) y `/` con una página mínima que muestre
  "Biolife" y el logo.
- `urls_tenant.py`: `/` con una vista que muestre el nombre del tenant actual
  (`request.tenant.name`). Es la prueba visual de que el enrutamiento por subdominio funciona.

**Criterio de aceptación:**
```powershell
python manage.py runserver
```
- `http://localhost:8000/` → página pública de Biolife
- `http://demo1.localhost:8000/` → "Lab Demo Uno"
- `http://demo2.localhost:8000/` → "Lab Demo Dos"

> En Windows, los subdominios de `localhost` resuelven solos en Chrome y Edge. Si no,
> agregar a `C:\Windows\System32\drivers\etc\hosts`:
> ```
> 127.0.0.1 demo1.localhost
> 127.0.0.1 demo2.localhost
> ```

---

### Tarea 9 — Tests

**Archivos:** `pytest.ini` o sección `[tool.pytest.ini_options]` en `pyproject.toml`,
`conftest.py`, `apps/tenants/tests/test_provisioning.py`,
`apps/tenants/tests/test_isolation.py` (crear)

Casos obligatorios:
1. `provision_tenant` crea tenant, esquema, dominio y suscripción.
2. `schema_name` inválido levanta `ApplicationError`.
3. `schema_name` duplicado levanta `ApplicationError` y **no** deja esquema huérfano.
4. Un objeto creado en el tenant A no es visible desde el tenant B.
5. Un objeto creado en un tenant no es visible desde el esquema `public`.

**Criterio de aceptación:**
```powershell
pytest -q
# Esperado: todos los tests en verde
```

---

### Tarea 10 — Cierre documental

**Archivos:** `docs/ESTADO.md`, `docs/DECISIONES.md` (actualizar)

- `ESTADO.md`: fase 01 completa, qué existe, qué sigue.
- `DECISIONES.md`: registrar ADR-001 (esquemas vs discriminador), ADR-002 (`config/` como
  nombre del proyecto), ADR-003 (`auto_drop_schema=False`), y la **cadena de conexión
  exacta** que se está usando, con nota sobre el modo de pooling.

---

## 6. Especificaciones técnicas adicionales

### Variables de entorno

| Variable | Local | Producción |
|---|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.local` | `config.settings.production` |
| `SECRET_KEY` | cualquiera | generada, 50+ caracteres |
| `DEBUG` | `True` | `False` |
| `DATABASE_URL` | `postgres://postgres:postgres@localhost:5432/biolife` | inyectada por Railway |
| `BASE_DOMAIN` | `localhost` | `biolife.app` |
| `ALLOWED_HOSTS` | `.localhost,127.0.0.1` | `.biolife.app` |

### `.vscode/settings.json`

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}\\.venv\\Scripts\\python.exe",
  "python.terminal.activateEnvironment": true,
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": { "source.organizeImports": "explicit" }
  },
  "files.exclude": { "**/__pycache__": true, "**/.pytest_cache": true }
}
```

---

## 7. Criterios de salida (Definition of Done)

- [ ] `python manage.py check` sin errores ni advertencias inesperadas
- [ ] `python manage.py migrate_schemas --shared` corre limpio
- [ ] Dos tenants creados por comando de management
- [ ] `psql -d biolife -c "\dn"` muestra `public`, `demo_uno`, `demo_dos`
- [ ] Los tres subdominios responden correctamente en el navegador
- [ ] `python scripts/check_tenant_isolation.py` devuelve código 0
- [ ] `pytest -q` en verde, incluidos los 5 casos de la Tarea 9
- [ ] `ruff check .` sin errores
- [ ] `docs/ESTADO.md` y `docs/DECISIONES.md` actualizados
- [ ] `.env` **no** está versionado; `.env.example` sí

---

## 8. Riesgos y trampas conocidas

| Riesgo | Señal | Mitigación |
|---|---|---|
| Pooler en modo transaction | Datos que "aparecen" en el tenant equivocado bajo carga | Check `biolife.W001` de la Tarea 7; conexión directa o session pooling |
| `INSTALLED_APPS` mal construido | Migraciones en el esquema incorrecto; tablas duplicadas | `INSTALLED_APPS` = unión exacta de `SHARED_APPS` + `TENANT_APPS`, sin duplicados |
| `TenantMainMiddleware` no va primero | `request.tenant` inexistente, `AttributeError` | Es la **primera** entrada de `MIDDLEWARE`, antes de `SecurityMiddleware` |
| `auto_drop_schema = True` | Borrado silencioso de datos clínicos | Fijado en `False`. Verificar en revisión de código |
| Venv equivocado en PowerShell | `ModuleNotFoundError` intermitente | `python -c "import sys; print(sys.executable)"` antes de todo comando |
| Migraciones de apps compartidas corriendo en tenants | Tablas de `tenants` duplicadas en cada esquema | `DATABASE_ROUTERS = ("django_tenants.routers.TenantSyncRouter",)` |
| Subdominios de `localhost` sin resolver | 404 o "servidor no encontrado" | Entradas en el archivo `hosts` |

---

## 9. Entrega

La respuesta debe seguir este formato:

1. **Índice de archivos** creados y modificados, agrupados por tarea.
2. **Un bloque de código por archivo**, con la ruta completa encima de cada bloque.
   Archivos existentes: sólo el fragmento que cambia, con 2–3 líneas de contexto.
3. **Comandos a ejecutar**, en orden, en PowerShell.
4. **Lista explícita de lo que quedó pendiente, incompleto o no verificado.**
5. Mensaje de commit sugerido.

**No entregar ZIP ni bundle de archivos.** No reescribir archivos completos que ya existan.

Commit sugerido:
```
feat(setup): proyecto Django con multi-tenancy por esquemas

- django-tenants sobre PostgreSQL, enrutamiento por subdominio
- apps core, tenants y masterdata
- service de provisionamiento y comando crear_laboratorio
- health check de pooling y test automatizado de aislamiento
```
