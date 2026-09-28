# ESTADO DEL PROYECTO — Biolife

> Se actualiza al **cerrar cada sesión**. Es el primer archivo que se lee al abrir la siguiente.
> Mantener bajo 100 líneas: si crece, es que hay historial que pertenece a DECISIONES.md.

**Última actualización:** 2026-09-27 (Fase 11)
**Fase actual:** 11 — Informe PDF, firma y QR (**en verificación** con ajustes de Darwin) → siguiente: 11b (panel del laboratorio)
**Repositorio:** https://github.com/darwinjoelap/biolife (rama `main`, CI en GitHub Actions)
**Responsable:** Darwin

---

## Completado

- [x] Fases 00–08b (hasta `53655ab`): diseño, multi-tenancy, usuarios y roles, configuración,
  pacientes, catálogo, rangos, fórmulas, perfiles, precios, ficha del examen (ADR-001–020).
- [x] Fases 08c, 08d y limpieza (`39a4491`, `7ad6be1`): provisión con catálogo, CI, sistema
  visual, baja de laboratorios demo (ADR-021–023). Verificado: 183 passed; CI en verde.
- [x] Fase 09 (`9919111`): órdenes, tubos, etiquetas, recepción (ADR-024). Verificado: 211.
- [x] Fase 10 (`f934aaf`, `bac4352`): captura con cálculo en vivo, marcas alto/bajo/crítico, aviso de
  críticos, validación que congela referencias, ISI por lote, observaciones por examen
  (ADR-025/026). Verificado por Darwin: 246 passed, ruff limpio.
- [~] Fase 11 (sin commit): informe PDF versionado desde contenido congelado, parciales,
  firma + sello por bioanalista, huella SHA-256, QR a página pública de verificación,
  bandeja *Informes*, entrega (ADR-027). Verificado por Darwin: migraciones, 256 passed,
  ruff limpio. Ajustes tras su revisión (ADR-028): pie nuevo con firma de Biolife
  editable en `public`, Instagram/correo en la cabecera, recotizar órdenes con precio
  pendiente, avisos de examen sin parámetros.

## Dónde estamos

Base del producto terminada: multi-tenancy, usuarios y roles, configuración del laboratorio,
pacientes, catálogo con rangos por sexo/edad/condición, motor de fórmulas, perfiles, precios
multimoneda y el sistema visual. Flujo clínico: recepción, órdenes, tubos y etiquetas
(Fase 09), resultados cargados y validados (Fase 10) e informe PDF con firma, versiones y
verificación por QR (Fase 11, por verificar).

Local: `demo_uno` → http://demo1.localhost:8000/ (+ `public` en localhost).
## Pendiente inmediato

1. Terminar de verificar la Fase 11 (checklist en `docs/roadmap/11_informe.md`): migrar
   `tenants.0002`, tests; anular la orden 260927-0001 (examen HC sin parámetros) y
   desactivar ese examen; cargar
   firma/sello/título en su usuario y logo, RIF y razón social del laboratorio, emitir un
   parcial y un final, escanear el QR, marcar entregada. Luego el commit.
   Sigue pendiente el lote de tromboplastina vigente en `demo_uno` (sin él no hay INR).
2. Cargar precios reales en la lista GENERAL (admin): sin ellos las órdenes quedan con
   monto pendiente.
3. **No usar en un informe real** ningún `ReferenceRange`/parámetro marcado "PENDIENTE DE
   CONFIRMAR" o "NO CONFIRMADO" (ver ADR-015 y ADR-016), ni el INR sin
   confirmar el ISI (ADR-017/019), hasta que el laboratorio responda.
4. Confirmar con Angelus los rangos de referencia contradictorios, los rangos
   pediátricos/neonatales reales, y el detalle geográfico de localidades sin municipio
   verificado (Cantagallo, Dos Caminos, Las Minas, Píritu).

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

- **Antes de producción (Fase 17):** sacar `docs/`, `TASKS.md` y `CLAUDE.md` de git y poner el
  repo privado (privacidad: datos del laboratorio de referencia). Decidido 2026-09-27.
- Los formatos originales están en el proyecto de Cowork. No re-analizarlos:
  el resumen completo está en `docs/04_HALLAZGOS_FORMATOS.md`.
- ADRs que conviene leer antes de tocar ciertas zonas: 007–009 (esquemas en
  django-tenants), 010–011 (`User` propio, `accounts` SHARED+TENANT), 017 (fórmulas),
  018 (alcance: Angelus es referencia), 019 (perfiles y precios), 020 (rangos y admin por
  tenant), 021 (provisión con catálogo, CI), 022 (sistema visual y `STORAGES`), 023 (baja de
  laboratorios demo), 024 (órdenes, tubos y etiquetas), 025
  (resultados, críticos, ISI), 026 (observaciones por examen), 027 (informe, versiones y QR), 028 (pie del informe y
  firma de la plataforma).
- "7 roles" del índice del roadmap = 6 roles de tenant (esta fase) + `SUPERADMIN_PLATAFORMA`
  como `PlatformUser` en `public` (Fase 12), no un séptimo `Role` de tenant.
- **Postgres local (máquina de Darwin):** hay 3 instalaciones (16, 17, 18). La base
  `biolife` del proyecto vive en la instancia **16**, que corre en el puerto **5434**
  (se cambió de 5432 porque la instancia 18 ya lo ocupaba con otro proyecto). Si
  `manage.py` da error de autenticación o "no existe la base de datos", verificar primero
  que el servicio `postgresql-x64-16` esté corriendo y que `.env` apunte a
  `localhost:5434`.
