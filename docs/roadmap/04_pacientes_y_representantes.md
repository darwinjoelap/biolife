# FASE 04 — Pacientes y Representantes

> **Modelo sugerido:** Sonnet
> **Duración estimada:** 1 sesión
> **Depende de:** Fase 02
> **Bloquea a:** Fase 09 (órdenes necesita seleccionar/crear pacientes)

---

## 1. Objetivo

Al terminar esta fase, cada tenant puede registrar pacientes (con o sin cédula) y,
cuando el paciente es menor de edad y no tiene documento propio, el sistema exige un
representante legal antes de aceptar el registro. Cada paciente queda identificado por
un `internal_code` único generado por el sistema, independiente de si tiene cédula.

---

## 2. Contexto mínimo necesario

Decisiones tomadas en esta sesión (con Darwin, antes de empezar):

- **Alcance de esta fase:** sólo modelos + services + selectors + tests. Los
  formularios/vistas HTMX de `apps/patients/` (listados en `docs/02_ESTRUCTURA_PROYECTO.md`)
  quedan para cuando la fase de UI correspondiente los necesite (Fase 09 es la primera
  consumidora real de la búsqueda de pacientes). Mientras tanto se opera vía Django admin,
  igual que `TenantSettings` en la Fase 03.
- **Formato de `internal_code`:** `{terminal del año}{iniciales del lab}{correlativo de 6
  dígitos}`, ej. `26LDU000001` para un laboratorio de iniciales "LDU" en 2026, primer
  paciente del año. El correlativo **reinicia en `000001` cada año** — el año va embebido
  en el propio código, así que un reinicio anual no genera colisiones.
- **Iniciales del laboratorio:** no existe hoy un campo para esto. Se agrega
  `TenantSettings.lab_initials` (Fase 03, `apps.settings_lab`) en vez de tocar el modelo
  `Tenant` (esquema `public`) — mantiene la generación del código dentro del mismo
  `schema_context()` del tenant, sin cruzar a `public`.
- **Roles que podrán crear/editar pacientes** (para cuando exista la UI, Fase 09 u otra):
  `RECEPCION`, `ADMIN_LAB`, `BIOANALISTA`, `TECNICO`. Documentado aquí para no
  re-decidirlo después; no se aplica todavía porque no hay vistas.

Decisiones ya tomadas en fases previas, **no renegociar**:
- Todos los modelos de tenant heredan `TenantBaseModel` (`docs/01_MODELO_DATOS.md`, línea 4-5)
  — UUID como PK, `created_at`/`updated_at`/`created_by`/`is_active`. Excepción documentada:
  el contador `PatientCodeSequence` (Tarea 1) es un modelo de soporte interno, no una
  entidad de dominio, y sigue el mismo patrón que `Role`/`Membership`/`AuditLog` en
  `apps.accounts` (PK entera simple, sin `TenantBaseModel`).
- `document_number` es **nullable de verdad** (no `blank=True, default=""`) — excepción
  explícita a la regla 8 de `docs/03_CONVENCIONES.md` ("nada de `null=True` en CharField"),
  necesaria para que el índice único parcial `WHERE document_number IS NOT NULL` tenga
  sentido: si fuera `""` para todos los pacientes sin documento, colisionarían entre sí.
- Servicios con excepciones de dominio (`ApplicationError`), nunca `ValueError` genérico
  (`docs/03_CONVENCIONES.md`, regla 6).

Documentos a leer antes de empezar:
- `docs/01_MODELO_DATOS.md` — sección C, bloques `Patient`, `Guardian`, `PatientGuardian`
- `docs/02_ESTRUCTURA_PROYECTO.md` — árbol de `apps/patients/`
- `docs/03_CONVENCIONES.md` — reglas de servicios, excepciones, tests
- `docs/DECISIONES.md` — ADR-001 (esquemas), ADR-007/008/009 (trampas de django-tenants)

---

## 3. Alcance

### Incluye
- [ ] App `apps.patients` (TENANT_APP) con modelos `Patient`, `Guardian`, `PatientGuardian`
- [ ] `PatientCodeSequence` — contador por año para generar `internal_code`
- [ ] `TenantSettings.lab_initials` (nuevo campo, migración en `apps.settings_lab`)
- [ ] `services/patient_creation.py` — `generate_internal_code()`, `create_patient()`
      (exige representante si el paciente es menor sin `document_number`)
