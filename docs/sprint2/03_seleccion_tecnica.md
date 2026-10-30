# Tarea 2.1 — Selección de la técnica de modelado

Fecha: 2026-10-23. Estado: **pendiente de visto bueno**. Cuaderno: `notebooks/03_seleccion_tecnica.ipynb` (ejecutado completo, sin errores).
Código: `src/models.py`, `src/verification.py`, `src/metrics.py`. **El conjunto de prueba no se cargó ni se usó.**

## Variantes comparadas

| Variante | Qué es | Pesos / entrenamiento |
|---|---|---|
| (a1) CNN propia | 5 bloques conv + embedding de 128, entrenada **desde cero** como clasificador de las 24 registradas | 2,39 M parámetros, 40 épocas, 112 s en GPU |
| (a2) ResNet-18 por transferencia | ResNet-18 preentrenada en **ImageNet** (sin rostros), ajustada completa como clasificador de las 24 registradas | `resnet18-f37072fd.pth` (torchvision, IMAGENET1K_V1); 11,19 M parámetros, 40 épocas, 53 s en GPU |
| (b1) FaceNet VGGFace2 | InceptionResnetV1 preentrenada en rostros, **sin reentrenar** | `20180402-114759-vggface2.pt` |
| (b2) FaceNet CASIA-WebFace | ídem | `20180408-102900-casia-webface.pt` |
| (c) LBPH | línea base clásica, OpenCV `cv2.face`, radio 1, 8 vecinos, rejilla 8×8, escala de grises 160×160 | sin entrenamiento |

