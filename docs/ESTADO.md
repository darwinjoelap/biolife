# ESTADO DEL PROYECTO — Biolife

> Se actualiza al **cerrar cada sesión**. Es el primer archivo que se lee al abrir la siguiente.
> Mantener bajo 100 líneas: si crece, es que hay historial que pertenece a DECISIONES.md.

**Última actualización:** 2026-09-26
**Fase actual:** 04 — Pacientes y representantes (**completa**) → siguiente: 05 (catálogo)
**Responsable:** Darwin

---

## Completado

- [x] Fase 00 (diseño): arquitectura, modelo de datos, convenciones, roadmap de 18 fases
- [x] Fase 01 (setup y multi-tenancy): ver detalle en el historial de este archivo / ADRs
- [x] Fase 02 (usuarios, roles y auditoría): `User` propio (ADR-010), `apps.accounts`
  SHARED_APP+TENANT_APP (ADR-011), 6 roles de tenant, `AuditLog` append-only, login por
  tenant, `provision_tenant()` crea el admin inicial.
- [x] Fase 03 (`docs/roadmap/03_configuracion_laboratorio.md`) completa: `TenantSettings`
  singleton por tenant, `provision_tenant()` lo crea por defecto, `TenantTimezoneMiddleware`
  movido a `apps.settings_lab` con guarda de esquema `public` (ADR-012), branding con
  `base_tenant.html`, storage local para logo/banner (Cloudinary diferido, ADR-013),
  `/admin/` registrado en `urls_tenant.py`.
- [x] Fase 02 + Fase 03 commiteadas en git en un solo commit combinado (`6d001d6`).
- [x] Fase 04 (`docs/roadmap/04_pacientes_y_representantes.md`) completa, sin UI (queda
  para Fase 09): `apps.patients` con `Patient`/`Guardian`/`PatientGuardian`
  (`TenantBaseModel`) + `PatientCodeSequence` (auxiliar plano); `internal_code` formato
  `{YY}{iniciales}{correlativo:06d}` (ej. `26LDU000001`), reinicia cada año,
  `select_for_update()` evita colisiones (ADR-014); `TenantSettings.lab_initials`;
  `services/patient_creation.py::create_patient()` — único punto que exige representante
  para menores sin documento propio (el admin **no** re-valida esta regla);
  `services/guardian_linking.py`; `selectors/patient_search.py`; admin con inline de
  representantes; migraciones aplicadas en los 3 tenants demo. `pytest -q`: 33/33 en
  verde · `ruff check .`: sin errores.

## En curso

Nada. Fase 04 cerrada.

## Pendiente inmediato

1. Empezar Fase 05 (catálogo) — leer su roadmap cuando se inicie, no antes.
2. Commit de la Fase 04 en git (mensaje sugerido en
   `docs/roadmap/04_pacientes_y_representantes.md` §8).
3. Confirmar con el laboratorio Angelus los rangos de referencia contradictorios (bloquea
   Fase 06) y el detalle geográfico del fixture de localidades (Cantagallo, Dos Caminos,
   Las Minas, Píritu sin municipio verificado).
4. `demo_tres` quedó creado como parte de la verificación de la Fase 02 — decidir si se
   conserva como tercer tenant demo o se borra.
5. Darwin debe borrar manualmente la carpeta suelta `Claude outputs/` en la raíz del
   proyecto (contenido superado, no se subió a git).

## Bloqueos

Ninguno técnico.

## Preguntas abiertas al laboratorio (bloquean la Fase 06)

- [ ] Rangos de referencia correctos donde los formatos se contradicen:
      glicemia, urea, creatinina, ácido úrico, bilirrubinas, TGO/TGP
- [ ] "ÁCIDO ÚRICO: 3,4 - 70 mg/dL" — ¿es error de tipeo por 7,0?
- [ ] Rangos pediátricos y neonatales reales
- [ ] Rangos diferenciados por sexo (los formatos usan el mismo para ambos)
- [ ] Valores críticos / de pánico
- [ ] Valor de ISI del lote de tromboplastina (necesario para el INR)
- [ ] ¿Doble validación (técnico + bioanalista) o validación única?
- [ ] Marca y modelo de los analizadores del laboratorio
- [ ] Precios de exámenes y perfiles

## Advertencia sobre el fixture de localidades

`apps/masterdata/fixtures/localidades.json` tiene los 21 nombres exactos de
`04_HALLAZGOS_FORMATOS.md`, pero el estado/municipio de cada uno se completó por
conocimiento general de geografía venezolana, no por dato del laboratorio. Cantagallo, Dos
Caminos, Las Minas y Píritu quedaron sin municipio por falta de certeza. Confirmar con el
laboratorio antes de producción.

## Notas

- Los formatos originales están en el proyecto de Cowork. No re-analizarlos:
  el resumen completo está en `docs/04_HALLAZGOS_FORMATOS.md`.
- ADR-007, ADR-008 y ADR-009 (Fase 01) documentan trampas reales de `django-tenants` al
  crear/borrar esquemas — leerlas antes de tocar `provisioning.py` o tests con schema_context.
- ADR-010 y ADR-011 (Fase 02) documentan por qué `User` es propio y por qué `apps.accounts`
  es SHARED_APP + TENANT_APP a la vez — leerlas antes de tocar `AUTH_USER_MODEL` o
  `INSTALLED_APPS`.
- ADR-012 y ADR-013 (Fase 03): mudanza del middleware de zona horaria (con la guarda de
  esquema `public`) y diferir Cloudinary a la Fase 17.
- ADR-014 (Fase 04): formato de `internal_code`, contador con `select_for_update()` y por
  qué `lab_initials` vive en `TenantSettings` y no en `Tenant`.
- "7 roles" del índice del roadmap = 6 roles de tenant (esta fase) + `SUPERADMIN_PLATAFORMA`
  como `PlatformUser` en `public` (Fase 12), no un séptimo `Role` de tenant.
- **Postgres local (máquina de Darwin):** hay 3 instalaciones (16, 17, 18). La base
  `biolife` del proyecto vive en la instancia **16**, que corre en el puerto **5434**
  (se cambió de 5432 porque la instancia 18 ya lo ocupaba con otro proyecto). Si
  `manage.py` da error de autenticación o "no existe la base de datos", verificar primero
  que el servicio `postgresql-x64-16` esté corriendo y que `.env` apunte a
  `localhost:5434`.
