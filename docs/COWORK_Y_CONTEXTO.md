# Configuración de Cowork y Gestión de Contexto

El problema real: un proyecto de 18 fases no cabe en una ventana de contexto. Si el
contexto se reconstruye conversando, cada sesión desperdicia tiempo y el modelo toma
decisiones distintas a las de la sesión anterior. La solución no es una configuración
mágica: es que **el estado del proyecto viva en archivos, no en el historial del chat**.

---

## 1. Separación de proyectos

Ya existen proyectos separados para BioLifeLab, BioLifeVentas y Ginea. **Biolife va en su
propio proyecto de Cowork.** No mezclarlo con ninguno de los anteriores.

Razón concreta: los tres sistemas usan Django y PostgreSQL, y comparten vocabulario de
dominio ("paciente", "resultado", "informe"). Un modelo con los cuatro proyectos en
contexto confunde convenciones entre ellos — aplicará el patrón de BioLifeLab en Biolife
sin avisar. La separación evita esa contaminación.

**Instrucciones del proyecto Cowork** (campo de descripción): pegar un resumen de 10 líneas
apuntando a `CLAUDE.md`. No duplicar `CLAUDE.md` ahí: dos fuentes de verdad divergen.

---

## 2. Los tres archivos que sostienen el contexto

| Archivo | Naturaleza | Frecuencia de cambio | Tamaño objetivo |
|---|---|---|---|
| `CLAUDE.md` | Permanente | Raras veces | < 200 líneas |
| `docs/ESTADO.md` | Vivo | Cada sesión | < 100 líneas |
| `docs/DECISIONES.md` | Append-only | Cuando hay una decisión | crece |

**La separación importa.** Si el estado va dentro de `CLAUDE.md`, el archivo crece cada
sesión, se vuelve ruidoso y el modelo empieza a ignorar las reglas que están al final.
`CLAUDE.md` debe ser estable y corto para que se lea entero, siempre.

`DECISIONES.md` es append-only: nunca se edita una entrada pasada. Si una decisión se
revierte, se agrega una entrada nueva que la supersede. Así, cuando dentro de seis meses
alguien pregunte "¿por qué esquemas y no `tenant_id`?", la respuesta está escrita — y el
modelo no vuelve a proponer el cambio en cada sesión.

---

## 3. Protocolo de sesión

### Apertura (primer mensaje de la sesión)
```
Lee CLAUDE.md, docs/ESTADO.md y docs/roadmap/NN_nombre.md.
Confirma en 5 líneas: en qué fase estamos, qué quedó pendiente
de la sesión anterior y cuál es la primera tarea de hoy.
No escribas código todavía.
```

Esa confirmación de 5 líneas es la verificación barata de que el contexto se cargó bien.
Si el resumen está mal, se corrige ahí, antes de haber invertido una sesión escribiendo
código sobre premisas equivocadas.

### Durante
- **Una fase por sesión.** Si la fase se acaba y sobra ventana de contexto, es mejor cerrar
  sesión y abrir una nueva que empezar la siguiente fase con el contexto de la anterior encima.
- Si se necesita algo de otra fase, **copiarlo** al mensaje, no pedirle al modelo que lea
  medio repositorio.
- Tras cada tarea grande: "resume en 3 líneas el estado actual antes de continuar". Es un
  punto de control que detecta la deriva temprano.

### Cierre (último mensaje, sin excepción)
```
Actualiza docs/ESTADO.md con: fase actual, tareas completadas,
tareas pendientes, próximo paso concreto, y cualquier cosa que
quedó rota o a medio hacer.
Si tomamos alguna decisión estructural, agrégala a docs/DECISIONES.md.
```

**Si una sesión se corta sin cierre, la siguiente empieza por reconstruir el estado a mano.**
Ese es el costo de saltarse este paso, y es alto. Vale la pena dejar el cierre como un
paso ritual, aunque la sesión haya sido corta.

---

## 4. Elección de modelo por tarea

| Tarea | Modelo |
|---|---|
| Diseño de arquitectura, decisiones de modelo de datos | Opus |
| Fases 07, 10, 14, 16 (fórmulas, validación, sync, instrumentos) | Opus |
| Implementación de modelos, services, vistas, tests | Sonnet |
| Fixtures, siembra de catálogos, tareas repetitivas bien especificadas | Haiku |
| Redactar el `.md` de una fase nueva | Opus |

El archivo de fase existe justamente para que Sonnet y Haiku no tengan que tomar decisiones
de arquitectura. Si al ejecutar una fase el modelo económico empieza a preguntar cosas
estructurales, el problema no es el modelo: **el archivo de fase está incompleto**.
Corregir el `.md`, no improvisar en el chat.

---

## 5. Archivos del repo que conviene tener a mano en Cowork

Subir al proyecto (o mantener accesibles en el repositorio conectado):
- `CLAUDE.md`
- `docs/00_ARQUITECTURA.md`
- `docs/01_MODELO_DATOS.md`
- `docs/03_CONVENCIONES.md`
- `docs/04_HALLAZGOS_FORMATOS.md`
- Los dos Excel originales del laboratorio

**No subir:** capturas sueltas, borradores, versiones antiguas de los documentos. Todo
archivo extra en el proyecto compite por atención con los que sí importan.

---

## 6. Skill propio: `biolife-conventions`

Vale la pena crear un skill del proyecto que encapsule las convenciones. Se dispara solo
al trabajar en Biolife y evita repetir las reglas en cada prompt.

**Contenido mínimo:**
- Patrón Services & Selectors con ejemplos de firma
- Formato de entrega (bloques por archivo, sin ZIP, diffs para archivos existentes)
- Nomenclatura español/inglés
- Verificación de venv en PowerShell como primer paso
- Reglas de dominio no negociables (inmutabilidad de resultados validados, representante
  obligatorio para menores sin cédula, congelado de referencias al validar)

---

## 7. Prácticas que evitan pérdida de contexto

**Prefijos numéricos en todo.** `01_`, `02_`… El orden lexicográfico es el orden de
ejecución. Un modelo económico que ve `roadmap/` sabe por dónde va sin que se lo expliquen.

**Rutas completas siempre.** "El archivo de provisionamiento" es ambiguo;
`apps/tenants/services/provisioning.py` no lo es.

**Nada de "como acordamos antes".** Si se acordó, está en `DECISIONES.md`. Si no está
escrito, no se acordó.

**Un `TODO` en el código lleva la fase entre paréntesis:**
```python
# TODO(FASE 03): leer la zona horaria de TenantSettings
```
Así, al llegar a la fase 03, un `grep "FASE 03"` devuelve la lista de pendientes exacta.

**Commits pequeños y por fase.** `git log --oneline` se vuelve un resumen legible del
avance que se puede pegar en el contexto cuando haga falta.

---

## 8. Señales de que el contexto se está perdiendo

Si aparece alguna de estas, detener y recargar contexto desde los archivos:

- El modelo propone una estructura de carpetas distinta a la de `02_ESTRUCTURA_PROYECTO.md`
- Reaparece una decisión ya cerrada (por ejemplo, proponer `tenant_id` en vez de esquemas)
- Sugiere entregar un ZIP o reescribir archivos completos
- Empieza a escribir modelos en español o campos con convención distinta
- Mezcla fases: implementa `TenantSettings` durante la fase 01
- Pregunta algo que está respondido en `CLAUDE.md`

La recarga es barata: `"Lee CLAUDE.md y docs/ESTADO.md. Reinicia desde ahí."`
