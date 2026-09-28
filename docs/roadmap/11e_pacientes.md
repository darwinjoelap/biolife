# Fase 11e — Pacientes: ficha, historial y evolución

**Depende de:** 11d · **Estado:** planificada (Darwin, 2026-09-28), no iniciada.
**Criterio de salida:** el paciente se busca, edita y consulta sin `/admin`, y el
laboratorio ve la evolución de sus resultados en el tiempo.

## Decisiones (Darwin, 2026-09-28)

- **Lista y ficha:** búsqueda por cédula/nombre/teléfono; editar datos y representantes;
  historial de órdenes del paciente.
- **Evolución por parámetro:** gráfico con eje X = fecha de toma y eje Y = valor, banda
  sombreada con el rango de referencia vigente en cada fecha, puntos marcados si
  alto/bajo/crítico, y tabla de valores debajo con la variación contra el anterior.
- **Panel de tendencias:** en la ficha, mini-gráficos de los parámetros numéricos con dos
  o más resultados validados, flecha ↑↓ y último valor; clic abre el gráfico grande.
- **Valor anterior al cargar:** en la captura de resultados, el resultado previo del
  paciente y su fecha junto a cada campo (ayuda a detectar errores).
- **PDF de evolución** para el médico, con membrete del laboratorio.
- **Antecedentes con parámetros sugeridos:** etiquetas en la ficha (diabético, hipertenso,
  anticoagulado, embarazada…) configuradas por el laboratorio; cada antecedente sugiere
  qué vigilar (diabético → glicemia, HbA1c; anticoagulado → INR). Se ven también al
  recibir la orden.

## Por decidir al iniciar

- Sólo resultados **validados** en la evolución (propuesta: sí; los no validados, marcados).
- Librería del gráfico (propuesta: SVG propio en servidor para pantalla y PDF, sin JS).
- Si el antecedente se registra como dato clínico del paciente con fecha y quién lo cargó.