- [ ] `services/guardian_linking.py` — `create_guardian()`, `link_guardian()` (agregar o
      cambiar representante de un paciente ya existente)
- [ ] `selectors/patient_search.py` — `search_patients(*, query)` por código interno,
      documento o nombre
- [ ] Admin de `Patient`/`Guardian`/`PatientGuardian` (operación manual mientras no hay UI)
- [ ] Tests: generación de código, reinicio anual del correlativo, regla del representante,
      unicidad de documento

### NO incluye (explícito)
- ❌ Formularios/vistas HTMX de `apps/patients/` → se construyen cuando los necesite la
  fase que consuma la búsqueda de pacientes (Fase 09 como mínimo)
- ❌ `services/merge.py` (fusión de pacientes duplicados) → no es parte de la ruta crítica
  al MVP; se planifica como fase de operación posterior, no numerada aún
- ❌ Cálculo preciso de edad en días para rangos de referencia → Fase 06. Aquí `is_minor`
  es sólo un booleano (¿es menor de 18 años, sí o no?) para la regla del representante,
  no un cálculo clínico exacto
- ❌ Aplicar `RoleRequiredMixin` con los roles decididos arriba → no hay vistas todavía;
  la decisión queda documentada para cuando existan

---

## 4. Pre-requisitos verificables

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"
python manage.py check
# Esperado: 0 errores (estado de cierre de Fase 03)
pytest -q
# Esperado: 24 passed
```

---

## 5. Tareas

### Tarea 1 — App `apps.patients` y modelos

**Archivos:** `apps/patients/__init__.py`, `apps/patients/apps.py`, `apps/patients/models.py`
(crear); `config/settings/base.py` (`TENANT_APPS`, ampliar)

Modelos (`Patient`, `Guardian`, `PatientGuardian` heredan `TenantBaseModel`;
`PatientCodeSequence` es un modelo de soporte, PK entera simple):

```python
class Patient(TenantBaseModel):
    class DocumentType(models.TextChoices):
        V = "V", "Cédula V"
        E = "E", "Cédula E"
        J = "J", "RIF Jurídico"
        P = "P", "Pasaporte"
        SIN_DOCUMENTO = "SIN_DOCUMENTO", "Sin documento"

    class Sex(models.TextChoices):
        M = "M", "Masculino"
        F = "F", "Femenino"

    class AgeUnit(models.TextChoices):
        DIAS = "DIAS", "Días"
        MESES = "MESES", "Meses"
        ANOS = "ANOS", "Años"

    internal_code = models.CharField(
        "Código interno", max_length=20, unique=True, editable=False
    )
    document_type = models.CharField(max_length=15, choices=DocumentType.choices)
    document_number = models.CharField(
        "Número de documento", max_length=20, null=True, blank=True
    )
    first_name = models.CharField("Nombres", max_length=100)
    last_name = models.CharField("Apellidos", max_length=100)
    sex = models.CharField(max_length=1, choices=Sex.choices)
    birth_date = models.DateField("Fecha de nacimiento", null=True, blank=True)
    declared_age_value = models.PositiveIntegerField(
        "Edad declarada", null=True, blank=True
    )
    declared_age_unit = models.CharField(
        max_length=5, choices=AgeUnit.choices, blank=True, default=""
    )
    declared_age_at = models.DateField(
        "Fecha en que se declaró la edad", null=True, blank=True
    )
    locality = models.ForeignKey(
        "masterdata.Locality", on_delete=models.PROTECT, null=True, blank=True
    )
    address = models.CharField("Dirección", max_length=255, blank=True, default="")
    phone = models.CharField("Teléfono", max_length=30, blank=True, default="")
    email = models.EmailField("Correo", blank=True, default="")

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        constraints = [
            models.UniqueConstraint(
                fields=["document_type", "document_number"],
                condition=models.Q(document_number__isnull=False),
                name="uniq_patient_document",
            ),
            models.CheckConstraint(
                check=models.Q(birth_date__isnull=False)
                | models.Q(declared_age_value__isnull=False),
                name="patient_has_birth_date_or_declared_age",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.internal_code})"

    def age_in_years(self, *, as_of: "date | None" = None) -> int:
        """Edad aproximada en años completos — sólo para la regla de mayoría de edad,
        no para resolución de rangos de referencia (eso es Fase 06, con días exactos)."""
        as_of = as_of or timezone.localdate()
        if self.birth_date is not None:
            years = as_of.year - self.birth_date.year
            if (as_of.month, as_of.day) < (self.birth_date.month, self.birth_date.day):
                years -= 1
            return years
        base = self.declared_age_at or as_of
        elapsed_years = (as_of - base).days / 365.25
        if self.declared_age_unit == self.AgeUnit.ANOS:
            return int(self.declared_age_value + elapsed_years)
        if self.declared_age_unit == self.AgeUnit.MESES:
            return int((self.declared_age_value / 12) + elapsed_years)
        return int((self.declared_age_value / 365.25) + elapsed_years)

    @property
    def is_minor(self) -> bool:
        return self.age_in_years() < 18


