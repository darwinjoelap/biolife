# Tasks — Biolife

## Active

- [ ] **Fase 05** - siguiente fase del roadmap (`docs/roadmap/`), aún no iniciada — leer su roadmap al empezar, no antes

## Waiting On

- [ ] **Commit de Fase 04 en git** - mensaje sugerido en `docs/roadmap/04_pacientes_y_representantes.md` §8
- [ ] **Confirmar rangos de referencia contradictorios** - para el laboratorio Angelus (bloquea Fase 06): glicemia, urea, creatinina, ácido úrico, bilirrubinas, TGO/TGP
- [ ] **Confirmar "ÁCIDO ÚRICO: 3,4 - 70 mg/dL"** - para el laboratorio Angelus, ¿es error de tipeo por 7,0?
- [ ] **Confirmar rangos pediátricos/neonatales reales** - para el laboratorio Angelus
- [ ] **Confirmar rangos diferenciados por sexo** - para el laboratorio Angelus (los formatos actuales usan el mismo para ambos)
- [ ] **Confirmar valores críticos/de pánico** - para el laboratorio Angelus
- [ ] **Confirmar valor de ISI del lote de tromboplastina** - para el laboratorio Angelus (necesario para el INR)
- [ ] **Confirmar si es doble validación (técnico + bioanalista) o única** - para el laboratorio Angelus
- [ ] **Confirmar marca y modelo de los analizadores** - para el laboratorio Angelus
- [ ] **Confirmar precios de exámenes y perfiles** - para el laboratorio Angelus
- [ ] **Confirmar estado/municipio de localidades sin certeza** - Cantagallo, Dos Caminos, Las Minas, Píritu (`apps/masterdata/fixtures/localidades.json`)
- [ ] **Decidir si se conserva o se borra el tenant `demo_tres`** - quedó creado al verificar `provision_tenant()` con el admin inicial
- [ ] **Borrar carpeta suelta `Claude outputs/`** - scratch file de una sesión anterior, no está trackeado por git, seguro de borrar manualmente

## Someday

- [ ] **Automatizar creación del tenant `public` + dominio** - como parte del script de despliegue (Fase 17), ver ADR-009

## Done

- [x] ~~Fase 00 — Diseño (arquitectura, modelo de datos, convenciones, roadmap de 18 fases)~~ (2026-09-19)
- [x] ~~Fase 01 — Setup y multi-tenancy~~ (2026-09-19) — Django+django-tenants, apps core/tenants/masterdata, provision_tenant(), tenant público, aislamiento verificado, 9/9 tests, ruff limpio
- [x] ~~Fase 02 — Usuarios, roles y auditoría~~ (2026-09-20) — User propio (accounts.User), Role/Membership (6 roles), AuditLog append-only, login por tenant, provision_tenant() crea admin inicial, 18/18 tests, ruff limpio
- [x] ~~Fase 03 — Configuración del laboratorio~~ (2026-09-26) — TenantSettings singleton por tenant, provision_tenant() crea la config por defecto, middleware de zona horaria movido a settings_lab (con guarda para public), base_tenant.html + branding, MEDIA_ROOT/URL local (Cloudinary diferido a Fase 17), admin singleton, 24/24 tests, ruff limpio
- [x] ~~Commit de Fases 02+03 en git~~ (2026-09-26) — commit combinado `6d001d6` (47 archivos), ver mensaje del commit para el detalle de cada fase
- [x] ~~Fase 04 — Pacientes y representantes~~ (2026-09-26) — Patient/Guardian/PatientGuardian + PatientCodeSequence, internal_code con correlativo anual (select_for_update), lab_initials en TenantSettings, services create_patient()/guardian_linking, selector de búsqueda, admin con inline, migraciones en los 3 tenants, 33/33 tests, ruff limpio
