# Tarea 2.4 — Métricas y valores objetivo

Fecha: 2026-10-23. Estado: **objetivos pendientes de confirmar con el docente.**
Implementación: `src/evaluation.py` (punto de operación, intervalos, objetivos, desglose) y `src/metrics.py` (ROC, EER, AUC).
Se aplican en la tarea 2.5 según `plan_evaluacion.md`.

## Unidad de evaluación

Una **comparación** es un par (imagen de rostro, identidad que la persona dice tener). Su **puntuación** *s* es la similitud coseno entre el
embedding de la imagen y la plantilla de esa identidad. Con un umbral *t* fijo, la comparación se **acepta** si *s* ≥ *t* y se **rechaza** si *s* < *t*.

| Tipo de comparación | Definición | n en prueba |
|---|---|---|
| Genuina | foto de prueba de una registrada contra **su** plantilla | 299 |
| Impostora externa | foto de una impostora **no registrada** contra cada una de las 24 plantillas | 327 × 24 = 7 848 |
| Impostora interna | foto de prueba de una registrada contra la plantilla de **otra** registrada | 299 × 23 = 6 877 |
| Impostoras, todas | externas + internas | 14 725 |

Los tamaños salen de `splits.csv` (cuaderno 02), no de resultados.

## Matriz de confusión

|  | Decisión: aceptada | Decisión: rechazada |
|---|---|---|
| **Genuina** | TA (aceptación correcta) | FR (falso rechazo) |
| **Impostora** | FA (falsa aceptación) | TR (rechazo correcto) |

Se reporta con conteos absolutos, para cada modelo y punto de operación, y para impostoras externas, internas y todas.

## Definiciones

| Métrica | Definición | Objetivo propuesto |
|---|---|---|
| **FAR** (tasa de falsa aceptación) | FA / (FA + TR) = fracción de comparaciones impostoras aceptadas | **≤ 5 %** *(pendiente de confirmar con el docente)* |
| **FRR** (tasa de falso rechazo) | FR / (TA + FR) = fracción de comparaciones genuinas rechazadas | **≤ 10 %** *(pendiente de confirmar con el docente)* |
| **Exactitud balanceada** | [(1 − FAR) + (1 − FRR)] / 2 | **≥ 90 %** *(pendiente de confirmar con el docente)* |
| Exactitud simple | (TA + TR) / (TA + FR + FA + TR) | sin objetivo; solo se reporta |
| Proporción de comparaciones | n_genuinas / (n_genuinas + n_impostoras), y n_impostoras / n_genuinas | sin objetivo; se reporta junto a la exactitud |
| **Curva ROC** | (FAR(*t*), 1 − FRR(*t*)) para todos los umbrales *t*; resumen: AUC | **sin objetivo** (descriptiva) |
| **EER** | valor donde FAR(*t*) = FRR(*t*); se toma el punto de la ROC con \|FAR − FRR\| mínimo y EER = (FAR + FRR) / 2 | **sin objetivo** (descriptiva) |
| **Tiempo por verificación** | tiempo de punta a punta de una comparación (ver abajo); mediana y p95 | **≤ 3 s** *(pendiente de confirmar con el docente)* |

### Por qué exactitud balanceada

En prueba hay **14 725 comparaciones impostoras por 299 genuinas**, unas 49 impostoras por cada genuina. Las genuinas son solo el **2,0 %**
del total. Con esa proporción, la exactitud simple está dominada por las impostoras. Un sistema que **rechazara a todo el mundo** tendría una
exactitud simple del 98,0 % aunque no dejara entrar a ningún usuario legítimo; su exactitud balanceada sería del 50 %.
Por eso el objetivo "exactitud ≥ 90 %" se evalúa sobre la **exactitud balanceada**. La simple se reporta siempre al lado, junto con la proporción de comparaciones.

### Tiempo por verificación

Se mide de punta a punta: leer el JPG del disco, preprocesar, calcular el embedding y compararlo con la plantilla reclamada. Se dan la mediana y el
p95 de 60 repeticiones, tras 5 de calentamiento, en GPU (RTX 5060) y en CPU (i5-10400). El objetivo se compara con el **p95 en CPU**, que es el caso más
desfavorable de los medidos. En el dataset el rostro ya viene recortado, así que **no incluye la detección de rostro**. En la tarea 2.6 (video) se
mide aparte el tiempo con detección, y para el video el objetivo se aplica a ese tiempo total.

### Intervalos de confianza

- Para FAR y FRR se da el intervalo exacto de **Clopper-Pearson al 95 %**, a partir de los conteos.
- Con 0 errores, el límite superior equivale aproximadamente a la regla del tres (3/n).
- **Advertencia:** las comparaciones no son independientes, porque la misma foto se compara con 23 o 24 plantillas. Por eso los intervalos de FAR son
  **optimistas** (más estrechos de lo real), y se presentan solo como orientación.

## Cómo se declara que se cumple un objetivo *(propuesta)*

- Se usa el **umbral oficial** fijado en validación: FaceNet 0,5514 (`plan_evaluacion.md`).
- El valor que se compara con el objetivo es la **estimación puntual** en prueba, con **todas las impostoras (externas + internas)**. Externas e
  internas se reportan también por separado.
- El punto secundario de FaceNet (0,595) y el control (a2) (0,8769) se reportan con las mismas métricas, pero **no** sirven para declarar que se
  cumplen los objetivos.

Desglose obligatorio (regla 3 del plan), siempre con la advertencia de que cada grupo es **una sola persona**:

| Grupo | Métrica | n en prueba |
|---|---|---|
| Marmik, genuinas | FRR | 5 |
| Demás registradas, genuinas | FRR | 294 |
| Kashyap, impostora externa | FAR | 30 × 24 = 720 |
| Demás impostoras externas | FAR | 297 × 24 = 7 128 |
| Marmik haciéndose pasar por otra registrada | FAR | 5 × 23 = 115 |

## Relación con el umbral

El umbral oficial se eligió en validación con un criterio mucho **más estricto** que el objetivo: FAR ≤ 0,1 % en todas las condiciones, frente al
objetivo de FAR ≤ 5 %. Los objetivos de esta tarea son, por tanto, el mínimo aceptable para el proyecto, no el criterio con el que se fijó el umbral.
Si el docente pidiera objetivos más estrictos, se cambiarían aquí **antes** de ejecutar la prueba, sin tocar el umbral.
