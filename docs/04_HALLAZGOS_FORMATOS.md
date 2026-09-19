# 04 — Análisis de los Formatos Reales del Laboratorio

Fuente: `Perfiles.xlsx` y `Formato_de_resultados_-_Angelus.xlsx` (Laboratorio Angelus,
San Juan de los Morros, Guárico). Este documento es el insumo para sembrar el catálogo.

## Hojas encontradas

**Formato_de_resultados:** `Obs`, `TODOS`, `HC`, `QUIM`, `COAGUL`, `SEROLOG`, `SERO ESPE`,
`ORINA`, `HECES`, `HC+COAG`, `HIV+VDRL`, `ORINA+HECES.ofi`, `HC+ORINA`, `DEPURACIÓN`

**Perfiles:** `Obs`, `TODOS`, `PERFIL 20.ofi`, `ORINA+HECES.ofi`, `P. BÁSICO`,
`P. LIPÍDICO`, `P. HEPÁTICO`, `P. RENAL.ofi`, `P. PRE-OPERAT`, `P. PRECLAMPTICO`,
`P. PEDIÁTRICO`, `P. GLICÉMICO`, `BLANCO`

> Cada hoja es una plantilla de impresión distinta. En Biolife todas colapsan a
> **un solo motor de render** parametrizado por `Profile` → `Test` → `Parameter`.
> Ese es el valor central del producto frente al método actual.

---

## 1. Parámetros numéricos con rango cerrado

| Parámetro | Unidad | Referencia (literal) |
|---|---|---|
| HEMOGLOBINA | g/dL | 13,0 - 15,0 g/dL |
| HEMATOCRITO | % | 41 - 50 % |
| CHCM | % | 31 - 33 % |
| GLÓBULOS BLANCOS | /mm3 | 4.500 - 10.000/mm3 |
| NEUTRÓFILOS | % | 50 - 70 % |
| LINFOCITOS | % | 20 - 40 % |
| EOSINÓFILOS | % | 0 - 2 % |
| PLAQUETAS | /mm3 | 150.000 - 450.000/mm3 |
| VSG | mm/h | 0 - 15 mm/h |
| GLICEMIA | mg/dL | 70 - 100 *o* 70 - 110 mg/dL ⚠️ |
| ÚREA | mg/dL | 10 - 30 *o* 20 - 45 mg/dL ⚠️ |
| CREATININA | mg/dL | 0,70 - 1,20 *o* 0,50 - 1,30 mg/dL ⚠️ |
| ÁCIDO ÚRICO | mg/dL | 3,4 - 70 ⚠️ *o* 3,0 - 7,0 mg/dL |
| CALCIO | mg/dL | 8,6 - 10,0 mg/dL |
| FÓSFORO | mg/dL | 2,9 - 4,7 mg/dL |
| PROTEÍNAS TOTALES | g/dL | 6,0 - 8,0 g/dL |
| ALBÚMINA | g/dL | 3,5 - 5,0 g/dL |
| GLOBULINAS | g/dL | 2,0 - 3,5 g/dL |
| REL. ALB/GLO | — | 1,2 - 2,2 |
| BILIRRUBINA TOTAL | mg/dL | 0,10 - 1,20 *o* 0,20 - 1,00 ⚠️ |
| BILIRRUBINA DIRECTA | mg/dL | 0,05 - 0,30 *o* 0,01 - 0,50 ⚠️ |
| BILIRRUBINA INDIRECTA | mg/dL | 0,20 - 0,80 mg/dL |
| LDH | IU/L | 90 - 510 IU/L |
| FIBRINÓGENO | mg/dL | 200 - 400 mg/dL |
| RAZÓN PT / INR | — | 0,80 - 1,20 |
| DENSIDAD (orina) | — | 1008 - 1025 |
| pH (orina) | — | 5,0 - 7,0 |

> ⚠️ **Inconsistencias detectadas entre hojas.** El mismo parámetro tiene rangos distintos
> según la plantilla, y "ÁCIDO ÚRICO: 3,4 - 70 mg/dL" es con alta probabilidad un error de
> tipeo por 7,0. Esto es exactamente el problema que el sistema elimina: **un rango, una
> fuente de verdad**. Antes de sembrar el catálogo hay que pedirle al laboratorio que
> confirme cuál es el valor correcto de cada uno de los seis parámetros marcados.

