# Fase 11c — Catálogo sin /admin (exámenes, rangos, perfiles, precios)

**Depende de:** 11b · **Criterio de salida:** el laboratorio mantiene su catálogo del día
a día (exámenes, parámetros, rangos y críticos, observaciones, perfiles, precios y tasa)
desde pantallas propias, sin `/admin`.

## Decisiones (Darwin, 2026-09-28)

- **11c** = lo diario; **11d** = tablas auxiliares (tubos, lotes de reactivos, unidades,
  métodos, secciones, listas de opciones, monedas), que mientras tanto siguen en `/admin`.
- **Quién edita:** el administrador todo; el **bioanalista** rangos, valores críticos y
  observaciones (criterio clínico); precios y tasa, administrador y **facturación**. Todos
  los roles de laboratorio consultan.
- **Precios:** tabla editable (se guarda al salir del campo), ajuste masivo por % con
  redondeo, tasa del día en un recuadro.
- Una sola entrega.

## Qué se hizo

- [x] *Catálogo → Exámenes* (`/catalogo/examenes/`): lista con sección, muestra, tubos,
  n.º de parámetros (aviso si 0 o sin tubo), búsqueda, filtro por sección, inactivos.
- [x] Ficha del examen: parámetros en orden de informe con sus rangos resumidos (y «C» si
  tiene críticos); datos del examen; tubos que requiere; grupos; observaciones propias.
  Un examen ya ordenado conserva su código.
- [x] Ficha del parámetro: datos (tipo de valor, unidad, decimales, grupo, lista de
  opciones, fórmula validada con sus dependencias), rangos por sexo/edad
  (años·meses·días)/condición con críticos, avisos de solapes y huecos, y **probador**.
  Un parámetro con resultados conserva código y tipo de valor.
- [x] *Catálogo → Perfiles*: lista y ficha con buscador de exámenes, orden con flechas y
  aviso si falta un examen que alimenta un cálculo del perfil.
- [x] *Catálogo → Precios* (`/precios/`): lista de precios, perfiles y exámenes con precio
  editable en la fila (htmx; «1.250,50» o «1250.50»; vacío = sin precio), perfiles en
  «precio fijo» o «suma de exámenes menos %», ajuste masivo, lista predeterminada, copiar
  a una lista nueva (incluso a otra moneda con la tasa del día) y **registro de la tasa**.
- [x] Nada se borra: exámenes, parámetros, rangos y observaciones se desactivan; sólo se
  quitan filas de tubos y grupos vacíos. Todo queda en `AuditLog`.
- [x] Menú: grupo *Catálogo* (Exámenes, Perfiles, Precios) según el rol; el `/admin`
  queda como «Administración (provisional)» para tubos, lotes y tablas auxiliares.
- [x] Tests: +7.

## Verificación en la máquina de Darwin

- [ ] `pytest -q` · `ruff check .` (no hay migraciones).
- [ ] Crear un examen de prueba con su tubo, un parámetro numérico y un rango; ordenarlo y
  cargarle resultado.
- [ ] En *Precios*: cargar precios reales en la lista GENERAL y registrar la tasa del día.
- [ ] Entrar como bioanalista: puede cambiar rangos/críticos/observaciones y no el resto.

## No incluye

- Tablas auxiliares (Fase 11d). Importar el catálogo desde Excel. Copiar un examen.
- Descuentos (siguen en `/admin`) y reordenar la lista de precios.
