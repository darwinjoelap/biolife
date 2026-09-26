# Fase 08c — Consolidación

**Depende de:** 08b · **Modelo usado:** Opus · **Origen:** revisión de estado pedida por Darwin
antes de la Fase 09.

## Qué se hizo

- [x] **Un laboratorio nuevo nace listo:** `provision_tenant(seed_catalog=True)` siembra
  catálogo base (rangos y fórmulas), perfiles, monedas y lista GENERAL vacía.
  `crear_laboratorio --sin-catalogo` lo omite.
- [x] **Rangos de lípidos:** migración `catalog.0006` pasa colesterol, triglicéridos y HDL de
  condición AYUNO a NINGUNA (el ayuno es requisito del examen, no otro rango). La siembra ya
  los crea así.
- [x] **CI:** `.github/workflows/ci.yml` (Postgres 16, Python 3.13): ruff, migraciones al día,
  pytest y prueba de aislamiento entre tenants, en cada push a `main` y en cada PR.
- [x] **`scripts/check_tenant_isolation.py` reparado:** usaba `auth.User` (reemplazado en la
  Fase 02) y la firma vieja de `provision_tenant()`; no funcionaba desde la Fase 02.
- [x] **Avisos eliminados:** `CheckConstraint(check=…)` → `condition=` (sin migración);
  pytest ya no intenta recolectar el modelo `Test` ni avisa por `staticfiles/`.
- [x] Tests: +2 (provisión con y sin catálogo).

## No incluye

- Dividir `catalog/models.py` en paquete (392 líneas; se hará cuando crezca en la Fase 10).
- Decidir el destino de `demo_tres` y borrar `Claude outputs/` (manual).
