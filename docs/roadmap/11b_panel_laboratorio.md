# Fase 11b — Panel del laboratorio (configuración sin /admin)

**Depende de:** 11 · **Criterio de salida:** el administrador de un laboratorio configura
sus datos, usuarios y roles desde pantallas propias con el estilo de Biolife, sin `/admin`.

## Decisiones (Darwin, 2026-09-28)

- Razón social y RIF (en `tenants.Tenant`, esquema `public`) los edita **sólo el
  administrador del SaaS**; el laboratorio los ve, no los cambia.
- **Roles fijos:** los define Biolife; el laboratorio sólo los asigna. Un usuario puede
  tener **varios** roles (suma de permisos).
- Nuevo rol **Auxiliar de toma**: sólo *Muestras por tomar*, la orden sin montos, imprimir
  etiquetas, marcar tubos tomados o rechazados.
- Alta con **clave temporal** (la escribe o la genera el administrador; se muestra una sola
  vez) y cambio obligatorio en el primer ingreso. Sin correo por ahora.
- La ficha del examen con el estilo nuevo va en una **Fase 11c** aparte.

## Qué se hizo

- [x] *Laboratorio → Datos del laboratorio* (`/configuracion/laboratorio/`): identificación
  legal (sólo lectura), contacto, logo, color, siglas, texto propio del informe, días del
  enlace del QR, doble validación, etiquetas. Validaciones (siglas 2–6 letras, días 1–365,
  tamaños de etiqueta) y bitácora de qué cambió.
- [x] *Usuarios* (`/configuracion/usuarios/`): lista (roles, firma cargada, último
  ingreso, estado), alta con clave temporal, edición de datos, roles y datos
  profesionales, nueva clave temporal, desactivar/reactivar (nunca se borra).
  Reglas: siempre queda un administrador activo; nadie se quita a sí mismo el rol de
  administrador ni se desactiva. Todo queda en `AuditLog`.
- [x] *Roles* (`/configuracion/roles/`): tabla de qué hace cada rol, generada de las mismas
  tuplas que usan las vistas (no se desincroniza).
- [x] *Mi perfil* (`/cuenta/perfil/`, desde el nombre en el menú): datos, título,
  colegiatura, firma y sello con vista previa y «Quitar»; *Cambiar clave*
  (`/cuenta/clave/`). Middleware que obliga a cambiar la clave temporal.
- [x] Menú según los roles del usuario (`can`): cada quien ve sólo lo suyo. Inicio del
  auxiliar: acceso directo a *Muestras por tomar*; `/ordenes/` lo lleva siempre ahí.
  Orden sin tarjeta de cobro ni botones de resultados/informe para quien no los tiene.
- [x] El `/admin` de exámenes, tubos, lotes, perfiles y precios sigue en el menú como
  «Catálogo (provisional)» hasta la Fase 11c.
- [x] Tests: +10.

## Verificación en la máquina de Darwin

- [ ] `migrate_schemas` (accounts.0006: crea el rol en los laboratorios existentes).
- [ ] `pytest -q` · `ruff check .`
- [ ] Crear un usuario Auxiliar de toma, entrar con él (otro navegador o ventana
  privada), cambiar la clave, revisar que sólo ve *Muestras por tomar*.
- [ ] *Mi perfil*: cargar firma y sello; emitir un informe y verlos en cada página.
- [ ] *Datos del laboratorio*: cambiar Instagram o logo y verlo en un informe nuevo.

## No incluye

- Invitación por correo y «olvidé mi clave» (requiere configurar el envío de correos).
- Roles o permisos propios por laboratorio.
- Ficha del examen, tubos, perfiles y precios con estilo propio (Fase 11c).
- Zona horaria, formato de hora y separador decimal (quedan fijos: Caracas, 12 h, coma).
