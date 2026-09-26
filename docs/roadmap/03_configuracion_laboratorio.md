# FASE 03 — Configuración del Laboratorio

> **Modelo sugerido:** Haiku
> **Duración estimada:** 1 sesión
> **Depende de:** Fase 02
> **Bloquea a:** Fase 05 (catálogo, necesita `TenantSettings` para branding del informe más adelante)

---

## 1. Objetivo

Al terminar esta fase, cada tenant tiene su propio `TenantSettings` (singleton) con
branding básico, zona horaria y formato de hora/fecha. La zona horaria activa en cada
request ya no es fija (`settings.TIME_ZONE`) sino la del tenant, y las plantillas pueden
usar el color primario/secundario del laboratorio vía variables CSS.

---

## 2. Contexto mínimo necesario

**Decisión tomada en esta sesión: Cloudinary queda fuera de esta fase.** `logo` y
`banner` se modelan como `ImageField` con el storage local por defecto de Django
(`MEDIA_ROOT`/`MEDIA_URL`). La integración real con Cloudinary se hace en la **Fase 17**,
cuando haya credenciales de producción y un despliegue real donde probarla — no tiene
sentido cablearla antes. Cambiar el `storage` de un `ImageField` más adelante no exige
tocar el modelo, sólo `DEFAULT_FILE_STORAGE`/`STORAGES` en `production.py`.

Decisiones ya tomadas en fases previas, **no renegociar**:
- Español en datos/UI, inglés en código (`docs/03_CONVENCIONES.md`).
- Hora del sistema siempre en formato 12h (`docs/00_ARQUITECTURA.md`, `CLAUDE.md`) —
  `TenantSettings.time_format` se modela igual (existe en `01_MODELO_DATOS.md`) pero
  **no** se cablea todavía a `apps/core/utils/dates.py::format_time_12h()`; eso es
  trabajo de una fase de reportes (11+), no de esta.

**Corrección de arquitectura respecto a la Fase 01:** `TenantTimezoneMiddleware` vive hoy
en `apps.core`, pero para leer la zona horaria real necesita el modelo `TenantSettings`
de `apps.settings_lab`. `CLAUDE.md` es explícito: *"`core/` puede ser importado por
todos; `core/` no importa a nadie."* Por lo tanto el middleware **se muda** a
`apps.settings_lab.middleware`. Se documenta como ADR-012 en el cierre de esta fase.

Documentos a leer antes de empezar:
- `CLAUDE.md`
- `docs/01_MODELO_DATOS.md` — sección B, bloque `TenantSettings`
- `docs/02_ESTRUCTURA_PROYECTO.md` — árbol de `apps/settings_lab/`
- `docs/03_CONVENCIONES.md` — sección "Frontend" (variables CSS de branding)
- `docs/DECISIONES.md` — ADR-007 (schema_context en services de provisioning)

---

## 3. Alcance

### Incluye
- [ ] App `apps.settings_lab` (TENANT_APP) con modelo `TenantSettings` (singleton)
- [ ] `TenantTimezoneMiddleware` movido a `apps.settings_lab`, leyendo la zona horaria real
- [ ] `provision_tenant()` crea el `TenantSettings` por defecto de cada laboratorio nuevo
- [ ] `templates/base_tenant.html` con variables CSS de `color_primary`/`color_secondary`
- [ ] Context processor que expone `tenant_settings` a todas las plantillas de tenant
- [ ] `MEDIA_ROOT`/`MEDIA_URL` configurados (storage local, sin Cloudinary)
- [ ] Admin de `TenantSettings` (singleton: sin opción de "agregar" otro)
- [ ] Tests: creación automática del singleton, unicidad, zona horaria aplicada

### NO incluye (explícito)
- ❌ Integración real con Cloudinary → **Fase 17**
- ❌ Cablear `time_format`/`date_format`/`decimal_separator` a la lógica de reportes → Fases 11+
- ❌ UI/formulario para que el laboratorio edite su propia configuración → se usa el
  admin de Django por ahora; una vista propia es trabajo de una fase de UI no planificada aún