class Guardian(TenantBaseModel):
    document_type = models.CharField(max_length=1, choices=Patient.DocumentType.choices[:4])
    document_number = models.CharField("Número de documento", max_length=20)
    first_name = models.CharField("Nombres", max_length=100)
    last_name = models.CharField("Apellidos", max_length=100)
    phone = models.CharField("Teléfono", max_length=30, blank=True, default="")
    address = models.CharField("Dirección", max_length=255, blank=True, default="")
    email = models.EmailField("Correo", blank=True, default="")

    class Meta:
        verbose_name = "Representante"
        verbose_name_plural = "Representantes"
        unique_together = [("document_type", "document_number")]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class PatientGuardian(TenantBaseModel):
    class Relationship(models.TextChoices):
        MADRE = "MADRE", "Madre"
        PADRE = "PADRE", "Padre"
        ABUELO = "ABUELO", "Abuelo/a"
        TIO = "TIO", "Tío/a"
        HERMANO = "HERMANO", "Hermano/a"
        TUTOR_LEGAL = "TUTOR_LEGAL", "Tutor legal"
        OTRO = "OTRO", "Otro"

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="guardians")
    guardian = models.ForeignKey(Guardian, on_delete=models.PROTECT, related_name="patients")
    relationship = models.CharField(max_length=15, choices=Relationship.choices)
    relationship_detail = models.CharField(max_length=100, blank=True, default="")
    is_primary = models.BooleanField("Representante principal", default=True)
    legal_doc_ref = models.CharField(
        "Referencia de documento legal", max_length=100, blank=True, default=""
    )

    class Meta:
        verbose_name = "Representante de paciente"
        verbose_name_plural = "Representantes de pacientes"
        unique_together = [("patient", "guardian")]


class PatientCodeSequence(models.Model):
    """Contador de internal_code por año. No es TenantBaseModel: es plumbing interno,
    mismo criterio que Role/Membership/AuditLog en apps.accounts."""

    year = models.PositiveIntegerField(unique=True)
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Secuencia de código de paciente"
        verbose_name_plural = "Secuencias de código de paciente"
```

> **Validación pendiente de revisar en la Tarea 3, no en el modelo:** que
> `document_number` sea obligatorio cuando `document_type != SIN_DOCUMENTO` y `None`
> cuando sí lo es. Va en el service porque es una regla de coherencia entre dos campos,
> no una constraint de un solo campo.

**Criterio de aceptación:**
```powershell
python manage.py makemigrations patients
```

---

### Tarea 2 — `TenantSettings.lab_initials`

**Archivos:** `apps/settings_lab/models.py` (ampliar)

```python
lab_initials = models.CharField(
    "Siglas del laboratorio", max_length=6, blank=True, default=""
)
```

**Criterio de aceptación:**
```powershell
python manage.py makemigrations settings_lab
```

---

### Tarea 3 — `services/patient_creation.py`

**Archivos:** `apps/patients/services/__init__.py`, `apps/patients/services/patient_creation.py`

Responsable de: generar `internal_code` (con `select_for_update()` sobre
`PatientCodeSequence` para evitar condiciones de carrera), validar coherencia
`document_type`/`document_number`, y exigir representante si el paciente es menor sin
documento propio — todo dentro de un único `transaction.atomic()`.

```python
def generate_internal_code() -> str:
    ...  # select_for_update sobre PatientCodeSequence del año actual

