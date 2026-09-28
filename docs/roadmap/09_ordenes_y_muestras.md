# Fase 09 — Órdenes y muestras

**Depende de:** 04, 08, 08d · **Modelo usado:** Opus · **Criterio de salida:** orden con
numeración, estados y código de barras; un tubo por tipo con su etiqueta.

## Decisiones (Darwin, 2026-09-27)

- **Número de orden diario `AAMMDD-NNNN`** (reinicia cada día, hasta 9.999). Cada tubo es
  `AAMMDD-NNNN-SS`; su código de barras son esos 12 dígitos sin guiones (Code 128, sólo
  números: lo leen también los analizadores viejos de la Fase 16).
- **Cobro:** la orden congela la cotización (líneas, descuentos, total, tasa) y marca
  pagada sí/no. Caja con abonos, métodos de pago y vuelto: fase propia más adelante.
- **Pantallas:** flujo de recepción completo (paciente, orden, tubos, etiquetas, toma).
- **Etiqueta:** térmica de 50 × 25 mm en PDF (lo más común; la impresora aún no está
  definida). Ancho y alto se cambian en *Laboratorio* sin tocar código.

## Lógica de tubos (ADR-024)

1. El tubo lo define el aditivo. Cada examen pide uno o más tubos (`SampleRequirement`).
2. En una orden, los exámenes que piden el mismo tubo y la misma toma **comparten tubo**.
3. Van aparte: *tubo propio* (envío externo, hielo, otra área), lo que exceda el máximo
   por tubo, y las **tomas por tiempo** (curvas: «Post-carga 2 h» no va con el basal).
4. Numeración en **orden de extracción** CLSI: azul (citrato) → rojo/amarillo (suero) →
   verde (heparina) → morado (EDTA) → gris (fluoruro) → frascos.
5. **Agregar exámenes** después: entran en un tubo *por tomar* compatible; si ya se tomó,
   se crea uno nuevo. La orden se recotiza (si estaba pagada, queda con saldo).
6. **Rechazo** (hemólisis, insuficiente, coagulada): la muestra queda rechazada con su
   motivo y se crea un **reemplazo con número nuevo**; un número nunca se reutiliza.
7. Estado de la orden: *Registrada* → *Muestra tomada* cuando todas las vigentes se toman.

Ejemplo de Darwin — hematología + colesterol + triglicéridos + tiempos de coagulación:
`-01 AZUL` (PT/PTT) · `-02 ROJO` (colesterol, triglicéridos) · `-03 MORADO` (hematología).

## Qué se hizo

- [x] `catalog.ContainerType` + `SampleRequirement` (reemplazan el texto libre
  `Test.container`), admin con color, inline «Tubos que requiere» en cada examen.
- [x] Siembra `seed_containers()` (9 tubos/envases; todo examen del catálogo base queda con
  tubo; depuración = envase 24 h + rojo; curvas con su toma). Nunca pisa ediciones.
  Comando `seed_contenedores`; los laboratorios nuevos ya nacen con tubos.
- [x] App `apps.orders`: `Order`, `OrderItem`, `Sample` (M2M con los exámenes),
  `OrderNumberSequence`, `LabelPrint`.
- [x] Services: `numbering`, `order_creation` (`build_draft` = vista previa idéntica a lo
  que se guarda; `create_order`), `sample_planning` (`plan_tubes` pura), `sample_collection`
  (tomar, tomar todas, rechazar con reemplazo), `order_management` (agregar, pagar, anular),
  `labels` (PDF con ReportLab, registro de reimpresiones).
- [x] Avisos al registrar (no bloquean): sin precio en la lista (la orden queda con monto
  pendiente), exámenes sin tubo, datos antropométricos faltantes, insumos de cálculos
  faltantes, exámenes que requieren ayuno, examen ya incluido en un perfil.
- [x] Pantallas: nueva orden (búsqueda de paciente y exámenes, resumen en vivo con monto y
  tubos), registro de paciente (con representante para menores sin documento), lista del
  día con indicadores, «Muestras por tomar», detalle con tubos y acciones, agregar exámenes,
  etiquetas PDF. Buscador superior acepta el lector de código de barras (va directo a la
  orden). Inicio con indicadores reales.
- [x] Permisos: recepción, bioanalista, técnico, facturación y administrador registran;
  sólo lectura consulta; el superusuario siempre pasa.
- [x] `patients.services.patient_age`: edad en días / texto / corta (etiquetas; Fase 10).
- [x] Tests: +28 (211 en total). Códigos de barras verificados con lector (zbar) a 203 dpi.

## Verificación en la máquina de Darwin (2026-09-27: todo OK, commit `9919111`)

- [x] `pip install -r requirements/local.txt` (nuevo: `reportlab`).
- [x] `python manage.py migrate_schemas` (catalog.0007, orders.0001, settings_lab.0004).
- [x] `python manage.py tenant_command seed_contenedores --schema=demo_uno`.
- [x] En *Laboratorio* (admin): cargar **Siglas del laboratorio** si está vacío (lo pide el
  código de paciente).
- [x] `pytest -q` → 211 · `ruff check .`
- [x] `runserver` → `http://demo1.localhost:8000/`: registrar un paciente, crear la orden
  del ejemplo, ver 3 tubos, imprimir etiquetas, tomar, rechazar, agregar un examen, pagar.

## No incluye

- Caja: abonos, métodos de pago, vuelto, facturas (fase propia).
- Captura de resultados y valores críticos (Fase 10). Recepción de muestras por área
  (estado «recibida en el laboratorio»): cuando exista la lista de trabajo por sección.
- Impresión directa ZPL/EPL (necesita un agente local); se imprime el PDF desde el
  navegador.
- Precios del laboratorio: la lista GENERAL sigue vacía; las órdenes quedan con monto
  pendiente hasta cargarlos.

## Ajuste posterior (2026-09-28): *Muestras por tomar* para el auxiliar

- [x] Pantalla propia (`orders/collection.html`): sin columna de pago ni total.
- [x] Etiquetas: cada fila dice si están «Sin imprimir», «1 de 2» o «Impresas», con quién
  imprimió y a qué hora (`LabelPrint`). Con todas impresas la fila se atenúa y baja al
  final: arriba quedan los pacientes que nadie ha atendido (urgentes y más antiguos
  primero). Botón *Imprimir / Reimprimir* en la fila, sólo con los tubos por tomar.
- [x] Se actualiza sola cada 20 s con htmx (sólo la tabla, sin perder la búsqueda; en
  pausa si la pestaña está oculta, y al volver a ella) y 2,5 s después de imprimir.
- [x] Tests: +1.