- ❌ `require_second_validation` con efecto real sobre la validación de resultados → Fase 10
- ❌ Despliegue a Railway (se evaluó adelantarlo y se decidió no hacerlo ahora)

---

## 4. Pre-requisitos verificables

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"
python manage.py check
# Esperado: 0 errores (estado de cierre de Fase 02)
pytest -q
# Esperado: 18 passed
```

---

## 5. Tareas

### Tarea 1 — App `apps.settings_lab` y modelo `TenantSettings`

**Archivos:** `apps/settings_lab/__init__.py`, `apps/settings_lab/apps.py`,
`apps/settings_lab/models.py` (crear)

```python
class TenantSettings(models.Model):
    class TimeFormat(models.TextChoices):
        H12 = "H12", "12 horas"
        H24 = "H24", "24 horas"

    class DecimalSeparator(models.TextChoices):
        COMA = "COMA", "Coma"
        PUNTO = "PUNTO", "Punto"

    # Identidad visual
    logo = models.ImageField("Logo", upload_to="branding/", blank=True, null=True)
    banner = models.ImageField("Banner", upload_to="branding/", blank=True, null=True)
    color_primary = models.CharField("Color primario", max_length=7, default="#1B5FA8")
    color_secondary = models.CharField("Color secundario", max_length=7, blank=True, default="")
    report_header_html = models.TextField("Cabecera del informe", blank=True, default="")
    report_footer_text = models.TextField("Pie del informe", blank=True, default="")
    report_disclaimer = models.TextField("Descargo de responsabilidad", blank=True, default="")
    # Contacto (impreso en el informe)
    phone = models.CharField("Teléfono", max_length=30, blank=True, default="")
    address = models.CharField("Dirección", max_length=255, blank=True, default="")
    email = models.EmailField("Correo", blank=True, default="")
    instagram = models.CharField("Instagram", max_length=100, blank=True, default="")
    website = models.URLField("Sitio web", blank=True, default="")
    # Localización
    timezone = models.CharField("Zona horaria", max_length=50, default="America/Caracas")
    time_format = models.CharField(max_length=3, choices=TimeFormat.choices, default=TimeFormat.H12)
    date_format = models.CharField("Formato de fecha", max_length=20, default="dd/MM/yyyy")
    decimal_separator = models.CharField(
        max_length=5, choices=DecimalSeparator.choices, default=DecimalSeparator.COMA
    )
    # Operación
    order_number_prefix = models.CharField(max_length=10, blank=True, default="")
    order_number_next = models.PositiveIntegerField(default=1)
    require_second_validation = models.BooleanField("Requiere doble validación", default=False)

    class Meta:
        verbose_name = "Configuración del laboratorio"
        verbose_name_plural = "Configuración del laboratorio"

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton forzado: un solo registro por esquema de tenant
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # no se borra: siempre debe existir configuración

    @classmethod
    def get_solo(cls) -> "TenantSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
```

> El patrón "singleton forzado con `pk=1`" es intencional y liviano (sin dependencia
> nueva tipo `django-solo`). No hace falta FK a `Tenant`: `TenantSettings` vive en el
> esquema del tenant, ya está aislado por diseño (ADR-001).

**Criterio de aceptación:**
```powershell
python manage.py makemigrations settings_lab
```

---

### Tarea 2 — `provision_tenant()` crea el `TenantSettings` por defecto

**Archivos:** `apps/settings_lab/services/__init__.py`,
`apps/settings_lab/services/branding.py` (crear); `apps/tenants/services/provisioning.py` (ampliar)

```python
# apps/settings_lab/services/branding.py
from apps.settings_lab.models import TenantSettings


def create_default_settings() -> TenantSettings:
    """Crea el TenantSettings del tenant activo si no existe. Debe llamarse dentro
    del schema_context() del tenant."""
    return TenantSettings.get_solo()
```

En `provisioning.py`, dentro del mismo `with schema_context(schema_name):` donde ya se
llama a `create_initial_admin(...)` (Fase 02, Tarea 6):
```python
from apps.settings_lab.services.branding import create_default_settings
# ...
with schema_context(schema_name):
    _, admin_password = create_initial_admin(email=admin_email, password=admin_password)
    create_default_settings()