def create_patient(
    *,
    first_name: str,
    last_name: str,
    sex: str,
    document_type: str,
    document_number: str | None = None,
    birth_date: "date | None" = None,
    declared_age_value: int | None = None,
    declared_age_unit: str = "",
    declared_age_at: "date | None" = None,
    locality: "Locality | None" = None,
    address: str = "",
    phone: str = "",
    email: str = "",
    created_by: "User | None" = None,
    guardian: "Guardian | None" = None,
    guardian_relationship: str = "",
    guardian_relationship_detail: str = "",
) -> Patient:
    ...
```

Reglas a implementar (con `ApplicationError`, mensaje apto para usuario final):
- `document_type == SIN_DOCUMENTO` ⇒ `document_number` debe ser `None`.
- `document_type != SIN_DOCUMENTO` ⇒ `document_number` es obligatorio.
- Paciente menor de 18 años **y** sin `document_number` ⇒ debe venir `guardian` +
  `guardian_relationship` en la misma llamada; si no, `ApplicationError` antes de
  escribir nada (todo dentro del `transaction.atomic()`).
- Si `guardian_relationship == OTRO`, `guardian_relationship_detail` es obligatorio.
- `TenantSettings.lab_initials` vacío ⇒ `ApplicationError` explicando que hay que
  configurarlo primero (Fase 03, admin de `TenantSettings`).

**Criterio de aceptación:** cubierto por los tests de la Tarea 6.

---

### Tarea 4 — `services/guardian_linking.py`

**Archivos:** `apps/patients/services/guardian_linking.py`

```python
def create_guardian(*, document_type, document_number, first_name, last_name, phone="", address="", email="") -> Guardian: ...

def link_guardian(
    *, patient: Patient, guardian: Guardian, relationship: str,
    relationship_detail: str = "", is_primary: bool = True, legal_doc_ref: str = "",
) -> PatientGuardian: ...
```

Para agregar o cambiar el representante de un paciente que ya existe (no sólo al
crearlo). Si `is_primary=True`, desmarca cualquier otro `PatientGuardian` principal del
mismo paciente dentro de la misma transacción.

**Criterio de aceptación:** cubierto por los tests de la Tarea 6.

---

### Tarea 5 — `selectors/patient_search.py` y admin

**Archivos:** `apps/patients/selectors/__init__.py`, `apps/patients/selectors/patient_search.py`,
`apps/patients/admin.py` (crear)

```python
def search_patients(*, query: str) -> "QuerySet[Patient]":
    """Busca por código interno, número de documento, nombre o apellido (icontains)."""
