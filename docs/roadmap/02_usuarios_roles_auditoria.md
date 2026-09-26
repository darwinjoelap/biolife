# FASE 02 — Usuarios, Roles y Auditoría

> **Modelo sugerido:** Sonnet
> **Duración estimada:** 1–2 sesiones
> **Depende de:** Fase 01
> **Bloquea a:** todas las fases con vistas autenticadas (04+)

---

## 1. Objetivo

Al terminar esta fase, cada tenant tiene su propio sistema de usuarios: login por
subdominio, un catálogo de roles con permisos, asignación de rol por usuario
(`Membership`), y un registro de acceso append-only (`AuditLog`) que deja constancia de
cada login. `TenantBaseModel.created_by` queda conectado al modelo de usuario real.

---

## 2. Contexto mínimo necesario

Decisión tomada en esta sesión (ver ADR pendiente en el cierre de esta fase):

- **`User` es un modelo propio** (`apps.accounts.User(AbstractUser)`), no el `auth.User`
  de Django. `AUTH_USER_MODEL = "accounts.User"`. Esto obliga a **recrear los esquemas
  `demo_uno` y `demo_dos`** creados en la Fase 01 (son solo datos de prueba, sin costo
  real de recrearlos) porque ya tenían migrada la tabla `auth_user` original.
- `apps.accounts` es una **TENANT_APP**: cada laboratorio tiene sus propios usuarios,
  aislados por esquema — coherente con ADR-001.

Decisiones ya tomadas en fases previas, **no renegociar**:
- Services & Selectors: la lógica vive en `apps/accounts/services/`, las consultas en
  `apps/accounts/selectors/user_queries.py`.
- Español en datos/UI, inglés en código (`docs/03_CONVENCIONES.md`).

**Nota de alcance sobre los "7 roles":** `docs/00_ARQUITECTURA.md` lista
`SUPERADMIN_PLATAFORMA, ADMIN_LAB, BIOANALISTA, TECNICO, RECEPCION, FACTURACION,
SOLO_LECTURA` (7). `SUPERADMIN_PLATAFORMA` **no** es un `Role` de tenant — es
`PlatformUser` en el esquema `public` (Fase 12, panel SuperAdmin). Esta fase siembra
los **6 roles de tenant**; el criterio de salida "7 roles" del índice se cumple entre
esta fase y la Fase 12.

Documentos a leer antes de empezar:
- `CLAUDE.md`
- `docs/00_ARQUITECTURA.md` — sección 7 "Seguridad y cumplimiento"
- `docs/01_MODELO_DATOS.md` — sección B (`TenantSettings`, `Role`/`Membership`, `AuditLog`)
- `docs/02_ESTRUCTURA_PROYECTO.md` — árbol de `apps/accounts/`
- `docs/DECISIONES.md` — ADR-001, ADR-007, ADR-008 (schema_context, transaction=True)

---

## 3. Alcance

### Incluye
- [ ] App `apps.accounts` (TENANT_APP) con `User`, `Role`, `Membership`, `AuditLog`
- [ ] `AUTH_USER_MODEL = "accounts.User"` + recreación de `demo_uno`/`demo_dos`
- [ ] `TenantBaseModel.created_by` (FK a `accounts.User`, null=True)
- [ ] Fixture con los 6 roles de tenant (`code`, `name`, `permissions` JSONB, `is_system=True`)
- [ ] `apps/accounts/permissions.py`: helpers de chequeo de rol/permiso + mixin de vista
- [ ] Login / logout por tenant (`django.contrib.auth` views, plantillas propias)
- [ ] `AuditLog` append-only: se registra un evento en cada login exitoso y fallido
- [ ] `provision_tenant()` actualizado: crea el usuario `ADMIN_LAB` inicial del laboratorio
- [ ] Comando de management `crear_usuario` (nombre, email, rol, laboratorio activo)
- [ ] Tests: creación de usuario, asignación de rol, login, `AuditLog` inmutable, aislamiento

### NO incluye (explícito)
- ❌ `SUPERADMIN_PLATAFORMA` / `PlatformUser` / panel SuperAdmin → **Fase 12**
- ❌ 2FA (`django-otp`), `django-axes`, rate limiting de login → **Fase 18**
- ❌ `TenantSettings`, branding → **Fase 03**
- ❌ Auditoría de acceso a **datos clínicos** (quién vio qué historia) → se activa cuando
  existan esos modelos (Fases 04+); esta fase sólo dejar listo el mecanismo (`log_action()`)
