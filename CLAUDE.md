# CLAUDE.md — Contexto permanente de Biolife

> Este archivo se lee al inicio de **cada** sesión. Mantenerlo corto (< 200 líneas).
> Lo que cambia seguido va en `docs/ESTADO.md`, no aquí.

## Qué es Biolife

SaaS multi-tenant para laboratorios clínicos. Cada laboratorio cliente es un *tenant*
aislado con su propia identidad visual, catálogo de exámenes, rangos de referencia y
usuarios. Producto de BioLife Diagnostics, Venezuela. Interfaz y datos en **español**.

## Alcance del producto y papel de Angelus

- **Biolife no automatiza a Angelus.** Es un producto para **muchos** laboratorios y
  debe ser lo más completo posible — más de lo que hoy tiene Angelus.
- Las hojas de trabajo de Angelus (`docs/04_HALLAZGOS_FORMATOS.md`) son una **base de
  referencia** para arrancar: datos reales para sembrar ejemplos y probar el diseño, no el
  límite del alcance ni una especificación a copiar.
- Hay **libertad creativa**: se pueden agregar funciones, exámenes, fórmulas o
  configuraciones que Angelus no usa si son útiles para un laboratorio clínico en general.
  Lo que difiera entre laboratorios se modela como **configuración por tenant**, no como
  regla fija. Ver ADR-018.
- Las respuestas de Angelus a las preguntas abiertas alimentan **sus datos de tenant**;
  no bloquean decisiones de producto.

## Stack fijo (no renegociar sin ADR)

- Django 5.x + Python 3.13 (ver ADR-006 — originalmente 3.12, no disponible en la máquina de desarrollo)
- PostgreSQL 16 con **esquemas** por tenant vía `django-tenants`
- Cloudinary para media
- Railway para staging y producción
- PWA: Service Worker + IndexedDB (Dexie) para modo offline parcial
- Frontend: Django Templates + HTMX + Alpine.js. **No SPA.**
- Zona horaria por defecto: `America/Caracas`. Hora siempre en formato **12 h (hh:mm AM/PM)**.

## Reglas de arquitectura (obligatorias)

1. **Cero monolito.** `views.py` sólo orquesta: valida entrada, llama a un service o
   selector, devuelve respuesta. Máximo ~25 líneas por vista.
2. Lógica de negocio en `services/`. Consultas en `selectors/`. Ningún ORM en vistas.
3. Ningún `import` cruzado entre apps de dominio. La comunicación va por `services/`
   públicos o señales. `core/` puede ser importado por todos; `core/` no importa a nadie.
4. Modelos delgados: validaciones de integridad en `clean()` y constraints de BD.
   Reglas de negocio en services.
5. Todo modelo de tenant hereda de `core.models.TenantBaseModel`
   (uuid, created_at, updated_at, created_by, is_active).
6. Nada de borrado físico en datos clínicos. Soft delete + auditoría.

## Reglas de dominio no negociables

- Un resultado **validado** es inmutable. Corregir = crear una *rectificación* versionada
  que referencia el original. Nunca se sobreescribe.
- Un paciente menor sin cédula **requiere** al menos un representante legal con documento.
- Los rangos de referencia dependen de sexo + edad (en días) y se imprimen tal cual los
  define el laboratorio (`display_text`), no se derivan en tiempo de render.
- El PDF del informe nunca es una URL pública. Se entrega por token firmado con expiración.
- La edad puede venir declarada (años/meses/días) cuando no hay fecha de nacimiento.

## Cómo trabajamos

- Una sesión = una fase de `docs/roadmap/`. No mezclar fases.
- **No entregar ZIP ni bundles de archivos.** Entregar el contenido de cada archivo por
  separado, en bloques de código, indicando la ruta exacta. Darwin aplica los cambios a mano.
- Cambios incrementales. Si un archivo existe, entregar sólo el diff o el bloque a sustituir,
  no el archivo completo reescrito.
- Antes de ejecutar, exponer las opciones y esperar decisión cuando haya más de un camino razonable.
- Reportar explícitamente lo que quedó **incompleto o faltante**. No cerrar con sólo lo positivo.
- Entorno: VS Code en Windows, PowerShell. **Verificar el venv activo como primer paso**
  de cualquier comando (hay múltiples Python instalados).

## Comandos base (PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.executable)"   # verificación obligatoria
python manage.py check
python manage.py makemigrations --dry-run
```

## Al cerrar cada sesión

1. Actualizar `docs/ESTADO.md` (qué se hizo, qué quedó pendiente, próximo paso).
2. Si se tomó una decisión estructural, agregar entrada a `docs/DECISIONES.md`.
3. Nunca dejar una fase a medias sin registrar el punto de corte.
