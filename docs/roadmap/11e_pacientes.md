# Fase 11e — Pacientes: ficha, historial y evolución

**Estado:** entregada (2026-09-28), pendiente de verificación en la máquina de Darwin.

**Depende de:** 11d · **Criterio de salida:** el paciente se busca, edita y consulta sin
`/admin`, y el laboratorio ve la evolución de sus resultados en el tiempo.

## Decisiones (Darwin, 2026-09-28)

- **Lista y ficha:** búsqueda; editar datos y representantes; historial de órdenes.
- **Sólo resultados validados** en la evolución, el panel y el PDF.
- **Gráfico SVG propio**, generado en el servidor, igual en pantalla y en el PDF: eje X =
  fecha de la orden, eje Y = valor, banda con el rango de referencia usado en cada fecha,
  puntos coloreados por marca y tooltip con fecha y valor.
- **Panel de tendencias** en la ficha, **PDF de evolución** para el médico, **valor
  anterior al cargar** con variación % y enlace a la evolución.
- **Antecedentes** configurables (tabla auxiliar) con parámetros sugeridos; los asignan
  **recepción y clínicos** (queda quién y cuándo).

## Qué se hizo

- [x] *Operación → Pacientes* (`/pacientes/`): búsqueda por cédula, nombre, apellido,
  teléfono o historia (varias palabras), n.º de órdenes y última visita.
- [x] Ficha: datos, antecedentes, representantes (agregar, principal, retirar), tendencias
  y órdenes. Editar datos (el código de historia no cambia; una edad declarada sin cambios
  conserva su fecha de declaración; documento repetido se rechaza).
- [x] Representantes: se reutiliza el existente con ese documento; un menor sin documento
  no puede quedarse sin representante; al retirar al principal pasa a otro.
- [x] Antecedentes (`patients.Antecedent`, `PatientAntecedent`): 8 sembrados (diabetes,
  hipertensión, anticoagulado, renal, dislipidemia, anemia, hepática, hiperuricemia) con
  sus parámetros; se editan en *Tablas auxiliares → Antecedentes* (administrador y
  bioanalista). Se ven en la ficha, al elegir el paciente en *Nueva orden*, en la orden y
  al cargar resultados.
- [x] Tendencias: primero lo que piden sus antecedentes, luego todo parámetro con 2+
  resultados; mini-gráfico, último valor con su marca, flecha y % contra el anterior.
- [x] Evolución (`/pacientes/<id>/evolucion/`): selector por examen, gráfico, tabla con
  variación y enlace a cada orden; PDF con los parámetros elegidos (membrete, datos del
  paciente, gráfico y tabla por parámetro; «Página X de Y»; aclara que no sustituye al
  informe firmado).
- [x] Captura de resultados: el valor anterior enlaza a su evolución y muestra la variación.
- [x] Menú: *Pacientes* reemplaza a «Nuevo paciente»; se quitó el último acceso a `/admin`
  (queda sólo la guía de estilo para el staff de Biolife).
- [x] Migraciones `patients.0002` (modelos) y `0003` (siembra en laboratorios existentes);
  la provisión de laboratorios nuevos también siembra los antecedentes.
- [x] Tests: +11 (`apps/patients/tests/test_patient_screens.py`).

## Verificación en la máquina de Darwin

- [ ] `migrate_schemas` (aplica `patients.0002` y `0003`), `check`, `makemigrations --check`.
- [ ] `pytest -q` → 298 passed · `ruff check .` limpio.
- [ ] Abrir un paciente con varias órdenes validadas: tendencias, evolución y PDF.
- [ ] Agregar un antecedente y verlo al crear una orden nueva para ese paciente.

## No incluye

- Unir pacientes duplicados, desactivar pacientes, importar historial externo.
- Parámetros codificados o de texto en la evolución (sólo numéricos).
