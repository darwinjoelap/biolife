# Fase 08d — Estilo visual y pantallas base

**Depende de:** 08c · **Modelo usado:** Opus · **Origen:** Darwin pidió un estilo moderno y
minimalista, sin tener que desplazarse para ver todos los campos, con el logo de Biolife
(la versión sin nombre).

## Decisiones

- **CSS plano sin build** (`static/css/biolife.css`) en vez de Tailwind: nada que compilar en
  Windows ni en CI, un solo archivo cacheable, funciona offline (ADR-022).
- **Paleta del logo:** navy `#0b2e63`, azul `#0d6dc9`, verde azulado `#11ad9b` (texto:
  `#0b7f72`). El laboratorio cambia `--brand` desde su configuración.
- **Densidad:** texto base 13,5 px, controles de 32 px, formularios en grilla de 12 columnas
  (12 campos caben en una pantalla de 1366×768), tablas compactas, barra de acciones fija.
- **Inter autoalojada** (OFL), íconos **Lucide** en sprite SVG (ISC), **htmx 2.0.11** y
  **Alpine 3.17.4** servidos desde `static/vendor/` (sin CDN: sirve sin internet y para la PWA).
- **Marcas clínicas:** NORMAL sin marca; ALTO en rojo, BAJO en azul; CRÍTICO en bloque rojo
  sólido con la fila resaltada: no se puede pasar por alto.

## Qué se hizo

- [x] `templates/base.html` (documento), `base_tenant.html` (barra lateral colapsable,
  barra superior, mensajes), `base_auth.html` (acceso).
- [x] Acceso rediseñado; **Inicio** real (`/`) en lugar del texto provisional.
- [x] **Guía de estilo viva** en `/estilo/` (sólo staff): color, botones, etiquetas, avisos,
  formulario denso, captura de resultados con marcas, lista de trabajo, estado vacío.
- [x] `{% load ui %}`: `icon`, `field`, `initials`, `nav_active`.
- [x] Íconos de marca: favicon, apple-touch, 192/512 para la PWA (`static/img/brand/`).
- [x] Admin con la identidad de Biolife y nombres de secciones en español.
- [x] **Bug corregido:** Django 5.1 eliminó `STATICFILES_STORAGE`; WhiteNoise no comprimía ni
  versionaba nada. Ahora `STORAGES` (producción con manifiesto; local/tests sin él).
- [x] Tests: +7 (pantallas y etiquetas).

## No incluye

- Pantallas reales de pacientes, órdenes y resultados (Fases 09 y 10, ya con este estilo).
- Modo oscuro (decisión: una clínica trabaja con fondo claro; se puede agregar con tokens).
- `manifest.webmanifest` y service worker (Fase 13; los íconos ya están).
- `color-mix()` requiere Chrome 111+ / Safari 16.2+; en navegadores más viejos los fondos
  suaves del color del laboratorio quedan transparentes (se degrada, no se rompe).
