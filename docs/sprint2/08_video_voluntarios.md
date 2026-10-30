# Tarea 2.6 — Prueba con video de voluntarios: preparada y ENSAYADA (sin datos reales)

Fecha: 2026-10-23. Estado: **listo y bloqueado, a la espera del video y las fotos reales.** Todas las cifras de este documento son de un
**ENSAYO con datos simulados** a partir del propio dataset. **No son resultados del sistema** y no deben citarse como tales.

Es la línea de ciencia de datos: solo hay scripts y cuadernos, sin aplicación web ni interfaz.

## Qué hay

| Pieza | Archivo | Qué hace |
|---|---|---|
| Script de registro | `src/registro_voluntario.py` | Toma la carpeta de fotos de un voluntario (fuera del repo), detecta el rostro con MTCNN, calcula los embeddings con FaceNet VGGFace2 congelado y guarda la plantilla (media renormalizada) en `plantillas_voluntarios.npz`. **No toca** `plantillas.npz` (las 24 del dataset). Rechaza ids que coincidan con el dataset y rutas dentro del repo fuera de `data/`. |
| Script de video | `src/video_verificacion.py` | Lee el video, procesa 1 de cada 3 fotogramas (MTCNN → 160×160 → embedding → coseno con todas las plantillas), decide con el umbral oficial **0,5514** (comprueba que es el del plan) y vota por mayoría en ventanas de 5 fotogramas. Con las anotaciones calcula FAR/FRR y la tasa sin rostro. Solo guarda agregados (el detalle por fotograma, sin imágenes, solo con `--detalle`). |
| Lógica común | `src/video.py` | Detector, privacidad, anotaciones, procesado, ventanas, métricas y tiempos. `src/pipeline.Verifier(..., voluntarios=archivo)` añade las plantillas de voluntarios a las del dataset. |
| Ensayo | `src/ensayo_video.py`, `notebooks/07_ensayo_video.ipynb` (ejecutado) | Genera un video sintético y fotos de registro con el dataset, y prueba de punta a punta los dos scripts. |
| Prueba real | `notebooks/08_video_voluntarios.ipynb` (**sin ejecutar, bloqueado**) | Ejecución única con los datos reales y las protecciones de la tarea 2.5. |
| Reglas | `plan_evaluacion.md`, sección "Prueba con video" | Fijadas antes de tener los datos. |

Parámetros fijos (`src/config.py`):
- MTCNN con margen 0 y el rostro más grande;
- 1 de cada 3 fotogramas;
- ventana de 5 fotogramas procesados, que se acepta con ≥ 3 votos;
- umbral 0,5514.

Un fotograma sin rostro cuenta como rechazo. Se reporta también la tasa sin rostro y el FRR solo con fotogramas con rostro.

## Formato de anotaciones

```
inicio_s,fin_s,identidad
0.0,12.5,V01
13.0,25.0,V02
26.0,40.0,no registrado
```

- La identidad es el seudónimo del voluntario registrado o `no registrado`. Para distinguir a varias personas no registradas se admite `no registrado A`, etc.
- Los tramos no pueden solaparse, y los fotogramas fuera de los tramos no se evalúan.
- **Comparaciones:**
  - genuina: el voluntario contra su plantilla;
  - impostora interna: un voluntario contra la plantilla de otro voluntario;
  - impostora externa: un `no registrado` contra cada plantilla de voluntario;
  - complementaria: todos contra las 24 plantillas del dataset.

## Comprobación previa: recorte MTCNN frente a `Faces` (solo VALIDACIÓN)

El umbral se fijó con los recortes de `Faces`, así que el recorte del video debe parecerse a ellos. Se tomaron 150 fotos de validación, se
recortaron sus originales con MTCNN y se compararon sus embeddings con los de su recorte de `Faces`. Archivo: `08_margen_mtcnn_validacion.csv`.

| Margen MTCNN | Detectados | Coseno mediana | p10 | Mínimo |
|---|---|---|---|---|
| **0 (elegido)** | 150/150 | **0,989** | 0,967 | −0,105 |
| 10 | 150/150 | 0,974 | 0,952 | −0,138 |
| 20 | 150/150 | 0,959 | 0,927 | −0,098 |
| 32 | 150/150 | 0,944 | 0,908 | −0,048 |
| 44 | 150/150 | 0,926 | 0,882 | −0,104 |

Con margen 0 se reproduce casi exactamente el recorte del dataset. Los mínimos negativos corresponden a fotos con varias personas, donde
MTCNN eligió como "más grande" a otro rostro. Es un riesgo también en el video real si aparece más de una persona en la imagen.

## ENSAYO (datos simulados del dataset)

Configuración del ensayo (`src/ensayo_video.py`):
- **Voluntarios simulados:** `ENSAYO_V01` = Hugh Jackman y `ENSAYO_V02` = Natalie Portman. No tienen plantilla entre las 24 y se registran con 10 fotos de *Original Images*.
- **No registrados:** `no registrado A` = Courtney Cox y `no registrado B` = Kashyap.
- **Video:** 25,9 s a 15 fps, 640×480. Cada tramo tiene 5 fotos, cada una 1,2 s con zoom, desplazamiento, ruido y brillo; la última va desenfocada (σ = 4).
- **Separación:** las fotos del video y las de registro son de grupos de casi duplicados distintos.
- **Plantillas:** se guardan en `plantillas_voluntarios_ENSAYO.npz`, distinto del archivo real.