**Fuente de los pesos FaceNet:** facenet-pytorch 2.6.0, publicados en https://github.com/timesler/facenet-pytorch/releases.
Son una conversión a PyTorch de los modelos de David Sandberg (https://github.com/davidsandberg/facenet). Se guardan en `models/torch_hub/`
(ignorado por git).

**Hiperparámetros de (a1) y (a2), fijos y no ajustados:**
- AdamW con OneCycle, lote 64, label smoothing 0,1, weight decay 5e-4.
- Tasa de aprendizaje 1e-3 en (a1) y 3e-4 en (a2).
- Aumento de datos: espejo, rotación ±10°, escala 0,9–1,1, traslación ±6 % y brillo/contraste ±20 %.
- Se usa la última época. La validación solo sirvió para dibujar la curva; no se eligió época con ella.

**Protocolo (validación):**
- **Plantilla:** media de los embeddings L2-normalizados de las fotos de *train* de cada registrada. En LBPH se usa el vecino más cercano entre sus fotos de train, que es la regla del propio LBPH.
- **Puntuación:** similitud coseno. La distancia euclídea sobre vectores normalizados es equivalente (d² = 2 − 2·cos) y da la misma ROC.
- **Comparaciones genuinas:** 305, cada foto de validación de una registrada contra su plantilla.
- **Comparaciones impostoras:** 269 × 24 = **6 456**, las fotos de Andy Samberg, Henry Cavill y Elizabeth Olsen contra las 24 plantillas.
- **Complementario:** 305 × 23 = 7 015 impostores internos (registradas contra plantillas ajenas).
- **Tiempo por verificación:** de punta a punta (leer el JPG, preprocesar, extraer el vector y comparar con la plantilla). Es la mediana de 60 repeticiones tras calentar. **No incluye detección de rostro**, porque Faces ya viene recortado; la detección se medirá en la tarea 2.6.

## Resultados en VALIDACIÓN

Archivo: `03_comparacion_validacion.csv`. FAR y FRR se dan en el umbral del EER.

| Variante | EER | IC 95 % EER (bootstrap) | AUC | Umbral | FAR | FRR | EER internas | t GPU (ms) | t CPU (ms) |
|---|---|---|---|---|---|---|---|---|---|
| (a1) CNN propia | 4,85 % | 3,93–6,57 % | 0,9892 | 0,550 | 4,79 % | 4,92 % | 2,87 % | 4,9 | 20,0 |
| (a2) ResNet-18 ImageNet | 3,55 % | 2,63–5,33 % | 0,9929 | 0,779 | 3,50 % | 3,61 % | 1,63 % | 6,5 | 41,6 |
| **(b1) FaceNet VGGFace2** | **0,00 %** | 0,00–0,00 % | **1,0000** | 0,607 | **0,00 %** | **0,00 %** | **0,00 %** | 32,8 | 71,0 |
| (b2) FaceNet CASIA-WebFace | 0,63 % | 0,25–1,13 % | 0,9999 | 0,422 | 0,60 % | 0,66 % | 1,21 % | 36,1 | 75,2 |
| (c) LBPH | 33,52 % | 30,17–36,39 % | 0,7171 | −33,09 (−χ²) | 33,60 % | 33,44 % | 28,55 % | — | 25,4 |

Notas sobre (b1):
- **Separa perfectamente** genuinas de impostoras. La genuina más baja es 0,607 (Zac Efron_56); la impostora más alta es 0,511
  (Elizabeth Olsen_7 contra la plantilla de Alexandra Daddario) y la interna más alta 0,583. El margen es de 0,096 frente a impostoras externas y
  de solo 0,024 frente a internas.
- Con 0 errores, el bootstrap da un intervalo degenerado (0–0). Un límite más honesto es la **regla del tres**: con 0 fallos en 305 genuinas,
  el FRR real es ≤ ≈ 1,0 % (95 %); con 0 en 6 456 impostoras, el FAR real es ≤ ≈ 0,05 %. **Validación está saturada** para esta variante.
- El "umbral del EER" (0,607) coincide con la genuina más baja, es decir, está en el borde del hueco, no en su centro. **No es un buen umbral
  operativo**; el umbral definitivo se fijará en la tarea 2.3 (p. ej. por un FAR objetivo o el centro del margen), siempre con validación.
- Todas las variantes CNN cumplen holgadamente el tiempo objetivo (≤ 3 s), incluso en CPU.

Figuras:
- `figuras/03_det_validacion.png`: curvas DET (FAR contra FRR), lineal y con FAR en escala log.
- `figuras/03_roc_validacion.png`: curvas ROC.
- `figuras/03_distribucion_puntuaciones.png`: histogramas de puntuaciones genuinas e impostoras con el umbral del EER.
- `figuras/03_curvas_entrenamiento_a.png`: pérdida y exactitud de train/val de (a1) y (a2), y `03_historial_entrenamiento_a.csv`.
  (a1) llega a 0,999 en train y 0,934 en val (clasificación de 24 clases); (a2) llega a 1,000 y 0,970. Hay algo de sobreajuste en ambas.

## Chequeo del sesgo de famosos (validación)

Archivo: `03_chequeo_sesgo_famosos.csv`; FRR por identidad en `03_frr_por_identidad_validacion.csv`.

| Variante | Marmik: genuinas aceptadas | FRR Marmik | FRR famosos | Mediana genuina Marmik / famosos | Marmik como impostora (115 intentos): FAR | Famosos como impostores internos: FAR |
|---|---|---|---|---|---|---|
| (a1) CNN propia | 5/5 | 0 % | 5,0 % | 0,915 / 0,900 | 0 % | 0,86 % |
| (a2) ResNet-18 ImageNet | 5/5 | 0 % | 3,7 % | 0,904 / 0,928 | 0 % | 0,10 % |
| (b1) FaceNet VGGFace2 | 5/5 | 0 % | 0,0 % | 0,851 / 0,868 | 0 % | 0,00 % |
| (b2) FaceNet CASIA | 5/5 | 0 % | 0,7 % | 0,793 / 0,824 | 0 % | 3,00 % |
| (c) LBPH | 2/5 | 60 % | 33,0 % | −33,2 / −30,8 | 1,7 % | 21,9 % |

Lectura:
- Con (b1), las genuinas de Marmik quedan algo por debajo de la mediana de los famosos (percentil 40). Una de ellas (Marmik_17, 0,653) es la
  5.ª genuina más baja de las 305, pero todas superan el umbral. Con 5 fotos es **solo una señal, no una prueba**.
- **En validación no hay impostoras no famosas**: Kashyap está reservada para prueba y no se tocó. El sustituto fue usar a Marmik como
  impostora interna contra las otras 23 plantillas: 0 de 115 aceptadas con todas las variantes CNN.
  **El chequeo real con una impostora no famosa (Kashyap) solo podrá hacerse en la tarea 2.5.**

## Limitación: posible sesgo de famosos

VGGFace2 y CASIA-WebFace se construyeron con fotos de **celebridades** descargadas de internet. Es **muy probable** que muchas de las 29 identidades
famosas de este dataset, o fotos muy parecidas, estuvieran en el entrenamiento de (b1) y (b2). No se ha verificado identidad por identidad.
Si fuera así, (b1) habría "memorizado" parte de estas caras y su EER del 0 % sería **optimista** respecto a usuarios desconocidos, como los de
una aplicación real. En cambio, (a2) parte de ImageNet (objetos, no rostros) y (a1) parte de cero: sus resultados no tienen este sesgo,
aunque tienen otro (se entrenan con muy pocas fotos de las mismas 24 personas).

## Decisión

**Se elige (b) FaceNet InceptionResnetV1 con pesos VGGFace2 + embeddings + similitud coseno**, frente a la plantilla del usuario.
- Es la que mejor resultado tiene en validación con diferencia: EER 0,00 % frente a 0,63 % de CASIA, 3,55 % de ResNet-18 y 4,85 % de la CNN propia.
  Además separa también los impostores internos.
- Cumple el tiempo: unos 33 ms en GPU y unos 71 ms en CPU por verificación, sin contar la detección.
- Es la única de las CNN que **no necesita reentrenarse** al registrar un usuario nuevo, porque basta con calcular su plantilla. (a1) y (a2) son
  clasificadores de 24 clases y sus embeddings solo están optimizados para estas 24 personas; esa es una desventaja estructural para un sistema
  de verificación abierto.
- LBPH queda como línea base: EER 33,5 %, muy por debajo de las CNN.
- Coincide con la preferencia inicial (b), pero la decisión se apoya en los números de la tabla.

Matices que se trasladan a las tareas siguientes:
1. Como validación está saturada para (b1), en la tarea 2.3 hay poco que ajustar. Lo principal es **fijar el umbral** con un criterio
   razonado, porque el umbral del EER queda en el borde del margen.
2. **Propuesta (requiere tu decisión):** evaluar en prueba, además de (b1), la variante **(a2) ResNet-18 ImageNet como control del sesgo de famosos**.
   Si (b1) empeora con Kashyap mucho más que (a2), eso indicaría memorización de famosos. Se evaluaría una sola vez, con su umbral fijado también en validación.

## Problemas encontrados

- No hay Node.js en el equipo, así que no se pudo ejecutar el validador de paleta de la guía de visualización. Se usaron los 5 colores
  categóricos por defecto ya validados de la guía, con distinto estilo de línea como segunda codificación.
- La extracción de histogramas LBPH más la distancia χ² tardó 275 s en total (bucle en NumPy). No afecta al tiempo por verificación (25 ms).
