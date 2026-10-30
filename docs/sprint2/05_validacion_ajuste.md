# Tarea 2.3 — Validación y ajuste de parámetros

Fecha: 2026-10-23. Estado: **pendiente de visto bueno**. Cuaderno: `notebooks/05_validacion_ajuste.ipynb` (ejecutado completo, sin errores).
Código nuevo: `src/robustness.py`, más `strategy_matrix` y `threshold_for_far` en `src/verification.py`.
**Solo se usó el conjunto de VALIDACIÓN; el de prueba no se cargó.** El plan de prueba quedó fijado antes, en `plan_evaluacion.md` (commit 512eecd).

Modelos: FaceNet VGGFace2 congelado (final) y control (a2) ResNet-18 ImageNet, usando los paquetes de la tarea 2.2.

## 1. Impostores internos

Se añadieron a validación 305 × 23 = **7 015** comparaciones de registradas contra la plantilla de **otra** registrada, además de las
6 456 externas. Archivo: `05_impostores_internos.csv`.

| | FaceNet VGGFace2 | Control (a2) |
|---|---|---|
| Genuina mínima / p1 / mediana | 0,607 / 0,639 / 0,867 | 0,622 / 0,682 / 0,927 |
| Impostora **externa** máxima (p99,9) | 0,511 (0,422) | 0,912 (0,883) |
| Impostora **interna** máxima (p99,9) | **0,583** (0,550) | 0,855 (0,779) |
| Margen genuina mín. − impostora máx.: solo externas / ext+int | 0,096 / **0,024** | −0,290 / −0,290 |
| EER externas / internas / ext+int | 0 / 0 / 0 % | 3,55 / 1,63 / 2,89 % |
| AUC ext+int | 1,0000 | 0,9962 |

**Lo que cambia con los internos (FaceNet):**
- La impostora más alta sube de 0,511 a 0,583, y el margen frente a la genuina mínima baja de 0,096 a 0,024.
- Los pares más difíciles son casi todos **Hrithik Roshan haciéndose pasar por Vijay Deverakonda**: 0,583, 0,576, 0,572, 0,568, 0,566 y 0,557, con 6 fotos distintas. Les sigue Akshay Kumar → Hrithik Roshan (0,553).
- Es el mismo par que ya era el más parecido entre plantillas en la tarea 2.2 (0,536).
- Las externas más altas son Elizabeth Olsen → Alexandra Daddario (0,511) y Henry Cavill → Zac Efron (0,490).
- Las genuinas más bajas son Zac Efron_56 (0,607), Hrithik Roshan_100 (0,610), Jessica Alba_101, Claire Holt_47 y Marmik_17 (0,653).

Archivos: `05_pares_dificiles_facenet.csv` y `figuras/05_pares_dificiles_facenet.png`.

## 2. Pruebas de robustez (solo validación)

Hay 17 perturbaciones más la condición limpia. Se aplican a **todas** las fotos de validación (genuinas e impostoras) sobre el recorte
160×160, sin volver a detectar el rostro:
- brillo ×0,6 y ×1,4; contraste ×0,5 y ×1,5;
- desenfoque gaussiano σ = 1, 2 y 3;
- JPEG con calidad 30, 15 y 8;
- rotación +5°, −10° y +15°;
- oclusión gris de la banda de los ojos (28–45 % de la altura), del tercio inferior, de la mitad lateral, y un parche de 48×48 en posición aleatoria con semilla.

Archivos: `05_robustez.csv`, `figuras/05_perturbaciones_ejemplo.png` y `figuras/05_robustez_puntuaciones.png`.

FaceNet, con el umbral propuesto (0,5514):