Son fotos del dataset que ya se usaron en la prueba de la tarea 2.5, pero aquí no se evalúa nada con ellas; solo sirven para ejercitar el código.
Unas fotos fijas animadas no son un video real: no hay movimiento de la cabeza, cambios de pose dentro del tramo ni compresión de cámara.

**Lo que se verificó que funciona:**
- **Registro:** 10/10 rostros detectados por voluntario, con unos 16–19 s por voluntario (fotos de hasta 5 760 px). Las 24 plantillas del dataset siguen intactas.
- **Guardianes:** rechazan una ruta del repositorio fuera de `data/` y un id que coincide con el dataset ("Marmik"). El cuaderno real se niega a ejecutarse sin `FACEID_EJECUTAR_VIDEO=SI`.
- **Conteos coherentes:**
  - 120 fotogramas procesados (30 por tramo) y 60 comparaciones genuinas;
  - 120 externas, 60 internas y 2 880 contra el dataset;
  - 24 ventanas.
- **Privacidad:** ninguna salida de los cuadernos 07 y 08 contiene imágenes de rostros. La única figura es la de tasas agregadas.

**Cifras del ENSAYO** (`08_ENSAYO_metricas_video.csv` y `figuras/08_ENSAYO_tasas_video.png`), **solo como prueba de funcionamiento**:

| Nivel | Comparación | Errores / n | Tasa (IC 95 %) |
|---|---|---|---|
| fotograma | genuina (FRR) | 6 / 60 | 10,0 % (3,8–20,5) |
| fotograma | impostora externa (FAR) | 0 / 120 | 0 % (0–3,0) |
| fotograma | impostora interna (FAR) | 0 / 60 | 0 % (0–6,0) |
| fotograma | contra dataset (FAR) | 1 / 2 880 | 0,03 % (0,0–0,2) |
| ventana | genuina (FRR) | 1 / 12 | 8,3 % (0,2–38,5) |
| ventana | impostora externa / interna / dataset (FAR) | 0 / 24, 0 / 12, 0 / 576 | 0 % |

- Los 6 rechazos genuinos por fotograma son todos de `ENSAYO_V01` (6/30); `ENSAYO_V02` no tiene ninguno.
- La aceptación contra el dataset es de `no registrado B` (1/720).
- Tasa de fotogramas sin rostro: **0 %** (120/120 con rostro), incluso en las fotos desenfocadas. En el video real puede ser distinto: perfiles, contraluz, rostros pequeños.

**Tiempo por verificación incluyendo la detección**, con 40 fotogramas de 640×480 del ensayo (`08_ENSAYO_tiempos_con_deteccion.csv`):

| Dispositivo | Mediana | p95 | Máximo | ≤ 3 s (p95) | Proceso de una ventana (5 fotogramas) |
|---|---|---|---|---|---|
| GPU (RTX 5060) | 0,154 s | 0,186 s | 0,204 s | Sí | ≈ 0,77 s |
| CPU (i5-10400) | 0,210 s | 0,275 s | 0,308 s | Sí | ≈ 1,05 s |

- La detección con MTCNN domina el tiempo. Sin detección, la verificación tardaba 20–90 ms (tareas 2.2 y 2.5).
- Con 1 de cada 3 fotogramas a 15 fps, una ventana cubre 1 s de video.
- Al procesar el video completo, la mediana por fotograma fue de 0,143 s en GPU.

## Privacidad

- Los videos, las anotaciones y las fotos de los voluntarios deben estar **fuera del repositorio** o en `data/`, que git ignora; los scripts lo comprueban.
- Las plantillas de voluntarios van en `models/`, que git ignora. Son datos biométricos y no se comparten.
- Se usan seudónimos (`V01`…); la correspondencia con los nombres reales queda fuera del repositorio.
- En git solo hay métricas agregadas. Las figuras de video son solo de tasas, y ninguna salida de cuaderno contiene imágenes, recortes ni datos por fotograma.

## Pasos para la prueba real (cuando existan los datos)

1. Fotos de registro de cada voluntario en una carpeta privada, distintas de las del video:
   `.venv/Scripts/python -m src.registro_voluntario --fotos D:/privado/fotos/V01 --id V01` (repetir para cada voluntario).
2. Grabar el video y anotar los tramos en `D:/privado/anotaciones.csv`.
3. Commitear cualquier cambio pendiente y ejecutar **una vez** (PowerShell):
   `$env:FACEID_EJECUTAR_VIDEO = "SI"; $env:FACEID_VIDEO = "D:/privado/video.mp4"; $env:FACEID_ANOTACIONES = "D:/privado/anotaciones.csv"`
   y luego `.venv/Scripts/python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks/08_video_voluntarios.ipynb`.
4. Los agregados se guardan como `docs/sprint2/09_video_*`; el detalle por fotograma en `data/video_real/`.

## Limitaciones

- No se ha probado con video real. El ensayo usa fotos fijas animadas, sin pose cambiante, movimiento ni ruido de cámara web.
- Con pocos voluntarios los intervalos serán muy anchos.
- Si aparecen varias personas, MTCNN elige el rostro más grande.
- **No hay detección de vida**: el sistema aceptaría una foto o una pantalla con el rostro de un voluntario. No se afirma resistencia a la suplantación.