```

**Criterio de aceptación:**
```powershell
python manage.py tenant_command shell --schema=demo_uno -c "from apps.settings_lab.models import TenantSettings; print(TenantSettings.objects.count())"
# Esperado: 1 (después de recrear demo_uno o de provisionar un tenant nuevo)
```

---

### Tarea 3 — Mudar `TenantTimezoneMiddleware` a `apps.settings_lab`

**Archivos:** `apps/settings_lab/middleware.py` (crear); `apps/core/middleware.py` (vaciar/eliminar
la clase); `config/settings/base.py` (ajustar `MIDDLEWARE`)

```python
# apps/settings_lab/middleware.py
from django.utils import timezone

from apps.settings_lab.models import TenantSettings


class TenantTimezoneMiddleware:
    """Activa la zona horaria real del tenant en cada request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tz = TenantSettings.get_solo().timezone
        timezone.activate(tz)
        response = self.get_response(request)
        timezone.deactivate()
        return response
```

En `base.py`:
```python
MIDDLEWARE = [
    "django_tenants.middleware.main.TenantMainMiddleware",
    "apps.settings_lab.middleware.TenantTimezoneMiddleware",   # antes: apps.core...
    ...
]
```

> **Trampa:** en el esquema `public`, no existe (ni debe existir) `TenantSettings` — ahí
> no debería ejecutarse este middleware para requests de plataforma. Como `public` no
> tiene la app en su `ROOT_URLCONF` de negocio (usa `urls_public.py`, sin vistas de
> tenant), en la práctica no se dispara ningún código que dependa de esto, pero si
> `TenantSettings.get_solo()` corre en `public` por error, crearía una fila fantasma allí.
> Verificar explícitamente en la Tarea 6 que `/admin/` en `localhost` sigue funcionando.

**Criterio de aceptación:** `python manage.py check` sin errores.

---

### Tarea 4 — `base_tenant.html` con variables CSS de branding

**Archivos:** `templates/base_tenant.html` (crear); `config/settings/base.py`
(`context_processors`, ampliar)

```python
# apps/settings_lab/context_processors.py
from apps.settings_lab.models import TenantSettings


def tenant_settings(request):
    if not hasattr(request, "tenant") or request.tenant.schema_name == "public":
        return {}
    return {"tenant_settings": TenantSettings.get_solo()}
```

```html
<!-- templates/base_tenant.html -->
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}{{ request.tenant.name }}{% endblock %}</title>
    <style>
        :root {
            --color-primary: {{ tenant_settings.color_primary|default:"#1B5FA8" }};
            --color-secondary: {{ tenant_settings.color_secondary|default:"#1B5FA8" }};
        }
    </style>
</head>
<body>
    {% block content %}{% endblock %}
</body>
</html>
```

Actualizar `templates/accounts/login.html` para extender `base_tenant.html` en vez de
ser un documento HTML completo aparte (reduce duplicación).

**Criterio de aceptación:** `http://demo1.localhost:8000/cuenta/login/` sigue
funcionando y el HTML incluye la variable `--color-primary`.

---

### Tarea 5 — `MEDIA_ROOT`/`MEDIA_URL`

**Archivos:** `config/settings/base.py`, `config/urls_tenant.py` (ampliar, sólo en `DEBUG`)

```python
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
```

```python
# config/urls_tenant.py — sólo para servir media en desarrollo
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

**Criterio de aceptación:** subir un logo desde el admin de `demo_uno` y verlo servido en
`http://demo1.localhost:8000/media/branding/...`.

---

### Tarea 6 — Admin de `TenantSettings` (singleton)

**Archivos:** `apps/settings_lab/admin.py` (crear)

```python
from django.contrib import admin

from apps.settings_lab.models import TenantSettings


@admin.register(TenantSettings)
class TenantSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not TenantSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
```

**Criterio de aceptación:** en `/admin/` de `demo1.localhost`, `TenantSettings` no ofrece
"Agregar" cuando ya existe la fila (creada por `provision_tenant()`), y no permite borrar.

---

### Tarea 7 — Tests

**Archivos:** `apps/settings_lab/tests/test_settings.py` (crear)

Casos obligatorios:
1. `TenantSettings.get_solo()` crea la fila si no existe.
2. Llamar `get_solo()` dos veces devuelve siempre el mismo `pk=1` (no se duplica).
3. `.delete()` no borra el registro.
4. `provision_tenant()` deja exactamente un `TenantSettings` en el tenant nuevo.
5. El middleware activa la zona horaria de `TenantSettings`, no la fija de `settings.TIME_ZONE`
   (crear un tenant de prueba con `timezone="America/Bogota"` y verificar
   `django.utils.timezone.get_current_timezone_name()` durante el request).

**Criterio de aceptación:**
```powershell
pytest -q
ruff check .
```

---

### Tarea 8 — Cierre documental

**Archivos:** `docs/ESTADO.md`, `docs/DECISIONES.md` (actualizar)

- `ESTADO.md`: Fase 03 completa, qué existe, qué sigue (Fase 04: pacientes).
- `DECISIONES.md`: ADR-012 (mudanza de `TenantTimezoneMiddleware` a `apps.settings_lab`
  por la regla "`core/` no importa a nadie"), ADR-013 (Cloudinary diferido a Fase 17,
  storage local mientras tanto).

---

## 6. Criterios de salida (Definition of Done)

- [ ] `apps.settings_lab` con `TenantSettings` singleton por tenant
- [ ] `provision_tenant()` crea el `TenantSettings` por defecto de cada laboratorio nuevo
- [ ] `TenantTimezoneMiddleware` vive en `apps.settings_lab` y usa la zona horaria real
- [ ] `base_tenant.html` con `--color-primary`/`--color-secondary` funcionando
- [ ] Login sigue funcionando después de migrar su template a `base_tenant.html`
- [ ] Subida de logo/banner funcional con storage local (sin Cloudinary)
- [ ] Admin de `TenantSettings` bloquea agregar un segundo registro y bloquea borrar
- [ ] `pytest -q` en verde, incluidos los 5 casos de la Tarea 7
- [ ] `ruff check .` sin errores
- [ ] `docs/ESTADO.md` y `docs/DECISIONES.md` actualizados

---

## 7. Riesgos y trampas conocidas

| Riesgo | Señal | Mitigación |
|---|---|---|
| `apps.core` importando `apps.settings_lab` | Rompe "core no importa a nadie"; import circular | Middleware vive en `apps.settings_lab`, no en `core` (Tarea 3) |
| `TenantSettings` creado sin querer en `public` | Fila fantasma en el esquema público | Context processor corta si `request.tenant.schema_name == "public"` |
| Olvidar mover el `MIDDLEWARE` en `base.py` al mudar la clase | `ModuleNotFoundError` o middleware duplicado | Un solo `sed`/edición del path, verificar con `manage.py check` |
| Singleton violado por `bulk_create` u ORM directo sin pasar por `get_solo()` | Dos filas con distinto `pk`, comportamiento inconsistente | `save()` fuerza `pk=1` siempre; documentarlo en el docstring del modelo |

---

## 8. Entrega

Mismo formato que las fases anteriores:
1. Índice de archivos creados/modificados por tarea.
2. Un bloque de código por archivo, ruta completa encima. Archivos existentes: sólo el
   fragmento que cambia.
3. Comandos a ejecutar, en orden, en PowerShell.
4. Lista explícita de lo que quedó pendiente, incompleto o no verificado.
5. Mensaje de commit sugerido.

Commit sugerido:
```
feat(settings_lab): configuración por tenant, branding y zona horaria real

- TenantSettings singleton por esquema (sin Cloudinary aún, storage local)
- provision_tenant() crea la configuración por defecto de cada laboratorio
- TenantTimezoneMiddleware movido a settings_lab, usa la zona horaria real del tenant
- base_tenant.html con variables CSS de branding
```
