# ESTADO DEL PROYECTO — Biolife

> Se actualiza al **cerrar cada sesión**. Es el primer archivo que se lee al abrir la siguiente.
> Mantener bajo 100 líneas: si crece, es que hay historial que pertenece a DECISIONES.md.

**Última actualización:** 2026-09-19
**Fase actual:** 00 — Diseño (completa) → siguiente: 01 Setup y multi-tenancy
**Responsable:** Darwin

---

## Completado

- [x] Análisis de los formatos Excel del Laboratorio Angelus
- [x] Decisión de estrategia multi-tenancy (esquemas PostgreSQL vía django-tenants)
- [x] Modelo de datos completo (`docs/01_MODELO_DATOS.md`)
- [x] Estructura de proyecto definida (`docs/02_ESTRUCTURA_PROYECTO.md`)
- [x] Convenciones de código (`docs/03_CONVENCIONES.md`)
- [x] Roadmap de 18 fases (`docs/roadmap/00_INDICE.md`)
- [x] Fase 01 redactada y lista para ejecución (`docs/roadmap/01_setup_y_tenants.md`)
- [x] Corregida inconsistencia de rutas: `00_INDICE.md` y `01_setup_y_tenants.md` ahora
      viven en `docs/roadmap/`, como describe `README.md`, en lugar de sueltos en `docs/`

## En curso

Nada. Fase 01 sin iniciar.

## Pendiente inmediato

1. **Borrar manualmente los duplicados** que quedaron en `docs/` (no en `docs/roadmap/`):
   `docs/00_INDICE.md` y `docs/01_setup_y_tenants.md` — el contenido correcto y vigente
   está en `docs/roadmap/`.
2. Crear el repositorio y copiar este paquete de documentación
3. Ejecutar `docs/roadmap/01_setup_y_tenants.md`

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

## Notas

- Los formatos originales están en el proyecto de Cowork. No re-analizarlos:
  el resumen completo está en `docs/04_HALLAZGOS_FORMATOS.md`.
