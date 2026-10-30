# Prerrequisito (fases 2 y 3): comprensión y preparación de datos

Fecha: 2026-10-23. Estado: **pendiente de visto bueno** (sorteo de impostoras rehecho con estratificación por género). Todavía no se ha empezado el modelado.

Cuadernos: `notebooks/01_comprension_datos.ipynb`, `notebooks/02_preparacion_datos.ipynb` (ejecutados de principio a fin, sin errores).
Código reutilizable: `src/config.py`, `src/data.py`.

## Entorno

| Elemento | Valor |
|---|---|
| SO | Windows 10 Pro 19045 |
| CPU / RAM | Intel Core i5-10400 @ 2.90 GHz / 16 GB |
| GPU | NVIDIA GeForce RTX 5060, 8 GB (compute capability 12.0), driver 616.92 |
| Python | 3.10.4 en `.venv` |
| PyTorch | 2.11.0+cu128, torchvision 0.26.0+cu128 |
| Otras | NumPy 2.2.6, OpenCV-contrib 5.0.0 (incluye LBPH), scikit-learn 1.7.2, pandas 2.3.3, Matplotlib 3.10.9, Pillow 12.3.0, facenet-pytorch 2.6.0 |

**Prueba real en GPU:** multiplicación de matrices 4096×4096 (20 repeticiones), ≈ 11.7 TFLOPS, error máximo frente a CPU 6.9e-4 (float32, TF32).
Convolución con forward y backward correcta. InceptionResnetV1 y MTCNN de facenet-pytorch se ejecutan en la GPU con torch 2.11.

**Decisión sobre facenet-pytorch:** fija `torch<2.3`, que no soporta Blackwell (sm_120). Se instaló con `--no-deps`; su código
funciona con torch 2.11. Los pesos preentrenados de FaceNet (VGGFace2) aún **no** se han descargado; se descargarán en la tarea 2.1.
Si fallaran, la alternativa es ArcFace vía ONNX.

## Dataset (fase 2)

- 2 562 imágenes, 31 identidades (de 30 a 120 por persona, media 82,6). CSV con `id` y `label`, totalmente consistente con las carpetas.
- `Faces` = recortes ajustados de `Original Images` (mismos nombres, mismas fotos). **Fuente única: `Faces`**, 160×160 RGB.
  No hace falta detectar rostros en esta etapa; la detección solo se necesitará para el video (tarea 2.6).
- Duplicados exactos (MD5): 5 pares. Casi duplicados: ver la sección siguiente.
- Sesgo: 29 de 31 identidades son famosas (probablemente vistas por los modelos preentrenados); Marmik y Kashyap no lo son.
  Fotos de prensa: buena iluminación, mayoría frontales.

Figuras: `figuras/01_imagenes_por_persona.png`, `figuras/01_original_vs_faces.png`, `figuras/01_muestra_faces.png`,
`figuras/01_hist_similitud_pares.png`, `figuras/01_pares_mas_similares.png`, `figuras/01_pares_cerca_umbral.png`.

## Casi duplicados

- Se descartó dHash: con caras alineadas, a distancia 3 ya empareja fotos **distintas** de la misma persona.
- Medida usada: correlación de píxeles a 32×32 en color, contando también el espejo horizontal. Solo se comparan pares de la misma persona,
  y se unen con union-find.
- **Umbral 0.90**, elegido revisando pares a ojo. Hay fotos idénticas con correlación de hasta ≈ 0.91, y con 0.89 las cadenas ya
  forman un grupo de 24 fotos distintas.

| Umbral | Grupos con >1 imagen | Imágenes agrupadas | Grupo más grande |
|---|---|---|---|
| 0.92 | 69 | 146 | 4 |
| **0.90 (elegido)** | **93** | **230** | **12** (Jessica Alba) |
| 0.89 | 106 | 291 | 24 |
| 0.88 | 121 | 364 | 33 |

Resultado: 2 425 grupos, 147 pares agrupados (`02_pares_casi_duplicados.csv`). Los grupos no dependen del sorteo.
**Riesgo residual:** con la división final, **178** pares de la misma persona con correlación en [0.85, 0.90) quedan en conjuntos distintos
(con el sorteo descartado eran 186; la cifra cambia porque cambian las identidades registradas). Son fotos parecidas, no idénticas,
pero la correlación de píxeles no detecta la misma sesión fotográfica con otra pose. Se mantiene como limitación.

## División (fase 3) — semilla 42

### Etiqueta de género aproximada (solo para estratificar)