```

Admin: `PatientAdmin` con `list_display` (código, nombre, documento, edad/is_minor) y
`search_fields`; `GuardianAdmin`; `PatientGuardianAdmin` como inline dentro de `PatientAdmin`
(similar al patrón `MembershipInline` de `apps.accounts`, Fase 02).

**Criterio de aceptación:** `python manage.py check` sin errores; verificar en
`/admin/patients/` que se puede crear un paciente adulto directamente.

> **Decisión tomada durante la implementación (revierte lo planteado más arriba):** el
> admin **no** re-implementa la regla "menor sin documento exige representante". Duplicar
> esa validación transaccional en `ModelAdmin.save_related()` para un admin que sólo es
> un puente temporal mientras no hay UI propia no vale la complejidad ni el riesgo de que
> las dos copias de la regla diverjan. La única vía que garantiza la regla es
> `services/patient_creation.py::create_patient()` (cubierta por tests, Tarea 6). Un
> operador usando el admin directamente puede, técnicamente, guardar un paciente menor
> sin representante — es un límite de confianza aceptado del admin, igual que el resto
> de Django admin confía en quien lo usa. Documentado también en `docs/ESTADO.md`.

---

### Tarea 6 — Tests

**Archivos:** `apps/patients/tests/test_patient_creation.py`,
`apps/patients/tests/test_guardian_linking.py`, `apps/patients/tests/test_code_sequence.py`

Casos obligatorios:
1. `create_patient()` con documento propio (adulto) — no requiere representante.
2. `create_patient()` con menor de edad y `document_number=None` sin representante ⇒
   `ApplicationError`.
3. `create_patient()` con menor de edad y `document_number=None` **con** representante ⇒
   crea `Patient` + `Guardian` + `PatientGuardian(is_primary=True)`.
4. `create_patient()` con menor de edad **y** documento propio ⇒ no requiere representante
   (la regla es "sin cédula", no "por ser menor").
5. `document_type=SIN_DOCUMENTO` con `document_number` no nulo ⇒ `ApplicationError`.
6. Dos pacientes con el mismo `document_type`+`document_number` ⇒ `IntegrityError`/
   `ApplicationError` (unicidad).
7. `generate_internal_code()` dos veces en el mismo año da correlativos consecutivos
   (`000001`, `000002`).
8. `generate_internal_code()` simulando año distinto reinicia el correlativo en `000001`.
9. `link_guardian()` con `is_primary=True` desmarca el representante principal anterior.

**Criterio de aceptación:**
```powershell
pytest -q
ruff check .
```

---

### Tarea 7 — Cierre documental

**Archivos:** `docs/ESTADO.md`, `docs/DECISIONES.md` (actualizar)

- `ESTADO.md`: Fase 04 completa, qué existe, qué sigue (Fase 05: catálogo).
- `DECISIONES.md`: ADR-014 (formato de `internal_code`, contador con
  `select_for_update()` en vez de derivarlo del máximo existente, y por qué vive en
  `apps.settings_lab.TenantSettings` y no en `apps.tenants.Tenant`).

---

## 6. Criterios de salida (Definition of Done)

- [ ] `apps.patients` con `Patient`, `Guardian`, `PatientGuardian`, `PatientCodeSequence`
- [ ] `TenantSettings.lab_initials` disponible y usado por `generate_internal_code()`
- [ ] Un paciente menor sin documento no puede crearse **vía `create_patient()`** sin
      representante — verificado con test real, no sólo revisado a ojo. No aplica al
      admin de Django (ver nota de la Tarea 5)
- [ ] Un paciente adulto, o un menor con documento propio, se crea sin representante
- [ ] `internal_code` único, formato `{YY}{iniciales}{000001}`, correlativo reinicia por año
- [ ] Admin operativo para registrar pacientes/representantes mientras no hay UI propia
- [ ] `pytest -q` en verde, incluidos los 9 casos de la Tarea 6
- [ ] `ruff check .` sin errores
- [ ] `docs/ESTADO.md` y `docs/DECISIONES.md` actualizados

---

## 7. Riesgos y trampas conocidas

| Riesgo | Señal | Mitigación |
|---|---|---|
| Condición de carrera generando `internal_code` con dos registros simultáneos | Dos pacientes con el mismo código | `select_for_update()` sobre `PatientCodeSequence`, todo en `transaction.atomic()` |
| `document_number=""` en vez de `None` para "sin documento" | El índice único parcial no filtra estos registros y choca entre sí | Servicio siempre normaliza a `None`, nunca a cadena vacía |
| Validar la regla del representante en `Patient.clean()` | No puede: la relación `PatientGuardian` no existe aún en ese punto | La regla vive en `services/patient_creation.py`, no en el modelo (ya anotado en `01_MODELO_DATOS.md`) |
| Olvidar que `is_minor` es aproximado (365.25 días/año) | Reportado como error en Fase 06 al comparar con rangos por edad en días exactos | Documentado explícitamente: aquí es sólo un booleano para la regla del representante |
| `TenantSettings.lab_initials` vacío al crear el primer paciente | `create_patient()` falla con `ApplicationError` poco claro | Mensaje de error explícito indicando configurarlo en el admin de `TenantSettings` primero |

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
feat(patients): pacientes con representante legal obligatorio para menores sin cedula

- Patient/Guardian/PatientGuardian (TenantBaseModel) + PatientCodeSequence
- internal_code generado por servicio: {YY}{iniciales del lab}{correlativo 6 digitos}
- TenantSettings.lab_initials nuevo campo
- create_patient() exige representante si es menor sin document_number
- guardian_linking: agregar/cambiar representante de un paciente existente
- selectors/patient_search + admin operativo (sin UI propia todavia)
```
