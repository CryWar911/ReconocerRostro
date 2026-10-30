# Resumen para el informe — Sprint 2 (CRISP-DM fases 4 y 5)

**Proyecto:** Sistema de autenticación biométrica mediante reconocimiento facial (verificación 1 a 1). Universidad Andina del Cusco, Inteligencia Artificial.
**Fecha:** 2026-10-23. **Repositorio:** local; último commit de este sprint al redactar: `6dfcfae`.
**Estado:**
- Fases 4 y 5 completas con el dataset.
- **La prueba con video de voluntarios (tarea 2.6) está PENDIENTE**: el código está listo, ensayado con datos simulados y bloqueado hasta tener el video y las fotos reales.
- **Los valores objetivo siguen pendientes de confirmar con el docente.**

Todas las cifras proceden de cuadernos ejecutados. Cada sección indica el documento de detalle en `docs/sprint2/`.

---

## 1. Entorno

| Elemento | Valor |
|---|---|
| Sistema operativo | Windows 10 Pro 19045 |
| CPU / RAM | Intel Core i5-10400 @ 2,90 GHz / 16 GB |
| GPU | NVIDIA GeForce RTX 5060, 8 GB (compute capability 12.0, Blackwell), driver 616.92 |
| Python | 3.10.4, entorno virtual `.venv` |
| PyTorch / torchvision | 2.11.0+cu128 / 0.26.0+cu128 (CUDA 12.8) |
| facenet-pytorch | 2.6.0, instalado con `--no-deps` (exige torch < 2.3, que no soporta la RTX 5060) |
| OpenCV (contrib) | 5.0.0 |
| NumPy / SciPy / scikit-learn | 2.2.6 / 1.15.3 / 1.7.2 |
| pandas / Matplotlib / Pillow | 2.3.3 / 3.10.9 / 12.3.0 |

Las versiones exactas están en `requirements.txt` y la reproducción en el `README.md`.

La GPU se verificó con una operación real: multiplicación de matrices 4096×4096 a ≈ 11,7 TFLOPS, con error máximo de 6,9e-4 frente a CPU.

## 2. Datos (prerrequisito: fases 2 y 3)

Detalle en `00_revision_previa.md` y `01_02_preparacion_datos.md`.

- **Dataset:** Kaggle *Face Recognition Dataset* (vasukipatel): 2 562 imágenes de **31 personas**, entre 30 y 120 por persona (media 82,6).
- **Fuente única: `Faces/Faces`** (recortes de 160×160 RGB). `Original Images` contiene las mismas fotos sin recortar y no se usó para modelar, para no filtrar datos entre conjuntos.
- **Casi duplicados:** se agruparon por correlación de píxeles (32×32, color, también en espejo) con umbral 0,90: 93 grupos y 230 imágenes. Cada grupo cae entero en un solo conjunto.
- **Riesgo residual:** 178 pares parecidos (correlación 0,85–0,90) de la misma persona quedan en conjuntos distintos.
- **Semilla: 42** (NumPy, `random` y PyTorch).
- **Tamaño de entrada: 160×160** (el nativo de FaceNet; las caras ya vienen así). Normalización (x − 127,5)/128.

**Reparto de identidades**, separado por identidad y estratificado por un género aproximado deducido del nombre, que se usa solo para el reparto:
- un primer sorteo sin estratificar se **descartó antes de entrenar nada** porque las 3 impostoras de validación eran mujeres;
- Marmik se forzó a registradas y Kashyap a impostoras de prueba.

