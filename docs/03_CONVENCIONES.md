# 03 — Convenciones de Código

## Idioma

- **Código, nombres de modelos, campos y funciones: inglés.** `Patient`, `ReferenceRange`,
  `create_order`. Es lo estándar en Django y evita `Paciente.fecha_de_nacimiento` mezclado
  con `created_at`.
- **Datos, etiquetas de UI, `verbose_name`, choices visibles y mensajes: español.**
  `verbose_name = "Paciente"`, `("M", "Masculino")`.
- Docstrings y comentarios: español.
- Commits: español, formato convencional — `feat(patients): representante legal obligatorio para menores`.

## Nomenclatura

| Elemento | Convención | Ejemplo |
|---|---|---|
| Modelo | PascalCase singular | `ReferenceRange` |
| Campo booleano | `is_` / `has_` / `requires_` | `is_active`, `requires_fasting` |
| Fecha/hora | sufijo `_at` | `validated_at` |
| Fecha sin hora | sufijo `_date` | `birth_date` |
| Service de escritura | verbo_sustantivo | `create_order`, `validate_result` |
| Selector | sustantivo descriptivo | `pending_validation_orders` |
| Choices | constantes en `TextChoices` | `class Status(models.TextChoices)` |
| Test | `test_<qué>_<condición>_<esperado>` | `test_create_patient_minor_sin_representante_falla` |

## Reglas de código

1. **Type hints obligatorios** en services y selectors. Opcionales en el resto.
2. **Keyword-only arguments** en toda función pública de `services/` y `selectors/`.
3. **Ninguna vista toca el ORM.** Si una vista importa un modelo para consultarlo, es un bug.
4. **`transaction.atomic()`** en todo service que escriba más de un modelo.
5. **`select_related` / `prefetch_related` en selectors**, no en vistas ni templates.
6. **Excepciones de dominio**, no `ValueError` genérico:
   ```python
   from apps.core.exceptions import ApplicationError
   raise ApplicationError("El paciente menor sin cédula requiere un representante legal.")
   ```
   Un middleware las traduce a mensajes de usuario. El usuario nunca ve un traceback.
7. **Migraciones:** una por cambio lógico, con nombre descriptivo
   (`0007_patient_declared_age.py`). Nunca editar una migración ya aplicada en producción.
8. **Nada de `null=True` en `CharField`/`TextField`** salvo que se necesite distinguir
   "vacío" de "no informado". Usar `blank=True` con `default=""`.
9. **Decimales, no floats**, para todo valor de resultado clínico. `DecimalField`.
   Los formatos ya muestran el problema: `4.5999999999999996` en lugar de `4.6`.

## Tests

- `pytest` + `pytest-django` + `factory-boy`.
- Mínimo por fase: los services nuevos con sus casos borde. Cobertura no es la meta;
  cubrir las **reglas de negocio** sí.
- Todo test corre dentro de un tenant de prueba. Fixture `tenant_context` obligatoria.
- Tests de aislamiento entre tenants en `apps/tenants/tests/test_isolation.py`.

## Formato y linting

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "N", "UP", "DJ", "B", "C4", "SIM"]

[tool.ruff.lint.per-file-ignores]
"*/migrations/*" = ["E501", "N806"]
```

## Formato de entrega de código en sesión

Darwin aplica los cambios a mano. Por lo tanto:

- **Un bloque de código por archivo**, precedido de su ruta completa.
- Si el archivo ya existe: entregar **sólo** el fragmento que cambia, con 2–3 líneas de
  contexto arriba y abajo para ubicarlo. No reescribir el archivo entero.
- Si son más de 5 archivos, listar primero el índice de cambios y esperar confirmación.
- **Nunca** entregar ZIP, tarball ni "descarga todos los archivos".
- Al final de cada entrega: checklist de verificación y lista explícita de lo que **no**
  quedó implementado.

## Frontend

- Django Templates + HTMX para interactividad. Alpine.js sólo donde HTMX no alcance
  (captura de resultados con cálculo en vivo).
- Nada de build pesado de JS. La PWA necesita ser liviana: se usa en equipos viejos y
  conexiones malas.
- CSS: Tailwind vía CLI (sin Node en producción, se compila en CI).
- Variables CSS para el branding del tenant, inyectadas en `base_tenant.html`:
  ```html
  <style>:root{--color-primary:{{ settings.color_primary }};}</style>
  ```