| Condición | Caída media de la genuina | Caída máx. | Genuina mín. | Impostora máx. | FAR | FRR |
|---|---|---|---|---|---|---|
| limpia | — | — | 0,607 | 0,583 | 0,052 % | 0,00 % |
| brillo ×0,6 / ×1,4 | 0,009 / 0,022 | 0,119 / 0,311 | 0,598 / 0,489 | 0,594 / 0,610 | 0,030 / 0,082 % | 0,00 / 0,98 % |
| contraste ×0,5 / ×1,5 | 0,015 / 0,013 | 0,141 / 0,136 | 0,533 / 0,485 | 0,590 / 0,602 | 0,030 / 0,089 % | 0,66 / 0,33 % |
| desenfoque σ1 / σ2 / σ3 | 0,010 / 0,050 / 0,130 | 0,091 / 0,195 / 0,412 | 0,614 / 0,516 / 0,356 | 0,587 / 0,619 / 0,595 | 0,082 / 0,045 / 0,022 % | 0,00 / 0,66 / **9,51 %** |
| JPEG q30 / q15 / q8 | 0,009 / 0,039 / 0,099 | 0,060 / 0,135 / 0,328 | 0,578 / 0,544 / 0,339 | 0,586 / 0,592 / 0,614 | 0,067 / 0,052 / 0,030 % | 0,00 / 0,33 / 4,26 % |
| rotación +5 / −10 / +15 | 0,003 / 0,018 / 0,037 | 0,079 / 0,142 / 0,192 | 0,595 / 0,521 / 0,482 | 0,592 / 0,623 / 0,643 | 0,082 / 0,067 / 0,097 % | 0,00 / 0,66 / 0,66 % |
| oclusión ojos | 0,239 | 0,527 | 0,253 | 0,612 | 0,045 % | **28,52 %** |
| oclusión inferior | 0,138 | 0,404 | 0,225 | 0,587 | 0,052 % | 7,87 % |
| oclusión lateral | 0,208 | 0,687 | 0,120 | 0,634 | 0,045 % | **23,28 %** |
| parche 48×48 | 0,077 | 0,372 | 0,324 | 0,614 | 0,030 % | 3,61 % |

Lectura:
- **Robusto** a cambios moderados de brillo y contraste, a desenfoque σ ≤ 2, a JPEG con calidad ≥ 15 y a rotaciones de hasta ±15°: FRR ≤ 1 %.
- **Sensible** a desenfoque fuerte (σ3: FRR 9,5 %), a JPEG muy agresivo (q8: 4,3 %) y, sobre todo, a **oclusiones**: ojos tapados 28,5 %,
  media cara 23,3 %, tercio inferior 7,9 %.
- Bajo **ninguna** perturbación se supera FAR 0,1 %, pero varias **elevan la impostora máxima** por encima de la limpia: rotación +15° llega a 0,643 y
  la oclusión lateral a 0,634. Por eso el umbral se fijó con la peor condición.
- El control (a2) es mucho menos robusto: con su umbral, el FRR es del 22 % con imágenes limpias y del 70–97 % con desenfoque σ2–σ3, JPEG q8/q15
  y oclusiones (tabla completa en el CSV).

## 3. Umbral: FAR objetivo con margen (no EER)

**Regla, definida antes de calcular:** FAR objetivo **≤ 0,1 %** sobre las 13 471 comparaciones impostoras de validación (externas + internas).
El umbral propuesto es el **mayor** de los umbrales que cumplen ese FAR en cada una de las 18 condiciones. Con 13 471 comparaciones,
0,1 % equivale a unas 13 aceptaciones y es medible; 0,01 % equivaldría a una sola y no sería estimable.

Archivos: `05_umbrales_candidatos.csv`, `05_umbrales_resumen.csv` y `05_umbral_propuesto.json`.

| FaceNet, umbral | Valor | FAR limpia | FRR limpia | FAR peor condición | FRR medio con perturbaciones | FRR peor (condición) |
|---|---|---|---|---|---|---|
| EER (limpia) | 0,6070 | 0,000 % | 0,00 % | 0,022 % | 7,68 % | 44,6 % (ojos) |
| Centro del hueco limpio | 0,5950 | 0,000 % | 0,00 % | 0,022 % | 6,94 % | 40,7 % (ojos) |
| FAR ≤ 0,1 % solo en limpia | 0,5469 | 0,097 % | 0,00 % | 0,119 % (rot +15) | 4,44 % | 26,6 % (ojos) |
| **FAR ≤ 0,1 % en la peor condición (PROPUESTO)** | **0,5514** | **0,052 %** | **0,00 %** | **0,097 %** (rot +15) | **4,78 %** | 28,5 % (ojos) |

