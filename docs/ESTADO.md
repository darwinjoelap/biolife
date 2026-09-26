# ESTADO DEL PROYECTO — Biolife

> Se actualiza al **cerrar cada sesión**. Es el primer archivo que se lee al abrir la siguiente.
> Mantener bajo 100 líneas: si crece, es que hay historial que pertenece a DECISIONES.md.

**Última actualización:** 2026-09-26
**Fase actual:** 08b — Ficha del examen (rangos) (**completa y verificada**) → siguiente: 09 (órdenes y muestras)
**Responsable:** Darwin

---

## Completado

- [x] Fases 00–05 (commits hasta `c9ac6ab`): diseño, multi-tenancy, usuarios y roles,
  configuración del laboratorio, pacientes, catálogo (ADR-001 a ADR-015).
- [x] Fase 06 (`d3475eb`) y Fases 07–08b (`53655ab`): rangos, motor de fórmulas, perfiles,
  precios multimoneda, ficha del examen (ADR-016 a ADR-020).
- [x] Fase 08c: laboratorios nacen con catálogo, lípidos sin AYUNO, CI, script de
  aislamiento reparado (ADR-021).
- [x] Fase 08d: sistema visual (CSS plano, paleta del logo, pantallas densas), acceso, Inicio,
  guía de estilo en `/estilo/`, admin con la marca (ADR-022). 180/180 en el entorno de Claude.

## En curso

Fases 08c y 08d escritas en disco; falta que Darwin corra `migrate_schemas`, `pytest` (180),
`ruff` y revise `/`, `/estilo/` y el acceso con `runserver`.

## Pendiente inmediato

1. Verificar 08c/08d. Siguiente: Fase 09 (órdenes y muestras) con el nuevo estilo.
2. Cargar precios reales en la lista GENERAL (admin) cuando se tengan.
3. **No usar en un informe real** ningún `ReferenceRange`/parámetro marcado "PENDIENTE DE
   CONFIRMAR" o "NO CONFIRMADO" (ver ADR-015 y ADR-016), ni el INR sin
   confirmar el ISI (ADR-017/019), hasta que el laboratorio responda.
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
- ADRs que conviene leer antes de tocar ciertas zonas: 007–009 (esquemas en
  django-tenants), 010–011 (`User` propio, `accounts` SHARED+TENANT), 017 (fórmulas),
  018 (alcance: Angelus es referencia), 019 (perfiles y precios), 020 (rangos y admin por
  tenant), 021 (provisión con catálogo, CI), 022 (sistema visual y `STORAGES`).
- "7 roles" del índice del roadmap = 6 roles de tenant (esta fase) + `SUPERADMIN_PLATAFORMA`
  como `PlatformUser` en `public` (Fase 12), no un séptimo `Role` de tenant.
- **Postgres local (máquina de Darwin):** hay 3 instalaciones (16, 17, 18). La base
  `biolife` del proyecto vive en la instancia **16**, que corre en el puerto **5434**
  (se cambió de 5432 porque la instancia 18 ya lo ocupaba con otro proyecto). Si
  `manage.py` da error de autenticación o "no existe la base de datos", verificar primero
  que el servicio `postgresql-x64-16` esté corriendo y que `.env` apunte a
  `localhost:5434`.