El dataset no trae género. Se asignó una etiqueta M/F **a partir del nombre de pila** (no se analizaron los rostros), según el uso más
habitual del nombre, y el usuario la confirmó el 2026-10-23 (`src/config.py`, `GENDER_BY_NAME`). Es una **aproximación** y se usa
**únicamente para estratificar** el sorteo de impostoras; no es una variable del modelo. Casos ambiguos por nombre, confirmados
explícitamente: Billie Eilish = F, Courtney Cox = F, Kashyap = M, Marmik = M. Total: 16 M y 15 F.

### Sorteo descartado

El primer sorteo, sin estratificar, dio como impostoras de validación a Claire Holt, Ellen Degeneres y Jessica Alba (todas F), y como
impostoras de prueba a Billie Eilish, Kashyap, Natalie Portman y Priyanka Chopra. **Se descartó por el desequilibrio de género**: el umbral
se habría ajustado solo con impostoras mujeres. **En ese momento no existía ningún modelo ni ninguna métrica**, así que el cambio no está
condicionado por los resultados.

### Sorteo final (estratificado por género, semilla 42)

Cuotas confirmadas: validación 2 M + 1 F; prueba 2 M (Kashyap + 1 sorteado) + 2 F; registradas 12 M + 12 F, con Marmik entre ellas.
Se sortea dentro de cada género con `random.Random(42)` (`D.assign_roles`).

| Rol | M | F | Identidades |
|---|---|---|---|
| Registradas (24) | 12 | 12 | Akshay Kumar, Alexandra Daddario, Alia Bhatt, Amitabh Bachchan, Anushka Sharma, Billie Eilish, Brad Pitt, Camila Cabello, Charlize Theron, Claire Holt, Dwayne Johnson, Ellen Degeneres, Hrithik Roshan, Jessica Alba, Lisa Kudrow, Margot Robbie, **Marmik**, Priyanka Chopra, Robert Downey Jr, Roger Federer, Tom Cruise, Vijay Deverakonda, Virat Kohli, Zac Efron |
| Impostoras de validación (3) | 2 | 1 | Andy Samberg (M), Henry Cavill (M), Elizabeth Olsen (F) |
| Impostoras de prueba (4) | 2 | 2 | Hugh Jackman (M), **Kashyap** (M), Courtney Cox (F), Natalie Portman (F) |

| Conjunto | Registradas (imágenes / personas) | Impostoras (imágenes / personas) | Total |
|---|---|---|---|
| train | 1 362 / 24 | — | 1 362 |
| val | 305 / 24 | 269 / 3 | 574 |
| test | 299 / 24 | 327 / 4 | 626 |
| **Total** | 1 966 | 596 | 2 562 |

Proporción en las registradas: 69,3 / 15,5 / 15,2 %. Marmik: 22 / 5 / 5. La tabla por persona (con la etiqueta de género) está en el
cuaderno 02 y en `02_splits.csv`; la figura es `figuras/02_division_registradas.png`.

Uso previsto: la plantilla de cada registrada se calcula **solo con sus fotos de train**. Los intentos genuinos salen de val/test.
Los intentos impostores son todas las fotos de las impostoras de val (o de test) contra las 24 plantillas:
269 × 24 = 6 456 en validación y 327 × 24 = 7 848 en prueba.

**Comprobaciones superadas** (`D.check_splits`, cuaderno 02):
- Ningún archivo, imagen idéntica (MD5) ni grupo de casi duplicados aparece en dos conjuntos.
- Ninguna impostora aparece en train.
- Las identidades impostoras de val y de test son distintas.
- Las 24 registradas tienen fotos en train, val y test.
- Se cumplen las cuotas de género (val 2M+1F, test 2M+2F); las impostoras de validación no son todas del mismo género;
  Marmik está registrada y Kashyap es impostora de prueba.

## Preprocesado

- 160×160 RGB, sin reescalar (ya viene así). Es la entrada nativa de FaceNet; para modelos de 112×112 se reescalará en su propio preprocesado.
- Normalización `(x − 127.5) / 128` (la de FaceNet), aplicada al cargar.
- Caché `data/processed/faces160.npz` (uint8, 159 MB) y `data/processed/splits.csv`, ambos fuera de git.
- Aumento de datos: se define en la tarea 2.2, solo para train.

## Observaciones y limitaciones para el informe

1. La etiqueta de género es una aproximación por nombre, usada solo para equilibrar el reparto. No se evalúa el rendimiento por género
   como resultado formal; con 3–4 impostoras por conjunto no habría base estadística.
2. Solo hay 4 identidades impostoras en prueba (3 en validación). Hay muchas comparaciones, pero poca diversidad de personas.
3. Marmik solo tiene 5 fotos genuinas en val y 5 en test, así que sus métricas individuales tendrán mucha varianza. Kashyap aporta 30 fotos impostoras.
4. Sesgo de famosos (ver arriba) y riesgo residual de 178 pares parecidos (corr. 0.85–0.90) en conjuntos distintos.