**Umbral propuesto en validación para FaceNet: 0,5514.** Lo fija la condición rotación +15°.
- Hay **0,056** de margen hasta la genuina limpia más baja (0,607). El 1 % más bajo de las genuinas está en 0,639 o más.
- Queda **0,032 por debajo** de la impostora limpia más alta (0,583). Por eso, con imágenes limpias, **acepta 7 de 13 471 comparaciones impostoras**
  (FAR 0,052 %), **todas internas**: 6 son Hrithik Roshan → Vijay Deverakonda y 1 es Akshay Kumar → Hrithik Roshan. Ninguna externa supera el umbral.
  Las externas limpias quedan a 0,040 o más por debajo (máx. 0,511).
- La alternativa "centro del hueco" (0,595) no acepta ningún impostor limpio, pero sube el FRR medio con perturbaciones de 4,8 % a 6,9 % y el
  FRR con ojos tapados de 28,5 % a 40,7 %. Se descarta por la regla definida, aunque se deja anotada como opción más conservadora.

**Control (a2): umbral propuesto 0,8769** con la misma regla (lo fija rotación −10°). FAR limpia 0,074 %, FRR limpia **22,0 %**.
Con un FAR tan bajo el control rechaza a muchos usuarios legítimos. Es esperable, porque su EER es del 2,9 %.

Los dos umbrales quedan escritos en el `config.json` de su paquete, con `"umbral_estado": "propuesto en validación"`, la regla, el FAR/FRR
de validación y los márgenes. Esos archivos están en `models/`, fuera de git.

## 4. Coseno frente a euclídea; plantilla media frente a varias plantillas

Se aplicó la misma regla de umbral a cada variante. Archivo: `05_estrategias_plantilla.csv`.

| FaceNet, estrategia | EER limpia | Margen limpio | EER medio con perturbaciones | Umbral (regla) | FRR limpia | FRR medio con perturbaciones | FRR peor |
|---|---|---|---|---|---|---|---|
| **Media + coseno (actual)** | 0,000 % | 0,024 | 0,619 % | 0,5514 | 0,00 % | **4,78 %** | 28,5 % |
| Media + euclídea (renormalizada) | 0,000 % | 0,027* | 0,619 % | −0,9472 (−d) | 0,00 % | 4,78 % | 28,5 % |
| Media sin renormalizar + euclídea | 0,000 % | 0,029* | 0,584 % | −0,8827 (−d) | 0,00 % | 5,03 % | 30,5 % |
| Vecino más cercano (todas las fotos de train) | 0,257 % | −0,115 | 0,785 % | 0,6667 | 1,31 % | 6,96 % | 36,7 % |
| Media de los 3 cosenos más altos | 0,052 % | −0,051 | 0,699 % | 0,6323 | 0,66 % | 5,65 % | 30,5 % |
| k-means, 3 plantillas por usuario | 0,041 % | −0,106 | 0,652 % | 0,5955 | 0,33 % | 5,52 % | 32,5 % |

\* El margen está en unidades de distancia, así que no es comparable con el del coseno.

- **Coseno frente a euclídea:** con vectores normalizados, ‖e − t‖² = 2 − 2·cos. Por eso dan **exactamente** los mismos EER y FRR; solo cambia la escala
  del umbral. Sin renormalizar la media, la diferencia es mínima y algo peor con perturbaciones. **Se mantiene el coseno.**
- **Varias plantillas por usuario:** las tres variantes (vecino más cercano, top-3 y k-means) **empeoran** frente a la media. Con más plantillas
  aumentan las coincidencias impostoras altas, sobre todo entre registrados parecidos. **Se mantiene una plantilla media por usuario.**
- En el control (a2), las variantes con varias plantillas mejoran algo el EER limpio (de 2,89 a 2,62–2,74 %), pero apenas cambian el FRR
  con el umbral de la regla. Se mantiene también la media, para usar el mismo protocolo en ambos modelos.