| Rol | Identidades |
|---|---|
| Registradas (24: 12 M y 12 F) | Akshay Kumar, Alexandra Daddario, Alia Bhatt, Amitabh Bachchan, Anushka Sharma, Billie Eilish, Brad Pitt, Camila Cabello, Charlize Theron, Claire Holt, Dwayne Johnson, Ellen Degeneres, Hrithik Roshan, Jessica Alba, Lisa Kudrow, Margot Robbie, **Marmik** (no famoso), Priyanka Chopra, Robert Downey Jr, Roger Federer, Tom Cruise, Vijay Deverakonda, Virat Kohli, Zac Efron |
| Impostoras de validación (3: 2 M y 1 F) | Andy Samberg, Henry Cavill, Elizabeth Olsen |
| Impostoras de prueba (4: 2 M y 2 F) | Hugh Jackman, **Kashyap** (no famoso), Courtney Cox, Natalie Portman |

| Conjunto | Registradas | Impostoras | Total |
|---|---|---|---|
| Entrenamiento | 1 362 | — | 1 362 |
| Validación | 305 | 269 | 574 |
| Prueba | 299 | 327 | 626 |
| **Total** | 1 966 | 596 | 2 562 |

Las registradas quedan en 69,3 / 15,5 / 15,2 %.

**Comparaciones de verificación:**

| | Genuinas | Impostoras externas | Impostoras internas |
|---|---|---|---|
| Validación | 305 | 6 456 (269 × 24) | 7 015 (305 × 23) |
| Prueba | 299 | 7 848 (327 × 24) | 6 877 (299 × 23) |

- Las externas son impostoras no registradas contra las 24 plantillas.
- Las internas son registradas contra la plantilla de otra registrada.

## 3. Técnica elegida y por qué (tarea 2.1)

Detalle en `03_seleccion_tecnica.md`. La comparación se hizo **solo en validación**, con el protocolo de verificación 1 a 1 (plantilla = media de los embeddings de train y similitud coseno).

| Variante | EER | AUC | Tiempo GPU / CPU por verificación |
|---|---|---|---|
| (a1) CNN propia desde cero (2,39 M parámetros) | 4,85 % | 0,9892 | 4,9 / 20 ms |
| (a2) ResNet-18 ImageNet por transferencia (11,19 M) | 3,55 % | 0,9929 | 6,5 / 42 ms |
| **(b1) FaceNet InceptionResnetV1, pesos VGGFace2, congelada** | **0,00 %** | **1,0000** | 33 / 71 ms |
| (b2) FaceNet, pesos CASIA-WebFace | 0,63 % | 0,9999 | 36 / 75 ms |
| (c) LBPH, línea base clásica | 33,52 % | 0,7171 | — / 25 ms |

**Elegida: (b1) FaceNet VGGFace2 congelada, con embeddings y similitud coseno contra la plantilla del usuario.**
- Es la mejor con diferencia en validación.
- No necesita reentrenarse para registrar usuarios nuevos; (a1) y (a2) son clasificadores de 24 clases.
- Cumple el tiempo de sobra.
- Es una CNN, como exige el proyecto. La línea base LBPH queda muy por debajo.