## 2. Límites abiertos

| Parámetro | Referencia |
|---|---|
| COLESTEROL TOTAL | MENOR A 200 mg/dL |
| TRIGLICÉRIDOS | MENOR A 150 mg/dL |
| LDL-c | MENOR A 100 mg/dL |
| VLDL-c | MENOR A 30 mg/dL |
| HDL-c | MAYOR 40 mg/dL |
| TGO (ASAT) / TGP (ALAT) | MENOR A 40 *o* 35 U/L ⚠️ |
| ALP | MENOR A 120 U/L |
| GGT | MENOR A 40 U/L |
| Índice de Castelli I | MENOR A 4,5 |
| Índice de Castelli II | MENOR A 2,5 |

## 3. Tolerancia

| Parámetro | Referencia |
|---|---|
| DIFERENCIA PTT (paciente − control) | ± 6,0 segundos |

## 4. Parámetros calculados — fórmulas a implementar

```
CHCM                  = HEMOGLOBINA / HEMATOCRITO * 100
GLOBULINAS            = PROTEINAS_TOTALES - ALBUMINA
REL_ALB_GLO           = ALBUMINA / GLOBULINAS
BILIRRUBINA_INDIRECTA = BILIRRUBINA_TOTAL - BILIRRUBINA_DIRECTA
VLDL                  = TRIGLICERIDOS / 5
LDL                   = COLESTEROL_TOTAL - HDL - VLDL        # Friedewald
CASTELLI_I            = COLESTEROL_TOTAL / HDL
CASTELLI_II           = LDL / HDL
PT_RAZON              = PT_PACIENTE / PT_CONTROL
INR                   = PT_RAZON ** ISI
PTT_DIFERENCIA        = PTT_PACIENTE - PTT_CONTROL
SUPERFICIE_CORPORAL   = 0.007184 * (@talla ** 0.725) * (@peso ** 0.425)   # DuBois
DEPURACION_SIN_CORR   = (CREAT_ORINA * @volumen_orina_24h) / (CREAT_SERICA * 1440)
DEPURACION_CORREGIDA  = DEPURACION_SIN_CORR * 1.73 / SUPERFICIE_CORPORAL
VOLUMEN_MINUTO        = @volumen_orina_24h / 1440
CREAT_URINARIA_24H    = CREAT_ORINA * @volumen_orina_24h / 100000
```

Variables con `@` provienen de la **orden** (peso, talla, volumen de orina 24 h), no del
catálogo. Ver `Order.weight_kg`, `Order.height_cm`, `Order.urine_volume_24h_ml`.

> Verificado contra los datos de la hoja `DEPURACIÓN`: creatinina sérica 0,79 mg/dL,
> creatinina en orina 14,9 mg/dL, volumen 5030 mL, talla 165 cm, peso 62 kg →
> superficie corporal 1,6857 m², depuración sin corregir 65,88 mL/min, corregida 67,61 mL/min.
> Las fórmulas de arriba reproducen esos números.

## 5. Conjuntos de opciones codificadas

