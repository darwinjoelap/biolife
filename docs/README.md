# Biolife — Sistema SaaS para Laboratorios Clínicos

Hoja de ruta maestra de arquitectura y ejecución.
Este paquete **no contiene código**: contiene las decisiones, el modelo de datos y los
prompts ejecutables que alimentan a los modelos de implementación fase por fase.

## Cómo usar este repositorio

1. Copia esta carpeta a la raíz del repo de Biolife.
2. `CLAUDE.md` queda en la **raíz del repo** (no dentro de `docs/`).
3. Cada sesión de trabajo ejecuta **una** fase: `docs/roadmap/NN_nombre.md`.
4. Al cerrar sesión se actualizan `docs/ESTADO.md` y `docs/DECISIONES.md`. Sin excepción.

## Mapa de archivos

| Archivo | Qué contiene | Cuándo leerlo |
|---|---|---|
| `CLAUDE.md` | Contexto permanente del proyecto. Se inyecta en cada sesión. | Siempre (automático) |
| `docs/00_ARQUITECTURA.md` | Decisiones estructurales, multi-tenancy, capas, PWA, integraciones | Antes de cualquier fase nueva |
| `docs/01_MODELO_DATOS.md` | Modelo ER completo, entidades, constraints, casos borde | Fases 04–11 |
| `docs/02_ESTRUCTURA_PROYECTO.md` | Árbol de carpetas exacto | Fase 01 |
| `docs/03_CONVENCIONES.md` | Naming, services/selectors, tests, commits | Siempre que se escriba código |
| `docs/04_HALLAZGOS_FORMATOS.md` | Análisis de los Excel reales del laboratorio | Fases 05–07, 11 |
| `docs/DECISIONES.md` | Bitácora ADR ligera, append-only | Al cerrar cada sesión |
| `docs/ESTADO.md` | Estado vivo del proyecto | Al abrir y al cerrar cada sesión |
| `docs/COWORK_Y_CONTEXTO.md` | Configuración de Cowork/Claude para no perder contexto | Una vez, al inicio |
| `docs/roadmap/00_INDICE.md` | Las 18 fases, dependencias y criterios de salida | Al planificar |
| `docs/roadmap/_PLANTILLA_FASE.md` | Estructura obligatoria de todo archivo de fase | Al redactar una fase nueva |
| `docs/roadmap/01_setup_y_tenants.md` | Fase 1 completa y ejecutable | Primera sesión de código |

## Estado actual

Fase 00 (diseño) **completa**. Fase 01 lista para ejecución.
Fases 02–17 definidas a nivel de objetivo y criterio de salida; su contenido ejecutable
se redacta al inicio de cada fase, no antes (evita documentación que envejece).
