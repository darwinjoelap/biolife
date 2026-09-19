# ESTADO DEL PROYECTO — Biolife

> Se actualiza al **cerrar cada sesión**. Es el primer archivo que se lee al abrir la siguiente.
> Mantener bajo 100 líneas: si crece, es que hay historial que pertenece a DECISIONES.md.

**Última actualización:** 2026-09-19
**Fase actual:** 01 — Setup y multi-tenancy (**completa**) → siguiente: 02 Usuarios, roles y auditoría
**Responsable:** Darwin

---

## Completado

- [x] Fase 00 (diseño): arquitectura, modelo de datos, convenciones, roadmap de 18 fases
- [x] Fase 01 completa y verificada de punta a punta:
  - Proyecto Django (`config/`) con settings divididos (base/local/staging/production)
  - Multi-tenancy por esquemas vía `django-tenants`, Python 3.13 (ADR-006)
  - Apps `core`, `tenants`, `masterdata` con modelos, admin y migraciones
  - Catálogo de 21 localidades cargado (`docs/roadmap/`, ver advertencia abajo)
  - Service `provision_tenant()` + comando `crear_laboratorio`, seguro ante el esquema
    activo del llamador (ADR-007)
  - Tenant público (`public` + dominio `localhost`) registrado (ADR-009)
  - Health check de pooler (`biolife.W001`) y `scripts/check_tenant_isolation.py` —
    **AISLAMIENTO VERIFICADO**
  - `python manage.py runserver` responde correctamente en `localhost` (admin),
    `demo1.localhost` y `demo2.localhost` (tenants)
  - Suite de tests: 9/9 en verde (`pytest -q`), `ruff check .` sin errores
  - Dos tenants demo creados y verificados: `demo_uno`, `demo_dos`

## En curso

Nada. Fase 01 cerrada.

## Pendiente inmediato

1. Confirmar con el laboratorio Angelus los rangos de referencia contradictorios (bloquea
   Fase 06) y el detalle geográfico del fixture de localidades (ver advertencia abajo).
2. Commit final de la Fase 01 en git (`feat(setup): proyecto Django con multi-tenancy por esquemas`).
3. Borrar los duplicados sueltos `docs/00_INDICE.md` y `docs/01_setup_y_tenants.md`
   (el contenido vigente está en `docs/roadmap/`) — pendiente desde el cierre de Fase 00.
4. Empezar Fase 02: usuarios, roles (7 tipos) y auditoría.

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
- ADR-007, ADR-008 y ADR-009 (nuevos en esta sesión) documentan trampas reales de
  `django-tenants` encontradas al ejecutar la Fase 01 — leerlas antes de tocar
  `apps/tenants/services/provisioning.py` o escribir tests que creen/borren esquemas.
