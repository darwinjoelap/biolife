# ESTADO DEL PROYECTO — Biolife

> Se actualiza al **cerrar cada sesión**. Es el primer archivo que se lee al abrir la siguiente.
> Mantener bajo 100 líneas: si crece, es que hay historial que pertenece a DECISIONES.md.

**Última actualización:** 2026-09-26
**Fase actual:** 08b — Ficha del examen (rangos) (**completa y verificada**) → siguiente: 09 (órdenes y muestras)
**Responsable:** Darwin

---

## Completado

- [x] Fase 00 (diseño): arquitectura, modelo de datos, convenciones, roadmap de 18 fases
- [x] Fase 01 (setup y multi-tenancy): ver detalle en el historial de este archivo / ADRs
- [x] Fases 02–03 (commit `6d001d6`): `User` propio, roles, `AuditLog`, login por tenant
  (ADR-010/011); `TenantSettings`, middleware de zona horaria, branding (ADR-012/013).
- [x] Fase 04 (commit `03a4f10`): pacientes, representantes, `internal_code` (ADR-014).
- [x] Fase 05 (commit `c9ac6ab`): `apps.catalog`, `seed_uroanalisis()` con los 9
  `value_type`, parámetros no confirmados marcados (ADR-015).
- [x] Fase 06 (sin commit aún): `ReferenceRange` + `resolve_reference_range()` (ADR-016).
- [x] Fase 07: motor de fórmulas (AST restringido, `Decimal`, ciclos al guardar), sintaxis
  `{CODIGO}`/`{@var}`, verificada en la máquina de Darwin (107/107) (ADR-017).
- [x] Fase 08: exámenes individuales desde los Excel, 15 perfiles, `apps.billing` multimoneda
  con descuentos y `quote()` (ADR-019). Verificada en la máquina de Darwin (149/149).
- [x] Fase 08b (`docs/roadmap/08b_ficha_del_examen_rangos.md`): ficha del examen en el admin
  (rangos por sexo/edad en años-meses-días/condición, avisos de solapes y huecos, probador),
  bug de bitácora del admin por tenant corregido (ADR-020). Verificada en la máquina de Darwin
  (171/171, ruff limpio, `accounts.0004` aplicada en los 3 tenants).

## En curso

Nada. Fase 08b cerrada y verificada.

## Pendiente inmediato

1. Ubicar en el roadmap la fase de **estilo visual y pantallas base** (antes de la primera
   pantalla real); ahí se hace la ficha del examen definitiva.
2. Cargar precios reales en la lista GENERAL (admin) cuando se tengan.
3. Commit de la Fase 06 y luego de la Fase 07 (mensajes en sus archivos de roadmap).
3. **No usar en un informe real** ningún `ReferenceRange`/parámetro marcado "PENDIENTE DE
   CONFIRMAR" o "NO CONFIRMADO" (ver ADR-015 y ADR-016), ni la superficie corporal/INR
   sin confirmar Mosteller e ISI (ADR-017), hasta que Angelus responda.
4. Confirmar con Angelus los rangos de referencia contradictorios, los rangos
   pediátricos/neonatales reales, y el detalle geográfico de localidades sin municipio
   verificado (Cantagallo, Dos Caminos, Las Minas, Píritu).
5. Decidir el destino de `demo_tres` y borrar manualmente `Claude outputs/`.

## Bloqueos

Ninguno técnico. Las preguntas abiertas al laboratorio (abajo) siguen sin responder, pero
ya no bloquean avanzar de fase — el motor y la siembra de ejemplo quedaron construidos con
valores marcados como pendientes en vez de esperar la confirmación.

## Preguntas abiertas al laboratorio

> Angelus es laboratorio de **referencia**, no el alcance del producto (ADR-018). Estas
> respuestas alimentan sus datos de tenant; no bloquean decisiones de producto.

- [ ] Rangos de referencia correctos donde los formatos se contradicen:
      glicemia, urea, creatinina, ácido úrico, bilirrubinas, TGO/TGP
- [ ] "ÁCIDO ÚRICO: 3,4 - 70 mg/dL" — ¿es error de tipeo por 7,0?
- [ ] Rangos pediátricos y neonatales reales
- [ ] Rangos diferenciados por sexo (los formatos usan el mismo para ambos)
- [ ] Valores críticos / de pánico (umbrales por parámetro; se configuran en la ficha del
      examen y se usan en la Fase 10 — ver TASKS.md)
- [ ] Valor de ISI del lote de tromboplastina (necesario para el INR)
- [ ] INR: su hoja calcula con ISI vacío e imprime siempre 1 (ADR-019)
- [ ] LDH: 90–510 IU/L en unas hojas, por sexo (H 80–285 / M 103–227) en otras
- [ ] Insulina: unidad "U/mL" (¿µU/mL?) y rango post-carga "40 – 230"
- [ ] ¿La composición de perfiles sembrada coincide con lo que venden? (ADR-019)
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
- ADR-015 (Fase 05): catálogo sembrado directo por tenant (Master*+copia pospuesto) y por
  qué el uroanálisis sembrado trae parámetros no confirmados por el laboratorio.
- ADR-016 (Fase 06): 4 exámenes mínimos nuevos para cubrir los 6 `range_type`, y por qué
  6 parámetros se sembraron con un valor marcado pendiente de confirmar.
- ADR-018: Angelus es referencia, no techo de alcance; libertad creativa y lo variable
  entre laboratorios va como configuración por tenant.
- ADR-020 (Fase 08b): edad años/meses/días con «hasta» exclusivo, ERROR/AVISO de cobertura,
  admin también por tenant.
- ADR-019 (Fase 08): perfiles = agrupación de exámenes individuales; `apps.billing`
  multimoneda; reglas de cotización; Mosteller confirmado por la celda de la hoja.
- ADR-017 (Fase 07): sintaxis de fórmulas, AST restringido, ISI como `{@isi}`, precisión
  completa en intermedios, y por qué la superficie corporal es Mosteller y no DuBois.
- "7 roles" del índice del roadmap = 6 roles de tenant (esta fase) + `SUPERADMIN_PLATAFORMA`
  como `PlatformUser` en `public` (Fase 12), no un séptimo `Role` de tenant.
- **Postgres local (máquina de Darwin):** hay 3 instalaciones (16, 17, 18). La base
  `biolife` del proyecto vive en la instancia **16**, que corre en el puerto **5434**
  (se cambió de 5432 porque la instancia 18 ya lo ocupaba con otro proyecto). Si
  `manage.py` da error de autenticación o "no existe la base de datos", verificar primero
  que el servicio `postgresql-x64-16` esté corriendo y que `.env` apunte a
  `localhost:5434`.