- ❌ Recuperación de contraseña por email (requiere `EMAIL_BACKEND` real) → queda con
  `django.contrib.auth` por defecto (consola en local), se revisita en Fase 17
- ❌ Permisos granulares por objeto — sólo por rol, vía `permissions` JSONB del `Role`

---

## 4. Pre-requisitos verificables

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"
python manage.py check
# Esperado: 0 errores (estado de cierre de Fase 01)
pytest -q
# Esperado: 9 passed (estado de cierre de Fase 01)
```

---

## 5. Tareas

### Tarea 1 — Modelo `User` propio y `AUTH_USER_MODEL`

**Archivos:** `apps/accounts/__init__.py`, `apps/accounts/apps.py`, `apps/accounts/models.py` (crear)

```python
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Usuario de un laboratorio (tenant). Aislado por esquema."""

    phone = models.CharField("Teléfono", max_length=30, blank=True, default="")
    professional_license = models.CharField(
        "Nº de colegiatura", max_length=40, blank=True, default=""
    )

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
```

En `config/settings/base.py`:
```python
AUTH_USER_MODEL = "accounts.User"

TENANT_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "apps.core",
    "apps.accounts",   # nueva
]
```

> **Trampa:** `AUTH_USER_MODEL` sólo se puede fijar sobre un esquema **sin** la tabla
> `auth_user` ya migrada con el modelo por defecto. `public` nunca migró `auth` como
> tenant app (sólo `demo_uno`/`demo_dos` lo hicieron). Hay que **recrear** esos dos
> esquemas de prueba — no basta con `makemigrations`.

**Criterio de aceptación:**
```powershell
python manage.py makemigrations accounts
python manage.py migrate_schemas --shared
```

---

### Tarea 2 — Recrear los tenants demo con el nuevo `User`

**Qué hacer:** borrar `demo_uno` y `demo_dos` (son datos de prueba) y recrearlos con
`provision_tenant()` para que su esquema se cree ya con `apps.accounts` migrada.

```powershell
python manage.py shell -c "
from django_tenants.utils import schema_context, get_public_schema_name
from apps.tenants.models import Tenant
with schema_context(get_public_schema_name()):
    Tenant.objects.filter(schema_name__in=['demo_uno', 'demo_dos']).delete(force_drop=True)
"
python manage.py crear_laboratorio --nombre "Lab Demo Uno" --schema demo_uno --subdominio demo1
python manage.py crear_laboratorio --nombre "Lab Demo Dos" --schema demo_dos --subdominio demo2
```

**Criterio de aceptación:**
```powershell
psql -d biolife -c "\dt demo_uno.*" | Select-String "accounts_user"
# Esperado: la tabla existe
```

---

### Tarea 3 — `Role` y `Membership`

**Archivos:** `apps/accounts/models.py` (ampliar), `apps/accounts/fixtures/roles.json` (crear)

```python
class Role(models.Model):
    class Code(models.TextChoices):
        ADMIN_LAB = "ADMIN_LAB", "Administrador del laboratorio"
        BIOANALISTA = "BIOANALISTA", "Bioanalista"
        TECNICO = "TECNICO", "Técnico"
        RECEPCION = "RECEPCION", "Recepción"
        FACTURACION = "FACTURACION", "Facturación"
        SOLO_LECTURA = "SOLO_LECTURA", "Sólo lectura"

    code = models.CharField(max_length=20, choices=Code.choices, unique=True)
    name = models.CharField("Nombre", max_length=80)
    permissions = models.JSONField("Permisos", default=dict, blank=True)
    is_system = models.BooleanField("Rol del sistema", default=True)

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="memberships")
    is_active = models.BooleanField("Activo", default=True)

    class Meta:
        verbose_name = "Membresía"
        verbose_name_plural = "Membresías"
        unique_together = [("user", "role")]
```

> Sólo `ADMIN_LAB` y `BIOANALISTA` validan resultados (regla ya documentada en
> `docs/00_ARQUITECTURA.md` §7) — esa regla se **aplica** en la Fase 10 (captura y
> validación), aquí sólo se modela el dato.

`permissions` (JSONB) — claves mínimas para esta fase, se amplía en fases posteriores:
```json
{"puede_validar_resultados": false, "puede_gestionar_usuarios": false, "puede_facturar": false}
```

**Criterio de aceptación:**
```powershell
python manage.py loaddata roles
python manage.py shell -c "from apps.accounts.models import Role; print(Role.objects.count())"
# Esperado: 6
```

---

### Tarea 4 — `AuditLog` append-only

**Archivos:** `apps/accounts/models.py` (ampliar), `apps/accounts/services/audit.py` (crear)

```python
class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=50)          # "LOGIN_OK", "LOGIN_FALLIDO", "LOGOUT"
    model_name = models.CharField(max_length=100, blank=True, default="")
    object_id = models.CharField(max_length=64, blank=True, default="")
    changes = models.JSONField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Registro de auditoría"
        verbose_name_plural = "Registros de auditoría"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ApplicationError("AuditLog es append-only: no se puede modificar un registro.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ApplicationError("AuditLog es append-only: no se puede borrar un registro.")
```

**`apps/accounts/services/audit.py`:**
```python
def log_action(
    *, action: str, user: User | None = None, model_name: str = "",
    object_id: str = "", changes: dict | None = None,
    ip: str | None = None, user_agent: str = "",
) -> AuditLog:
    """Único punto de escritura de AuditLog en todo el sistema."""
```

Conectar a las señales `user_logged_in` / `user_logged_in_failed` / `user_logged_out` de
`django.contrib.auth.signals` en `apps/accounts/apps.py::ready()`.

**Criterio de aceptación:** login exitoso desde el navegador → una fila en `AuditLog` con
`action="LOGIN_OK"`.

---

### Tarea 5 — Permisos y login

**Archivos:** `apps/accounts/permissions.py`, `apps/accounts/urls.py`,
`templates/accounts/login.html` (crear); `config/urls_tenant.py` (ampliar)

```python
# apps/accounts/permissions.py
def has_role(user, *codes: str) -> bool:
    if not user.is_authenticated:
        return False
    return user.memberships.filter(role__code__in=codes, is_active=True).exists()


class RoleRequiredMixin:
    allowed_roles: tuple[str, ...] = ()

    def dispatch(self, request, *args, **kwargs):
        if not has_role(request.user, *self.allowed_roles):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
```

`urls_tenant.py`: `/cuenta/login/`, `/cuenta/logout/` usando
`django.contrib.auth.views.LoginView`/`LogoutView` con `template_name` propio.
`LOGIN_URL = "accounts:login"` en settings.

**Criterio de aceptación:** `http://demo1.localhost:8000/cuenta/login/` muestra el
formulario y autentica contra los usuarios de `demo_uno` únicamente.

---

### Tarea 6 — `provision_tenant()` crea el usuario administrador inicial

**Archivos:** `apps/tenants/services/provisioning.py` (ampliar), `apps/accounts/services/user_management.py` (crear)

Ampliar la firma:
```python
def provision_tenant(
    *, name: str, schema_name: str, subdomain: str,
    admin_email: str, admin_password: str | None = None,   # nuevo
    plan: Plan | None = None, rif: str | None = None, trial_days: int = 30,
) -> Tenant:
```

Después de crear el dominio, dentro del `schema_context(schema_name)` del propio tenant
recién creado: crear el `User` admin, el `Role` `ADMIN_LAB` (si no existe) y su
`Membership`. Si `admin_password` es `None`, generar una contraseña temporal y devolverla
(no imprimirla — el comando de management sí la imprime).

**Criterio de aceptación:**
```powershell
python manage.py crear_laboratorio --nombre "Lab Demo Tres" --schema demo_tres --subdominio demo3 --admin-email admin@demo3.test
# Esperado: imprime la contraseña temporal generada, un solo Membership ADMIN_LAB
```

---

### Tarea 7 — `TenantBaseModel.created_by`

**Archivos:** `apps/core/models.py` (ampliar)

```python
class TenantBaseModel(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="+",
    )
    is_active = models.BooleanField("Activo", default=True)

    class Meta:
        abstract = True
```

> `apps.core` no puede importar `apps.accounts.User` directamente (regla de CLAUDE.md:
> "Ningún import cruzado entre apps de dominio"). Usar la referencia como string
> `"accounts.User"`, que Django resuelve sin import.

**Criterio de aceptación:** `python manage.py check` sin errores (no hay todavía modelos
concretos que hereden de `TenantBaseModel` con datos, así que no hace falta migración de
datos, sólo de esquema).

---

### Tarea 8 — Tests

**Archivos:** `apps/accounts/tests/test_roles.py`, `apps/accounts/tests/test_audit.py`,
`apps/accounts/tests/test_login.py` (crear)

Casos obligatorios:
1. Crear un `User`, asignarle `Membership(role=ADMIN_LAB)`, `has_role(user, "ADMIN_LAB")` → `True`.
2. `has_role` con rol inactivo (`Membership.is_active=False`) → `False`.
3. Login exitoso crea un `AuditLog` con `action="LOGIN_OK"`.
4. Login fallido crea un `AuditLog` con `action="LOGIN_FALLIDO"` y `user=None`.
5. Modificar un `AuditLog` existente (`.save()` con `pk` ya asignado) levanta `ApplicationError`.
6. Borrar un `AuditLog` levanta `ApplicationError`.
7. Un `User` creado en `demo_uno` no es visible desde `demo_dos` (aislamiento, ya cubierto
   en `test_isolation.py` con `auth.User` — repetir con el `User` propio).

**Criterio de aceptación:**
```powershell
pytest -q
ruff check .
```

---

### Tarea 9 — Cierre documental

**Archivos:** `docs/ESTADO.md`, `docs/DECISIONES.md` (actualizar)

- `ESTADO.md`: Fase 02 completa, qué existe, qué sigue (Fase 03).
- `DECISIONES.md`: nuevo ADR — `User` personalizado en vez de `auth.User` (contexto:
  coincidir con `docs/02_ESTRUCTURA_PROYECTO.md` y permitir campos propios; consecuencia:
  hubo que recrear `demo_uno`/`demo_dos`). Documentar también la aclaración de los "7
  roles" (6 de tenant + `SUPERADMIN_PLATAFORMA` en Fase 12).

---

## 6. Criterios de salida (Definition of Done)

- [ ] `AUTH_USER_MODEL = "accounts.User"`, migrado en `public`, `demo_uno`, `demo_dos`
- [ ] 6 roles de tenant sembrados vía fixture
- [ ] Login/logout funcional en `http://demo1.localhost:8000/cuenta/login/`
- [ ] `provision_tenant()` crea el usuario `ADMIN_LAB` inicial de cada laboratorio nuevo
- [ ] Cada login exitoso/fallido queda en `AuditLog`; un `AuditLog` no se puede editar ni borrar
- [ ] `TenantBaseModel.created_by` apunta a `accounts.User`
- [ ] `pytest -q` en verde, incluidos los 7 casos de la Tarea 8
- [ ] `ruff check .` sin errores
- [ ] `docs/ESTADO.md` y `docs/DECISIONES.md` actualizados

---

## 7. Riesgos y trampas conocidas

| Riesgo | Señal | Mitigación |
|---|---|---|
| `AUTH_USER_MODEL` cambiado con esquemas ya migrados | `InconsistentMigrationHistory` o tabla `auth_user` duplicada/huérfana | Recrear `demo_uno`/`demo_dos` (Tarea 2) antes de tocar nada más |
| Señales de auth no conectadas | Login funciona pero `AuditLog` queda vacío | Conectar en `AppConfig.ready()`, no en `models.py` (import circular) |
| `permissions` JSONB usado para autorizar sin pasar por `has_role()` | Lógica de permisos duplicada e inconsistente | Todo chequeo de rol pasa por `apps/accounts/permissions.py` |
| `apps.core` importando `apps.accounts.User` directo | Rompe la regla de "cero import cruzado" y crea dependencia circular | FK con string `"accounts.User"` |
| Contraseña temporal del admin inicial impresa en logs de producción | Filtración de credencial | Sólo el comando de management la imprime a stdout local; el service la devuelve, no la loguea |

---

## 8. Entrega

Mismo formato que la Fase 01:
1. Índice de archivos creados/modificados por tarea.
2. Un bloque de código por archivo, ruta completa encima. Archivos existentes: sólo el
   fragmento que cambia.
3. Comandos a ejecutar, en orden, en PowerShell.
4. Lista explícita de lo que quedó pendiente, incompleto o no verificado.
5. Mensaje de commit sugerido.

Commit sugerido:
```
feat(accounts): usuarios propios, roles de tenant y auditoría de acceso

- User personalizado (AUTH_USER_MODEL=accounts.User), reemplaza auth.User
- Role/Membership con los 6 roles de tenant
- AuditLog append-only conectado a señales de login
- provision_tenant() crea el usuario ADMIN_LAB inicial
- TenantBaseModel.created_by conectado al modelo de usuario real
```
