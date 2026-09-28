# Fase 11d — Tablas auxiliares sin /admin

**Estado:** entregada (2026-09-28), pendiente de verificación en la máquina de Darwin.

**Depende de:** 11c · **Criterio de salida:** el laboratorio mantiene sus tablas de
apoyo (secciones, unidades, métodos, listas de opciones, observaciones generales, tubos,
lotes de reactivos, monedas y descuentos) desde pantallas propias. En el menú sólo queda
el `/admin` de pacientes, hasta la Fase 11e.

## Decisiones (Darwin, 2026-09-28)

- **Formato:** índice *Tablas auxiliares* con tarjetas; cada tabla con su lista (buscar,
  ver inactivos) y su ficha, como Exámenes.
- **Quién edita** (además del administrador): el **bioanalista** listas de opciones y
  observaciones generales; **bioanalista y técnico** los lotes de reactivos (registrar el
  lote nuevo al cambiar de reactivo); **facturación** monedas y descuentos. Todos los roles
  de laboratorio consultan.
- **Moneda base fija** tras crearse: se editan nombre, símbolo, decimales y orden.
- **Pacientes** (lista, ficha, representantes, historial y evolución) van aparte, en la
  **Fase 11e**.

## Qué se hizo

- [x] Motor genérico en `apps/core/aux_tables.py`: cada app registra sus tablas
  (`AuxTable`) en `AppConfig.ready()`; `core` pone índice, lista y ficha
  (`/tablas/`, `/tablas/<tabla>/`, `.../nuevo/`, `.../<id>/`; plantillas en
  `templates/core/tablas/`, no `aux/`: Windows reserva ese nombre) sin conocer los modelos.
- [x] Catálogo (`apps/catalog/aux_tables.py`): secciones, unidades, métodos, listas de
  opciones (con sus opciones en tabla), observaciones generales o de sección, tubos y
  envases (color con selector), lotes de reactivos.
- [x] Cobro (`apps/billing/aux_tables.py`): monedas y descuentos (por orden o por
  examen/perfil, porcentaje o monto fijo, vigencia, acumulable, autorización).
- [x] Reglas: nada se borra (se desactiva). Código fijo cuando ya está en uso (sección con
  exámenes, lista con parámetros, tubo en exámenes u órdenes, moneda existente). Una lista
  de opciones con resultados conserva el texto de sus opciones (se pueden agregar nuevas y
  desactivar). Una lista activa necesita al menos una opción activa. Un lote vigente
  desplaza al anterior del mismo reactivo; tromboplastina vigente exige ISI. Moneda nueva
  nunca es base; la base no se desactiva, ni una moneda con listas de precios activas.
- [x] Todo queda en `AuditLog` (`TABLA_CREADA`, `TABLA_MODIFICADA`).
- [x] Menú: *Catálogo → Tablas auxiliares*; se quitaron los accesos a `/admin` de tubos,
  lotes y tablas. Tabla *Roles* con las nuevas capacidades.
- [x] Corrección de paso (11c): la casilla «Quitar» ya no aparece en filas nuevas vacías.
- [x] Tests: +11 (`apps/catalog/tests/test_aux_tables.py`).

## Verificación en la máquina de Darwin

- [ ] `python manage.py check` y `makemigrations --check` (no hay migraciones).
- [ ] `pytest -q` → 287 passed · `ruff check .` limpio.
- [ ] Recorrer *Tablas auxiliares*: abrir cada tabla, crear una unidad de prueba y
  desactivarla; crear el lote de tromboplastina (con ISI) si se va a probar PT/INR.
- [ ] Entrar como técnico: consulta todo y sólo guarda lotes.

## No incluye

- Pacientes sin `/admin` (Fase 11e). Tipos de reactivo nuevos (hoy sólo tromboplastina).
- Localidades (`masterdata`): son tabla compartida del SaaS, no del laboratorio.
