# Tarea 0 — Revisión previa (estado del Sprint 1 y exploración del dataset)

Fecha: 2026-10-23. Estado: revisado. **Actualización:** el protocolo quedó confirmado y el dataset se movió a `data/raw/Dataset/`. Las figuras `00_*` se sustituyeron por las `01_*` del cuaderno 01, el sorteo final de impostoras está estratificado por género y el umbral de casi duplicados final es 0.90 (ver `01_02_preparacion_datos.md`).

## 1. ¿Existe la preparación de datos del Sprint 1?

**No.** En `D:\IA\FaceID` solo hay `archive.zip` (761 MB) y la carpeta `Dataset/` descomprimida.
No hay cuadernos, scripts, división train/val/test ni repositorio git. Por tanto, las fases 2 y 3
(comprensión y preparación de datos) deben hacerse primero como prerrequisito, en su propio cuaderno
(`notebooks/01_preparacion_datos.ipynb`), separado del modelado.

## 2. Hechos verificados del dataset (medidos, no asumidos)

| Aspecto | Resultado |
|---|---|
| `Dataset.csv` | 2 562 filas, columnas `id` (nombre de archivo) y `label` (persona) |
| `Faces/Faces` | 2 562 archivos JPG, **todos 160×160 px, RGB** |
| `Original Images/Original Images` | 31 subcarpetas (una por persona), 2 562 archivos; tamaños de 216×200 a 5760×5568 px (mediana ≈ 967×891) |
| Correspondencia | Los nombres de archivo coinciden 1 a 1 entre CSV, `Faces` y `Original Images`; `label` = prefijo del nombre en el 100 % de filas |
| ¿`Faces` son recortes de `Original Images`? | **Sí.** Inspección visual (`figuras/00_original_vs_face.jpg`): cada cara es un recorte ajustado (frente y mentón cortados) del original con el mismo nombre |
| Identidades | 31 |
| Imágenes por persona | mín. 30 (Kashyap), máx. 120 (Brad Pitt), media 82,6 |
| Duplicados exactos (MD5) en `Faces` | 5 pares, todos de la misma persona: Courtney Cox 9/10, Courtney Cox 23/45, Henry Cavill 5/25, Hugh Jackman 82/83, Natalie Portman 92/93 |
| Casi duplicados (dHash, distancia ≤ 2) | 6 pares, todos de la misma persona (los 5 anteriores + Natalie Portman 71/73). Con umbrales mayores aparecen falsos positivos entre personas distintas, así que el umbral definitivo se fijará revisando visualmente |

Imágenes por persona (de `Dataset.csv`):

| Persona | n | Persona | n | Persona | n |
|---|---|---|---|---|---|
| Brad Pitt | 120 | Alexandra Daddario | 92 | Margot Robbie | 72 |
| Vijay Deverakonda | 115 | Andy Samberg | 92 | Elizabeth Olsen | 71 |
| Robert Downey Jr | 113 | Zac Efron | 91 | Lisa Kudrow | 70 |
| Hugh Jackman | 112 | Camila Cabello | 87 | Anushka Sharma | 68 |
| Jessica Alba | 108 | Courtney Cox | 80 | Dwayne Johnson | 61 |
| Henry Cavill | 106 | Alia Bhatt | 79 | Tom Cruise | 58 |
| Natalie Portman | 105 | Charlize Theron | 78 | Akshay Kumar | 50 |
| Priyanka Chopra | 102 | Roger Federer | 77 | Virat Kohli | 49 |
| Hrithik Roshan | 101 | Ellen Degeneres | 75 | Marmik | 32 |
| Billie Eilish | 98 | Amitabh Bachchan | 74 | Kashyap | 30 |
| Claire Holt | 96 | | | | |

Observaciones:
- 29 de las 31 identidades son celebridades; **Marmik** y **Kashyap** parecen personas no famosas.
- Es muy probable que los modelos preentrenados de rostros (FaceNet/VGGFace2, ArcFace/MS1M) hayan visto
  fotos de estas celebridades durante su entrenamiento. Eso puede inflar los resultados de la opción (b).
  Se documentará como limitación y se reportarán aparte las métricas de Marmik/Kashyap si es posible.
- Fotos de prensa/alfombra roja: buena iluminación, mayoría frontales → sesgo respecto a una cámara web real.

## 3. Decisiones propuestas (requieren confirmación)

1. **Fuente única: `Faces/Faces` (160×160).** `Original Images` no se usa para nada, porque son las mismas
   fotos (usar ambas filtraría datos entre conjuntos). Ventaja: no hace falta un detector para el dataset.
   Para el video (tarea 2.6) sí se necesitará un detector, y su recorte debe imitar este recorte ajustado.
2. **Tamaño de entrada: 160×160.** Las caras ya vienen a 160×160 (no hay que reescalar ni perder detalle), y
   es la entrada nativa de FaceNet (InceptionResnetV1). Para ArcFace (112×112) o la línea base se reescalará
   dentro del propio modelo.
3. **Agrupación de casi duplicados** (dHash + revisión visual) antes de dividir, para que cada grupo caiga
   entero en un solo conjunto.
4. **Semilla: 42** (NumPy, `random`, PyTorch).

## 4. Propuesta de protocolo con impostores

- **24 identidades registradas / 7 impostoras**, impostoras elegidas al azar con semilla 42 (tras fijar el
  protocolo, no después de ver resultados).
- Registradas: sus imágenes se dividen ≈ 70/15/15 por persona (estratificado, por grupos de casi duplicados).
  Train = entrenamiento del modelo propio y **plantilla de registro** (enrolamiento); val/test = intentos
  genuinos.
- Impostoras: **nunca** en entrenamiento. Propongo separarlas por identidad: **3 para validación** (ajuste
  del umbral) y **4 para prueba**, de modo que los impostores de prueba sean personas que el sistema nunca vio,
  como en la realidad.
- Intento impostor = imagen de una persona X que dice ser el usuario registrado Y (todas las combinaciones
  imagen × usuario). Además se pueden añadir intentos "registrado contra otro registrado" como impostores
  internos.

Justificación de 24/7: deja ≥ 75 % de identidades para entrenar el modelo propio (a), y 7 impostoras dan
≈ 7 × 80 ≈ 560 imágenes × 24 usuarios ≈ 13 000 intentos impostores, suficientes para estimar un FAR ≤ 5 %.

## 5. Entorno

Detectado: Python 3.10.4 (Windows), NumPy 1.26.4, OpenCV 4.11.0, Matplotlib 3.10.7, Pillow 11.3.0.
CPU Intel i5-10400, 16 GB RAM, GPU **NVIDIA RTX 5060 (8 GB)**.

Faltan: PyTorch + torchvision, scikit-learn, pandas, Jupyter, facenet-pytorch (y opcionalmente
opencv-contrib-python para LBPH). Nota técnica: la RTX 5060 (arquitectura Blackwell) requiere PyTorch ≥ 2.7
con CUDA 12.8, mientras que `facenet-pytorch` fija `torch<2.3`; se instalaría con `--no-deps` (solo se usan
sus pesos y la red, que funcionan con versiones nuevas).

## Figuras
- `figuras/00_original_vs_face.jpg` — original (izq.) vs. recorte de `Faces` (der.), 6 ejemplos al azar.
- `figuras/00_muestra_faces.jpg` — 64 recortes al azar de `Faces`.
