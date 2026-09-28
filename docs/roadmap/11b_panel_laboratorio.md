# Fase 11b — Panel del laboratorio (configuración sin /admin)

**Depende de:** 11 · **Estado:** planificada (Darwin, 2026-09-27), no iniciada.
**Criterio de salida:** el administrador de un laboratorio configura todo desde pantallas
propias con el estilo de Biolife, sin entrar a `/admin`.

## Alcance propuesto (a confirmar al iniciar)

- Datos del laboratorio: razón social, RIF, nombre comercial, dirección, teléfono, correo,
  Instagram, web, logo, color, texto propio al pie del informe, días de validez del QR,
  doble validación, etiquetas.
- Usuarios: alta, baja (desactivar), roles, restablecer contraseña.
- Roles: ver permisos por rol (los de sistema) y ajustar los que el producto permita.
- Mi perfil profesional (cada bioanalista): título, colegiatura, firma y sello.
- Probablemente también la ficha del examen definitiva (TASKS: reemplaza al admin
  provisional) — decidir si entra aquí o en una 11c.

## Pendiente de decidir

- Si razón social y RIF (hoy en `tenants.Tenant`, esquema `public`) los edita el
  laboratorio o sólo el SuperAdmin.
- Qué permisos de rol son editables por el laboratorio.
