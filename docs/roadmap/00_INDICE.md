# 00 — Índice del Roadmap

18 fases. Cada una es una sesión de trabajo cerrada con criterio de salida verificable.

**Regla:** el archivo ejecutable de una fase se redacta **al iniciar esa fase**, no antes.
Sólo la Fase 01 viene escrita completa. Redactar las 18 por adelantado produce documentación
que envejece antes de usarse.

| # | Fase | Modelo | Depende de | Criterio de salida |
|---|---|---|---|---|
| 01 | Setup y multi-tenancy | Sonnet | — | Dos tenants aislados creados y verificados |
| 02 | Usuarios, roles y auditoría | Sonnet | 01 | Login por tenant, 7 roles, log de acceso |
| 03 | Configuración del laboratorio | Haiku | 02 | Branding, zona horaria y formato 12 h aplicados |
| 04 | Pacientes y representantes | Sonnet | 02 | Menor sin cédula exige representante |
| 05 | Catálogo: secciones, unidades, parámetros | Sonnet | 03 | Uroanálisis completo cargado con sus 9 tipos de valor |
| 06 | Rangos de referencia | Sonnet | 05 | Resolución por sexo + edad en días, 6 `range_type` |
| 07 | Motor de fórmulas | **Opus** | 06 | Las 16 fórmulas de `04_HALLAZGOS` reproducen los valores reales |
| 08 | Perfiles y lista de precios | Haiku | 05 | Los 13 perfiles de Angelus cargados |
| 09 | Órdenes y muestras | Sonnet | 04, 08 | Orden con numeración, estados y código de barras |
| 10 | Captura y validación de resultados | **Opus** | 07, 09 | Captura con cálculo en vivo, marcado alto/bajo, validación que congela referencias |
| 11 | Informe PDF, firma y QR | Sonnet | 10 | PDF reproduce el formato de Angelus pixel a pixel |
| 12 | Panel SuperAdmin SaaS | Sonnet | 01 | Planes, suscripciones, métricas, suspensión |
| 13 | PWA base y modo lectura offline | Sonnet | 11 | Instalable, consulta órdenes sin conexión |
| 14 | Escritura offline y sincronización | **Opus** | 13 | Captura offline idempotente, conflictos registrados |
| 15 | Rectificaciones y trazabilidad | Sonnet | 10 | Resultado validado inmutable, versión 2 emitida |
| 16 | Gateway de instrumentos (ASTM/HL7) | **Opus** | 10 | Mensaje crudo persistido, parseado y mapeado |
| 17 | Despliegue Railway, CI y backups | Sonnet | 11 | Staging y producción operando, backup automatizado |
| 18 | Hardening y pruebas de carga | Sonnet | 17 | Aislamiento verificado bajo carga, 2FA, rate limiting |

> **Angelus = laboratorio de referencia, no alcance máximo (ADR-018).** Los criterios de
> salida que nombran a Angelus ("los 13 perfiles de Angelus", "reproduce el formato de
> Angelus") se leen como *demostración con datos reales de un laboratorio*: el producto
> debe poder representar eso **y más**, configurable por tenant. Cada fase tiene libertad
> para ir más allá de lo que usan sus hojas.

> **Fase 08b (agregada):** ficha del examen — rangos por sexo/edad/condición (lógica + admin
> provisional). **Fases 08c y 08d (agregadas):** consolidación (ADR-021) y estilo visual y
> pantallas base (ADR-022), antes de la primera pantalla real de la Fase 09.

> **Avance (2026-09-27):** Fases 01–10 completas y verificadas (último commit `bac4352`, en
> GitHub). Próxima: **11 — Informe PDF, firma y QR**. El CI se adelantó desde la Fase 17
> (ADR-021); Railway y backups siguen en la 17.

## Ruta crítica al MVP vendible

```
01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → 09 → 10 → 11 → 17
```

Fases 12–16 y 18 son posteriores al primer laboratorio en producción. **Resistir la
tentación de construir el panel SaaS antes de que el primer laboratorio esté operando** —
es la trampa clásica de los productos multi-tenant: administración pulida sobre un
producto que nadie usa todavía.

## Asignación de modelos

| Modelo | Cuándo |
|---|---|
| **Opus** | Fases 07, 10, 14, 16 — motor de fórmulas, validación clínica, sincronización, protocolos de instrumentos. Son las que tienen decisiones de diseño reales y donde un error cuesta caro. |
| **Sonnet** | Grueso de la implementación: modelos, services, vistas, tests. |
| **Haiku** | Fases 03 y 08, fixtures, siembra de catálogos, tareas repetitivas y bien especificadas. |

## Mapa de dependencias

```
01 ─┬─► 02 ─┬─► 03 ──► 05 ─┬─► 06 ──► 07 ──┐
    │       │              │               │
    │       └─► 04 ────────┼──► 09 ────────┴─► 10 ─┬─► 11 ──► 13 ──► 14
    │                      │                        │
    │                      └─► 08 ──────────────────┤
    │                                               ├─► 15
    └─► 12                                          └─► 16
                                        11 ──► 17 ──► 18
```