**Pesos:** `20180402-114759-vggface2.pt` (facenet-pytorch, https://github.com/timesler/facenet-pytorch/releases; conversión de davidsandberg/facenet). SHA-256 `281cebca8662831a…`, 27,91 M parámetros.

**Control:** (a2) ResNet-18 ImageNet se mantuvo hasta la prueba para estudiar el sesgo de famosos, porque su preentrenamiento no incluye rostros.

## 4. Entrenamiento (tarea 2.2)

Detalle en `04_entrenamiento.md`.

- **FaceNet** no se ajustó, por tres motivos: la validación ya estaba saturada, el ajuste fino con 24 personas sobreajusta y la red congelada permite registrar usuarios sin reentrenar.
  "Entrenar" fue registrar las 24 identidades con sus fotos de train (de 22 a 84 por persona).
- Por eso **FaceNet no tiene curvas de entrenamiento**.
- **Control (a2):** AdamW con OneCycle, lr 3e-4, 40 épocas, lote 64, label smoothing 0,1, weight decay 5e-4 y aumento de datos. Tardó **72 s en GPU**.
  Exactitud de clasificación 1,000 en train y 0,970 en validación (`figuras/04_curvas_control_a2.png`).
- **Formato reutilizable:** paquete `models/<nombre>/`, ignorado por git, con la red en TorchScript, las plantillas (24×512) y un `config.json`.
  Se carga con `src.pipeline.Verifier` sin necesitar facenet-pytorch. Al recargarlo se reproduce la validación.

| Tiempos de FaceNet (mediana) | GPU | CPU |
|---|---|---|
| Verificación 1 a 1 (leer JPG, embedding y coseno) | 18 ms | 89 ms (p95 246 ms) |
| Registro de un usuario (54 fotos) | 0,18 s | 2,2 s |
| Embedding por imagen, en lotes de 64 | 0,51 ms | 34,6 ms |

## 5. Ajuste de parámetros con validación (tarea 2.3)

Detalle en `05_validacion_ajuste.md`. Se usó **solo validación**; el plan de prueba se fijó antes (`plan_evaluacion.md`).

| Parámetro | Probado | Elegido |
|---|---|---|
| Métrica | coseno; euclídea normalizada; euclídea sin normalizar | **coseno** (la euclídea normalizada da exactamente lo mismo) |
| Plantilla | media; vecino más cercano; media de los 3 mejores; k-means con 3 | **media de los embeddings de train, renormalizada** (las variantes con varias plantillas empeoran) |
| Umbral | EER (0,607); centro del hueco (0,595); FAR ≤ 0,1 % solo con imágenes limpias (0,547); FAR ≤ 0,1 % en la peor condición (0,5514) | **0,5514** |
| FAR objetivo para fijar el umbral | — | ≤ 0,1 % con impostoras externas e internas (13 471), en cada una de 18 condiciones (limpia y 17 perturbaciones) |
| Agregación de fotogramas en video | 1 fotograma; media de embeddings; media de puntuaciones; votación (k = 3, 5) | **votación por mayoría** |

**Umbral:**
- La regla se definió **antes de calcularlo**: el mayor umbral con FAR ≤ 0,1 % en todas las condiciones.
- En validación limpia da FAR 0,052 % (7 de 13 471, todas internas: Hrithik Roshan → Vijay Deverakonda en 6 casos y Akshay Kumar → Hrithik Roshan en 1) y FRR 0 %, con 0,056 de margen hasta la genuina mínima.
- **Umbrales fijados antes de la prueba:**
  - FaceNet **0,5514 (oficial)**;
  - FaceNet 0,595 (secundario, solo para reportar);
  - control (a2) 0,8769.

**Robustez** (17 perturbaciones sintéticas en validación; FRR de FaceNet con 0,5514):
- **Robusta** a brillo, contraste, JPEG con calidad ≥ 15, desenfoque σ ≤ 2 y rotación ≤ 15°: FRR ≤ 1 %.
- **Débil** ante oclusiones (ojos tapados 28,5 %, media cara 23,3 %, tercio inferior 7,9 %), desenfoque σ3 (9,5 %) y JPEG con calidad 8 (4,3 %).
- El FAR se mantuvo ≤ 0,1 % en todas las condiciones.

## 6. Métricas y valores objetivo (tarea 2.4)

Definiciones formales en `06_metricas.md`. **Objetivos pendientes de confirmar con el docente.**

| Métrica | Definición | Objetivo |
|---|---|---|
| FAR | impostoras aceptadas / impostoras | ≤ 5 % |
| FRR | genuinas rechazadas / genuinas | ≤ 10 % |
| Exactitud balanceada | [(1 − FAR) + (1 − FRR)] / 2 | ≥ 90 % |
| Exactitud simple y proporción de comparaciones | (TA + TR) / total | solo se reportan |
| ROC, AUC y EER | descriptivas | sin objetivo |
| Tiempo por verificación | de punta a punta; p95 en CPU | ≤ 3 s |

Se usa la exactitud balanceada porque en prueba hay unas 49 impostoras por cada genuina (las genuinas son el 1,99 %). Un sistema que rechazara
a todo el mundo tendría un 98 % de exactitud simple.

## 7. Resultados finales en PRUEBA (tarea 2.5)

Detalle en `06_evaluacion_prueba.md`.
- **Ejecución única** sobre el commit `0a27e3d`, con el árbol limpio, sin errores y sin re-ejecución. No se recalculó ningún umbral.
- La tabla usa todas las impostoras (externas más internas). El IC 95 % es de Clopper-Pearson y es optimista en el FAR, porque las comparaciones no son independientes.

| Modelo / umbral | FAR | FRR | Exactitud balanceada | Exactitud simple | EER (descr.) | AUC |
|---|---|---|---|---|---|---|
| **FaceNet, 0,5514 (oficial)** | **0,041 %** (6 / 14 725; IC 0,015–0,089 %) | **1,00 %** (3 / 299; IC 0,21–2,90 %) | **99,48 %** | 99,94 % | 0,67 % | 0,99992 |
| FaceNet, 0,595 (secundario) | 0,014 % (2 / 14 725) | 1,67 % (5 / 299) | 99,16 % | 99,95 % | 0,67 % | 0,99992 |
| Control (a2), 0,8769 | 0,081 % (12 / 14 725) | 26,76 % (80 / 299) | 86,58 % | 99,39 % | 3,99 % | 0,99304 |

Por tipo de impostora, FaceNet con 0,5514:
- externas: 3 de 7 848 (0,038 %);
- internas: 3 de 6 877 (0,044 %).

**Matriz de confusión de FaceNet con 0,5514:**

| | Aceptada | Rechazada |
|---|---|---|
| Genuina | 296 | 3 |
| Impostora | 6 | 14 719 |

**Cumplimiento de objetivos** (umbral oficial; objetivos pendientes de confirmar con el docente):

| Métrica | Valor | Objetivo | ¿Cumple? |
|---|---|---|---|
| FAR | 0,041 % | ≤ 5 % | Sí |
| FRR | 1,00 % | ≤ 10 % | Sí |
| Exactitud balanceada | 99,48 % | ≥ 90 % | Sí |
| Tiempo por verificación (p95, CPU, sin detección) | 0,073 s | ≤ 3 s | Sí |
| Tiempo con detección MTCNN (p95, CPU; ensayo con fotogramas de 640×480) | 0,275 s | ≤ 3 s | Sí (cifra de ensayo) |

**Validación frente a prueba** (FaceNet, 0,5514):
- el FAR pasa de 0,052 % a 0,041 %;
- **el FRR pasa de 0 % a 1,00 %**;
- la genuina mínima baja de 0,607 a 0,402 y la impostora máxima sube de 0,583 a 0,628.

En prueba las genuinas y las impostoras ya no están separadas del todo, y el EER pasa de 0 a 0,67 %. La validación estaba saturada.

**Errores concretos de FaceNet en prueba:**
- **Rechazos:** Zac Efron_32 (0,402), Billie Eilish_34 (0,436) y Billie Eilish_66 (0,467).
- **Aceptaciones externas:** Kashyap_25 → Marmik (0,628), Courtney Cox_58 → Charlize Theron (0,594) y Kashyap_17 → Marmik (0,566).
- **Aceptaciones internas:** Vijay Deverakonda_17 → Hrithik Roshan (0,596), Hrithik Roshan_93 → Akshay Kumar (0,563) y Vijay Deverakonda_77 → Hrithik Roshan (0,561).

**Chequeo del sesgo de famosos** (cada grupo es **una sola persona** y no permite conclusiones firmes):
- **Marmik** (registrado, no famoso): FaceNet lo rechazó en 0 de 5 intentos; el control (a2), en 2 de 5.
- **Kashyap** (impostor, no famoso): FaceNet lo aceptó en 2 de 720 comparaciones (0,278 %), frente al 0,014 % del resto de impostoras externas.
  **Las dos aceptaciones son contra la plantilla de Marmik.** El control (a2) no lo aceptó ninguna vez (0 de 720).
- Con esto **no se puede afirmar ni descartar** el sesgo de famosos.

**Tiempos en prueba** (mediana / p95): FaceNet 20 / 41 ms en GPU y 62 / 73 ms en CPU, sin detección.

## 8. Prueba con video de voluntarios (tarea 2.6): PENDIENTE

Detalle en `08_video_voluntarios.md`.

- **Preparado:**
  - script de registro de voluntarios (`src/registro_voluntario.py`);
  - script de video (`src/video_verificacion.py`), con MTCNN de margen 0, 1 de cada 3 fotogramas, el umbral oficial 0,5514 y votación por mayoría en ventanas de 5 fotogramas;
  - métricas por fotograma y por ventana, desglose por voluntario, tasa de fotogramas sin rostro y tiempo con detección.
- **Margen de MTCNN:** se eligió 0 con imágenes de validación. Reproduce el recorte del dataset con un coseno mediano de 0,989 entre embeddings.
- **Ensayo con datos simulados** (video sintético hecho con fotos del dataset): todo funciona de punta a punta. Tiempo con detección: p95 de 0,186 s en GPU y 0,275 s en CPU. **Sus cifras de FAR y FRR no son resultados** y no se incluyen en este informe.
- **Prueba real:** `notebooks/08_video_voluntarios.ipynb`, de ejecución única, **sin ejecutar y bloqueado** hasta contar con el video, las fotos de registro y las anotaciones.
- **Privacidad:** los datos van fuera del repositorio, con seudónimos, y en git solo hay métricas agregadas.

## 9. Figuras (en `docs/sprint2/figuras/`)

| Archivo | Contenido |
|---|---|
| `01_imagenes_por_persona.png` | Imágenes por persona en el dataset |
| `01_original_vs_faces.png` | Original frente a recorte de `Faces` |
| `01_muestra_faces.png` | Muestra aleatoria de `Faces` |
| `01_hist_similitud_pares.png`, `01_pares_mas_similares.png`, `01_pares_cerca_umbral.png` | Detección de casi duplicados y elección del umbral 0,90 |
| `02_division_registradas.png`, `02_muestras_por_conjunto.png` | División 70/15/15 y muestras por conjunto |
| `03_roc_validacion.png`, `03_det_validacion.png` | ROC y DET de las 5 variantes en validación (tarea 2.1) |
| `03_distribucion_puntuaciones.png` | Puntuaciones genuinas e impostoras por variante (validación) |
| `03_curvas_entrenamiento_a.png` | Curvas de entrenamiento y validación de (a1) y (a2) |
| `04_curvas_control_a2.png` | Curvas de entrenamiento y validación del control (a2) |
| `04_similitud_plantillas.png` | Similitud entre las 24 plantillas de FaceNet |
| `05_pares_dificiles_facenet.png` | Impostores más parecidos en validación |
| `05_perturbaciones_ejemplo.png`, `05_robustez_puntuaciones.png` | Perturbaciones y su efecto en las puntuaciones (validación) |
| **`07_roc_det_prueba.png`** | **ROC y DET en prueba, con los puntos de operación fijados** |
| **`07_matrices_confusion_prueba.png`** | **Matrices de confusión en prueba (FaceNet 0,5514 y 0,595; control 0,8769)** |
| `07_distribucion_puntuaciones_prueba.png` | Puntuaciones genuinas, externas e internas en prueba |
| `08_ENSAYO_tasas_video.png` | Tasas del ENSAYO de video (datos simulados; no es un resultado) |

## 10. Limitaciones observadas

1. **Sesgo de famosos:** FaceNet se preentrenó con VGGFace2, una colección de celebridades, y es probable que ya hubiera visto a 29 de las 31 personas.
   El chequeo con no famosos es de una sola persona por grupo. El único caso observado (Kashyap aceptado como Marmik) no permite generalizar.
2. **Pocas identidades impostoras:** 4 en prueba y 3 en validación. Hay muchas comparaciones, pero poca diversidad de personas.
3. **Validación saturada:** la validación no permitió distinguir ajustes finos (EER 0 %). En prueba aparecieron errores que no se vieron en validación.
4. **Pares de registrados muy parecidos:** Hrithik Roshan y Vijay Deverakonda concentran la mayoría de las aceptaciones internas en validación y en prueba.
5. **Iluminación y pose:** son fotos de prensa, bien iluminadas y mayoritariamente frontales. Las pruebas de robustez son sintéticas, sobre el recorte ya alineado,
   y muestran fragilidad ante **oclusiones** (gafas de sol, mascarilla, media cara) y desenfoque fuerte.
6. **Sesgo y equilibrio del dataset:** entre 30 y 120 fotos por persona. El género se aproximó a partir del nombre y solo para el reparto; no se evaluó el rendimiento por género.
7. **Intervalos de confianza:** las comparaciones no son independientes (cada foto se compara con 23 o 24 plantillas), así que los IC del FAR son optimistas.
8. **Video real sin probar:** las cifras de video son de un ensayo con fotos fijas animadas. Si aparecen varias personas, MTCNN elige el rostro más grande.
9. **Suplantación:** **no hay detección de vida**. El sistema aceptaría una foto o un video del usuario mostrado a la cámara, y no se afirma ninguna resistencia a la suplantación.

## 11. Problemas encontrados y cómo se resolvieron

| Problema | Solución |
|---|---|
| No existía la preparación de datos del Sprint 1 | Se hizo como prerrequisito, en los cuadernos 01 y 02 |
| `facenet-pytorch` fija `torch<2.3`, que no soporta la RTX 5060 (sm_120) | PyTorch 2.11 con CUDA 12.8 y `facenet-pytorch --no-deps`; comprobado con operaciones reales en la GPU |
| dHash agrupaba fotos distintas de la misma persona | Se cambió a correlación de píxeles con umbral 0,90, revisado a ojo |
| Primer sorteo de impostoras con validación solo femenina | Se descartó antes de entrenar y se rehizo estratificado por género aproximado |
| La carpeta del dataset estaba bloqueada como directorio de trabajo de la sesión | Se cambió el directorio de trabajo y se movió a `data/raw/` |
| Plantilla recalculada con TorchScript frente a la del paquete (diferencia ~2,5e-5) | Se usa una tolerancia de 1e-3, documentada |
| El umbral del EER quedaba en el borde del margen en validación | Se cambió a un criterio de FAR objetivo con margen de robustez, fijado antes de calcularlo |
| Node.js no está instalado (validador de paleta de la guía de gráficos) | Se usaron los colores por defecto ya validados, con estilos de línea como segunda codificación |
| La extracción LBPH con χ² fue lenta (275 s) | No afecta al tiempo por verificación (25 ms); se aceptó así |

## 12. Cómo volver a la fase de modelado (si el docente exige más)

Con los objetivos propuestos no hace falta volver: se cumplen en prueba. Si el docente pidiera objetivos más estrictos, o si la prueba con video real
no los alcanzara, estas serían las vías, a decidir **antes** de una nueva evaluación y con datos nuevos, porque el conjunto de prueba ya se usó:
- más identidades impostoras y personas no famosas;
- datos con oclusiones e iluminación variable;
- ajuste fino con pérdida de márgenes (ArcFace) sobre un conjunto externo;
- detección de vida para la suplantación.

## Documentos de detalle

`00_revision_previa.md`, `01_02_preparacion_datos.md`, `03_seleccion_tecnica.md`, `04_entrenamiento.md`, `05_validacion_ajuste.md`, `06_metricas.md`,
`plan_evaluacion.md`, `06_evaluacion_prueba.md`, `08_video_voluntarios.md`. Las tablas CSV/JSON de cada tarea están en `docs/sprint2/`, con el prefijo de su número de cuaderno.