```
ABUNDANCIA          AUSENTES · ESCASAS · MODERADAS · ABUNDANTES
ABUNDANCIA_SING     AUSENTE · ESCASA · MODERADA · ABUNDANTE
NEG_POS_CRUCES      NEGATIVO · TRAZAS · POSITIVO (+) · POSITIVO (++) ·
                    POSITIVO (+++) · POSITIVO (++++)
NEG_POS             NEGATIVO · POSITIVO
PRESENCIA           AUSENTES · PRESENTES
REACTIVIDAD         NO REACTIVO · REACTIVO
UROBILINOGENO       NORMAL · AUMENTADO
COLOR_ORINA         AMARILLO · ROJO · ÁMBAR · TRANSPARENTE · CLARO
ASPECTO_ORINA       CLARO · LIGERAMENTE TURBIO · TURBIO
OLOR_ORINA          SUI-GENERIS · AMONIACAL
DENSIDAD_ORINA      1010 · 1015 · 1020 · 1025 · 1030       (lista cerrada, tira reactiva)
PH_ORINA            5 · 6 · 6,5 · 7 · 8 · 9                (lista cerrada, tira reactiva)
COLOR_HECES         MARRÓN · AMARILLO · VERDE · ROJO · NEGRO
CONSISTENCIA_HECES  BLANDA · DURA · LÍQUIDA
ASPECTO_HECES       HETEROGÉNEO · HOMOGÉNEO
OLOR_HECES          FECAL · FÉTIDO
REACCION_HECES      ÁCIDA · ALCALINA
MICROBIOTA          NORMAL · AUMENTADA
EDAD_UNIDAD         AÑOS · AÑO · MESES · MES · DÍAS · DÍA
```

> Nota sobre `DENSIDAD_ORINA` y `PH_ORINA`: el formato los maneja como lista desplegable
> porque la tira reactiva sólo lee esos escalones. Se modelan como `CODED` con
> `numeric_equivalent` poblado, de modo que el marcado alto/bajo siga funcionando.

## 6. Títulos / diluciones

**PCR (proteína C reactiva), aglutinación látex semicuantitativo**
```
NEGATIVO: Menor a 6,0 mg/L      ordinal 0   equiv —
POSITIVO: 1/1  = 6,0   mg/L     ordinal 1   equiv 6
POSITIVO: 1/2  = 12    mg/L     ordinal 2   equiv 12
POSITIVO: 1/4  = 24    mg/L     ordinal 3   equiv 24
POSITIVO: 1/8  = 48    mg/L     ordinal 4   equiv 48
POSITIVO: 1/16 = 96    mg/L     ordinal 5   equiv 96
POSITIVO: 1/32 = 192   mg/L     ordinal 6   equiv 192
POSITIVO: 1/64 = 384   mg/L     ordinal 7   equiv 384
POSITIVO: 1/128 = 768  mg/L     ordinal 8   equiv 768
POSITIVO: 1/256 = 1536 mg/L     ordinal 9   equiv 1536
```

**VDRL, floculación**
```
NO REACTIVO · REACTIVO: 2 Dils · 4 · 8 · 16 · 32 · 64 · 128 · 256 Dils
```

> ⚠️ La hoja `P. PEDIÁTRICO` muestra "NEGATIVO: Menor a 0,6 mg/dL" mientras el resto usa
> "Menor a 6,0 mg/L". Son la misma cantidad en distintas unidades, pero el texto impreso
> es inconsistente. Confirmar con el laboratorio cuál se estandariza.

## 7. Escala interpretativa (`range_type = INTERPRETIVE`)

**Procalcitonina**, inmunocromatografía semicuantitativa:
```json
[
  {"max": 0.5,  "text": "Posible infección localizada."},
  {"min": 0.5,  "text": "Posible infección sistémica."},
  {"min": 2.0,  "text": "Probable infección sistémica (sepsis)."},
  {"min": 10.0, "text": "Alta probabilidad de shock séptico."}
]
```

## 8. Catálogo de hallazgos parasitarios (`MULTI_CATALOG`)

```
NO SE OBSERVARON FORMAS PARASITARIAS.
Blastocystis spp. forma vacuolar.
Blastocystis spp. forma granular.
QUISTES DE Giardia intestinalis.
QUISTES DE Entamoeba histolytica/E. dispar.
QUISTES DE Entamoeba coli.
QUISTES DE Endolimax nana.
QUISTES Y TROFOZOÍTOS DE Giardia intestinalis.
QUISTES Y TROFOZOÍTOS DE Entamoeba histolytica/E. dispar.
QUISTES Y TROFOZOÍTOS DE Entamoeba coli.
QUISTES Y TROFOZOÍTOS DE Endolimax nana.
HUEVOS DE Enterobius vermicularis.
HUEVOS DE Ascaris lumbricoides.
HUEVOS DE Anquilostomídeos.
HUEVOS Y LARVAS DE Enterobius vermicularis.
HUEVOS Y LARVAS DE Ascaris lumbricoides.
LARVAS DE Strongyloides stercoralis.
```
> La nomenclatura científica lleva cursiva en el informe impreso. El campo `value` debe
> admitir marcado mínimo (`<i>`) o guardar `scientific_name` aparte. **Decidir en Fase 05.**

