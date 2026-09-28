# Fase 11 — Informe PDF, firma y QR

**Estado:** completa (2026-09-28, `212bb7a`).

**Depende de:** 10 · **Criterio de salida:** informe PDF con cabecera, exámenes por sección
con la observación de cada uno **debajo de su examen**, firmas de quienes validaron, QR de
verificación y versiones que nunca se sobrescriben.

## Decisiones (Darwin, 2026-09-27)

- **Motor:** ReportLab (ya se usaba para etiquetas; sin dependencias de sistema en Windows).
- **QR:** abre una **página pública de verificación**: confirma que el informe es auténtico
  sin mostrar valores clínicos y permite descargar el PDF de la versión vigente mientras
  no venza el plazo del laboratorio (`TenantSettings.report_link_days`, 30 días).
- **Parciales:** sí, marcados PARCIAL (cabecera, recuadro con lo pendiente y marca de agua).
- **Firma:** imagen de firma + sello por bioanalista (en su usuario) + huella SHA-256 del
  contenido.

## Qué se hizo

- [x] App `apps.reports`: `Report` (versión, parcial/final, vigente/reemplazado, contenido
  congelado, huella, huella anterior, código de verificación). Una sola versión vigente por
  orden (constraint).
- [x] Contenido congelado (`build_payload`): laboratorio (razón social, RIF, contacto,
  logo), paciente, orden (médico, registro, primera toma, condición), exámenes
  **validados** por sección con valor, unidad, marca, referencia congelada,
  interpretación y observación; exámenes pendientes; firmantes (quien validó cada examen).
  Las imágenes se guardan por ruta: una firma nueva no altera un informe ya emitido.
- [x] Emisión (`emit_report`): sin validados no hay informe; mismo contenido = misma versión
  (no duplica); contenido distinto = versión siguiente, encadenada por huella, y la
  anterior queda *Reemplazada* (se conserva).
- [x] PDF carta (`render_report_pdf`): cabecera en cada página (logo, laboratorio, «INFORME
  DE RESULTADOS», orden, versión, PARCIAL; recuadro del paciente con C.I., historia, edad,
  sexo, médico, registro, toma y emisión); secciones con barra de color del laboratorio;
  exámenes de un parámetro en una línea; grupos (serie roja, examen físico…); marcas ▲ ▼,
  críticos en rojo con «C», anormal «*» y leyenda; observaciones debajo de cada examen;
  firmas con imagen de firma y sello, nombre, título y colegiatura; pie con el texto legal
  del laboratorio (o el de §11 de los hallazgos), teléfono e Instagram, QR, huella y
  «Página X de Y». Marca de agua PARCIAL o REEMPLAZADO. La barra de una sección nunca
  queda sola al pie de una página; un examen corto no se parte.
- [x] Pantallas: *Informes* en el menú (listas para entregar / parciales / entregadas),
  informe de la orden (vigente, emitir versión N+1 cuando hay cambios, ver/descargar PDF,
  historial de versiones, enlace de verificación con copiar, marcar entregada). Botón
  *Informe* en la orden y en la captura de resultados.
- [x] Verificación pública `/verificar/<código>/` (sin sesión): auténtico/reemplazado,
  iniciales y últimos 3 dígitos de la C.I., orden, versión, fecha, n.º de exámenes,
  firmantes, huella completa; **sin valores ni nombres de exámenes**. `/pdf/` sólo para la
  vigente y dentro del plazo (404 si no).
- [x] Entrega: `orders.services.mark_delivered` (sólo con todo validado; emite antes para
  que lo entregado sea lo último validado). `Order.delivered_at/delivered_by`.
- [x] Usuario: `professional_title`, `signature_image`, `stamp_image` (admin → Usuarios →
  *Datos de Biolife*). Laboratorio: `report_link_days`.
- [x] Tests: +10 (reports).

## Ajustes tras la primera revisión de Darwin (2026-09-27)

- [x] Pie sin el texto «firma y sello húmedo» (sólo el texto propio del laboratorio, si lo
  configura); línea de verificación; firma de Biolife con su ícono, editable en el admin de
  `public` → *Configuración de la plataforma* (ADR-028).
- [x] Instagram y correo del laboratorio bajo el número de orden en la cabecera.
- [x] Firma y sello del bioanalista en **cada página** (franja inferior derecha, sobre el
  pie), en lugar de un bloque al final. El QR sube a esa franja, a la izquierda, a la
  altura de la firma; el pie queda más bajo con el enlace y la firma de Biolife con un
  ícono más grande. Un examen largo (uroanálisis) ahora se parte entre
  páginas repitiendo su título, en vez de saltar entero a la página siguiente.
- [x] Orden con precio pendiente: botón **Recotizar con los precios actuales** (sólo si
  quedó pendiente; una orden cotizada no se toca). Antes no había forma de cobrarla.
- [x] Examen sin parámetros: aviso al elegirlo en la orden («Sin parámetros»), al
  registrarla y en la captura. Caso real: un «Hematologia completa» (código HC) creado a
  mano, distinto del sembrado HEMATOLOGÍA COMPLETA (HEM_COMP).
- [x] El admin de un laboratorio ya no muestra laboratorios, planes ni suscripciones.
- [x] Se puede marcar un tubo como tomado aunque ya haya resultados cargados (antes el
  botón desaparecía al pasar la orden a «Resultados cargados»); no en anuladas/entregadas.

## Verificación en la máquina de Darwin

- [x] `migrate_schemas` (accounts.0005, orders.0003, reports.0001, settings_lab.0005) y
  256 passed, ruff limpio (primera entrega).
- [x] `migrate_schemas` (tenants.0002); 258 passed y, con los últimos ajustes, 259 passed ·
  ruff limpio. Commit `212bb7a` (2026-09-28).
- [ ] (por confirmar) Admin → Usuarios → su usuario: título, colegiatura, imagen de firma y de sello (PNG
  con fondo transparente se ve mejor). Admin → Laboratorio: logo, teléfono, dirección,
  Instagram; Admin → tenant: razón social y RIF.
- [ ] (por confirmar) Una orden con parte validada → *Informe* → emitir (parcial) → ver PDF. Validar el
  resto → emitir versión 2 (final) → la v1 queda reemplazada. Escanear el QR con el
  teléfono (en local sólo abre si el teléfono resuelve `demo1.localhost`; si no, abrir el
  enlace *Verificación* en el navegador). Marcar entregada.

## Diferencias con lo planificado (registradas en ADR-027)

- El índice decía «reproduce el formato de Angelus pixel a pixel». Se tomó su contenido
  (§11: cabecera, datos del paciente, pie legal) con un diseño propio: Angelus es
  referencia, no plantilla (ADR-018).
- No hay tabla `ResultSignature` ni PDF guardado en Cloudinary: la firma es quien validó +
  su imagen, y la huella cubre el informe completo; el PDF se genera desde el contenido
  congelado (nada queda en una URL pública).
- `report_header_html` no se usa (ReportLab no dibuja HTML); la cabecera sale de los datos
  del laboratorio.

## No incluye

- Envío por WhatsApp/correo (hoy: copiar el enlace). Firma digital con certificado (PKI).
- Pantalla propia para que cada bioanalista suba su firma (hoy: admin).
- Rectificaciones (Fase 15): al rectificar se emitirá otra versión por este mismo flujo.
- Ajustes por laboratorio del diseño (tamaño oficio, columnas, orden de secciones).