## 5. Agregación de varios fotogramas (simulación para la tarea 2.6)

**Es una simulación, no hay video.** Un "video" de k fotogramas se simula con k fotos de validación distintas de la misma persona, cada una con
una degradación al azar (limpia, desenfoque σ1/σ2, JPEG q30, brillo ×0,6/×1,4, rotación +5/−10). Se generan grupos con semilla 42:
- 960 genuinos: 24 registradas × 40 grupos;
- 3 120 impostores: 360 externos y 2 760 internos.

Las fotos distintas varían más que los fotogramas consecutivos de un video real, así que el beneficio real de agregar será probablemente **menor**.
Archivo: `05_agregacion_fotogramas.csv`.

| FaceNet (umbral 0,5514) | FRR | FAR |
|---|---|---|
| 1 fotograma | 0,21 % (2/960) | 0,064 % (2/3 120) |
| 3 fotogramas: media de embeddings | 0,00 % | 0,096 % (3/3 120) |
| 3 fotogramas: media de puntuaciones | 0,00 % | 0,032 % (1/3 120) |
| 3 fotogramas: votación por mayoría | 0,00 % | 0,032 % (1/3 120) |
| 5 fotogramas: media de embeddings | 0,00 % | 0,160 % (5/3 120) |
| 5 fotogramas: media de puntuaciones | 0,00 % | 0,000 % |
| 5 fotogramas: votación por mayoría | 0,00 % | 0,000 % |

- Con FaceNet, agregar 3–5 fotogramas elimina los pocos rechazos genuinos. La **media de puntuaciones** y la **votación** además mantienen o bajan el FAR.
- La **media de embeddings** sube el FAR (5/3 120 con k = 5). Promediar embeddings acerca el vector al "centro" de la persona y cambia la
  distribución de puntuaciones, así que el umbral calibrado con una sola imagen deja de ser el adecuado.
- En el control (a2), la media de embeddings baja el FRR de 31 % a 0,1–2 %, por esa misma razón; la votación lo baja a 20–23 %.
- Las diferencias de FAR son de 1 a 5 aceptaciones sobre 3 120, así que **no son estadísticamente concluyentes**.
- **Propuesta para la tarea 2.6:** usar la **votación por mayoría** sobre los fotogramas con rostro detectado, porque usa el mismo umbral por
  fotograma calibrado aquí y es fácil de explicar. La media de puntuaciones se reportaría como dato complementario.

## Parámetros elegidos (resumen)

| Parámetro | Probado | Elegido |
|---|---|---|
| Métrica | coseno; euclídea (renormalizada y sin renormalizar) | **coseno** (equivalente a la euclídea normalizada) |
| Plantilla | media; vecino más cercano; top-3; k-means 3 | **media de los embeddings de train, renormalizada** |
| Umbral | EER (0,607); centro del hueco (0,595); FAR ≤ 0,1 % limpia (0,547); FAR ≤ 0,1 % peor condición (0,551) | **0,5514** (propuesto en validación) |
| FAR objetivo | — | **≤ 0,1 %** (externas + internas, en todas las condiciones) |
| Agregación de video | 1 fotograma; media de embeddings; media de puntuaciones; votación (k = 3, 5) | **votación por mayoría** (propuesta para 2.6) |
| Control (a2) | ídem | coseno, media, umbral **0,8769** |

## Limitaciones y observaciones

- **Validación sigue casi saturada con imágenes limpias**: los resultados limpios dependen de muy pocas comparaciones, las 7 impostoras internas
  por encima del umbral y las genuinas más bajas.
- **Riesgo de pares de registrados muy parecidos:** Hrithik Roshan y Vijay Deverakonda. En prueba conviene vigilar este par en las comparaciones internas.
- Las perturbaciones son **sintéticas** y se aplican sobre el recorte ya alineado. No reproducen bien la pose real, el contraluz ni el ruido de
  una cámara web, y tampoco el error del detector de rostro.
- La simulación de video usa fotos distintas, no fotogramas consecutivos.
- No hay detección de vida.