## 9. Observaciones predefinidas (`ObservationTemplate`)

| Sección | Textos |
|---|---|
| GENERAL | VALOR VERIFICADO · VALORES VERIFICADOS |
| HEMATOLOGÍA | HEMATOLOGÍA COMPLETA VERIFICADA MEDIANTE TÉCNICA MANUAL · …VERIFICADA CON UNA SEGUNDA MUESTRA · CONTAJE Y FÓRMULA LEUCOCITARIA VERIFICADOS · CONTAJE PLAQUETARIO VERIFICADO |
| QUÍMICA | SUERO ICTÉRICO · SUERO LIPÉMICO |
| ORINA | SE SUGIERE REPETIR UROANÁLISIS MEJORANDO LA TOMA DE MUESTRA · HEMATÍES: EUMÓRFICOS __ % / DISMÓRFICOS __ % |
| HECES | SE SUGIERE REALIZAR EXAMEN DE HECES SERIADO |
| INMUNOLOGÍA | SE SUGIERE REALIZAR β-HCG CUANTIFICADA · SE SUGIERE CONFIRMAR RESULTADO MEDIANTE FTA-Abs · SE SUGIERE CONFIRMAR FACTOR Rh MEDIANTE Du |

## 10. Métodos analíticos que se imprimen

```
Aglutinación látex semicuantitativo
Inmunocromatografía cualitativa
Inmunocromatografía semicuantitativa
Floculación
Colorimétrico Jaffé modificado
```

## 11. Elementos del encabezado y pie del informe

**Encabezado:** logo · razón social · RIF · teléfono · dirección ·
nombre del paciente · C.I. (prefijo V-/E-) · edad + unidad · género · dirección/localidad ·
teléfono · fecha · N.º de orden.

**Pie:**
```
Los resultados requieren firma y sello húmedo para su legalidad.
El laboratorio es garante de la fase preanalítica de las muestras
recolectadas por el personal del mismo.
```
más teléfono e Instagram. Todo configurable en `TenantSettings`.

## 12. Catálogo de localidades (Guárico y Aragua)

ALTAGRACIA DE ORITUCO · CALABOZO · CAMATAGUA · CANTAGALLO · DOS CAMINOS · EL SOMBRERO ·
EL TOCO · LAS MERCEDES DEL LLANO · LAS MINAS · ORTIZ · PARAPARA · PIRITU · SAN CASIMIRO ·
SAN FRANCISCO DE TIZNADOS · SAN JOSÉ DE TIZNADOS · SAN JUAN DE LOS MORROS ·
SAN SEBASTIÁN DE LOS REYES · TAGUAY · VALLE DE LA PASCUA · VALLES DE TUCUTUNEMOS · VILLA DE CURA

> Se carga como `Locality` en el esquema público, con estado y municipio. Ampliar a
> cobertura nacional antes de vender al segundo tenant.

---

## Lo que los formatos NO revelan y hay que preguntar al laboratorio

1. Rangos de referencia **pediátricos y neonatales** reales. La hoja `P. PEDIÁTRICO`
   imprime rangos de adulto sobre un paciente "RN" — es un error del método actual, no un
   dato aprovechable.
2. Rangos diferenciados por **sexo**. Los formatos muestran hemoglobina 13,0–15,0 tanto en
   hojas masculinas como femeninas, lo cual es clínicamente incorrecto (mujer: 12,0–16,0).
3. Valores **críticos / de alerta** (pánico) que obligan a notificación inmediata.
4. El valor de **ISI** del lote de tromboplastina en uso (necesario para el INR).
5. Precios de exámenes y perfiles.
6. Qué analizadores tiene el laboratorio, marca y modelo.
7. Si requieren **doble validación** (técnico carga, bioanalista valida) o una sola.
