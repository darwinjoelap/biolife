# ESTADO DEL PROYECTO — Biolife

> Se actualiza al **cerrar cada sesión**. Es el primer archivo que se lee al abrir la siguiente.
> Mantener bajo 100 líneas: el detalle de fases cerradas va a `HISTORIAL.md`; las decisiones, a DECISIONES.md.

**Última actualización:** 2026-09-28 (cierre del día)
**Fase actual:** 11e — Pacientes: ficha, antecedentes y evolución (**completa**, `518ba38`; revisión manual pendiente) → siguiente: 12 (SuperAdmin; no iniciar sin pedirlo)
**Repositorio:** https://github.com/darwinjoelap/biolife (rama `main`, CI en GitHub Actions)
**Responsable:** Darwin

---

## Completado

- [x] Fases 00–11e (hasta `518ba38`, 2026-09-28): base multi-tenant, catálogo, rangos,
  fórmulas, precios, órdenes y tubos, resultados, informe PDF con QR, panel del
  laboratorio, catálogo y tablas auxiliares sin /admin, ficha del paciente con
  antecedentes y evolución (ADR-001–032). Verificado por Darwin: 298 passed, ruff
  limpio. Detalle por fase en `docs/HISTORIAL.md`.

## Dónde estamos

Base del producto terminada: multi-tenancy, usuarios y roles, configuración del laboratorio,
pacientes, catálogo con rangos por sexo/edad/condición, motor de fórmulas, perfiles, precios
multimoneda y el sistema visual. Flujo clínico: recepción, órdenes, tubos y etiquetas
(Fase 09), resultados cargados y validados (Fase 10) e informe PDF con firma, versiones y
verificación por QR (Fase 11). El laboratorio ya no necesita `/admin` para nada; el
paciente tiene ficha, antecedentes y evolución de sus resultados (Fase 11e).

Local: `demo_uno` → http://demo1.localhost:8000/ (+ `public` en localhost).

## Pendiente inmediato

1. Revisión manual pendiente (11 a 11e): examen de prueba con tubo, parámetro y rango,
   ordenarlo y cargarle resultado; precios reales y tasa; entrar como bioanalista,
   técnico y Auxiliar de toma; firma/sello; QR; entregar una orden; *Tablas auxiliares*;
   ficha, evolución y PDF de un paciente con varios resultados; un antecedente visible
   al crear su orden. Siguiente fase: 12 (SuperAdmin), cuando Darwin lo pida.
2. Cargar precios reales en la lista GENERAL (*Precios*): sin ellos las órdenes quedan con
   monto pendiente.
3. **No usar en un informe real** ningún `ReferenceRange`/parámetro marcado "PENDIENTE DE
   CONFIRMAR" o "NO CONFIRMADO" (ver ADR-015 y ADR-016), ni el INR sin
   confirmar el ISI (ADR-017/019), hasta que el laboratorio responda.
4. Confirmar con Angelus los rangos de referencia contradictorios, los rangos
   pediátricos/neonatales reales, y el municipio de Cantagallo, Dos Caminos, Las Minas y
   Píritu (el fixture de localidades se completó sin dato del laboratorio; ver HISTORIAL).

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

## Notas

- **Antes de producción (Fase 17):** sacar `docs/`, `TASKS.md` y `CLAUDE.md` de git y poner el
  repo privado (privacidad: datos del laboratorio de referencia). Decidido 2026-09-27.
- Los formatos originales están en el proyecto de Cowork. No re-analizarlos:
  el resumen completo está en `docs/04_HALLAZGOS_FORMATOS.md`.
- ADRs clave: 007–011 (esquemas, `User` propio), 017–020 (fórmulas, alcance, precios,
  rangos), 021–024 (provisión, visual, órdenes), 025–028 (resultados, informe, QR),
  029–031 (panel, catálogo y tablas sin /admin), 032 (paciente y evolución).
- "7 roles" del índice del roadmap = 6 roles de tenant (esta fase) + `SUPERADMIN_PLATAFORMA`
  como `PlatformUser` en `public` (Fase 12), no un séptimo `Role` de tenant.
- **Postgres local (Darwin):** la base `biolife` está en la instancia **16**, puerto
  **5434** (hay también 17 y 18). Si `manage.py` falla al conectar, revisar el servicio
  `postgresql-x64-16` y que `.env` apunte a `localhost:5434`.
