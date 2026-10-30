# Lista de comprobación para grabar el video de los voluntarios (tarea 2.6)

El video sirve para la prueba de la tarea 2.6 y debe tratarse con el mismo cuidado que los datos biométricos:
se guarda fuera del repositorio, se identifica a las personas con seudónimos y se pide el consentimiento escrito de todos.

## Antes de grabar

| ✔ | Qué | Detalle |
|---|---|---|
| ☐ | Consentimiento | Autorización escrita y firmada de **todas** las personas que aparecen, también de las no registradas, para grabar y usar el video en el proyecto. |
| ☐ | Registro previo | Los voluntarios ya están registrados en la app (*Administración*) con su seudónimo (V01, V02…). Las fotos de registro deben ser de **otra sesión**, distinta del video: otro día, otra ropa o, como mínimo, otro momento. |
| ☐ | Cámara | Preferiblemente la misma cámara web de la demostración, fija (trípode o laptop sobre la mesa), a la altura de los ojos. |
| ☐ | Efectos desactivados | Sin filtros de belleza, desenfoque de fondo ni "encuadre automático" (Windows Studio Effects, apps de la cámara). La exposición puede quedar en automático. |
| ☐ | Resolución | **1280×720** recomendado (mínimo 640×480). |
| ☐ | Fotogramas por segundo | **30 fps** (mínimo 15). |
| ☐ | Formato | MP4 (H.264), el archivo original sin editar ni recomprimir. |
| ☐ | Luz | Luz frontal o lateral suave sobre la cara, sin ventanas detrás de la persona salvo en un tramo de contraluz a propósito. |
| ☐ | Fondo | Sin otras caras visibles (personas que pasan, carteles o fotos en la pared). |
| ☐ | Guardado | Carpeta privada fuera del repositorio, por ejemplo `D:\privado\video_voluntarios\`. Nunca en `D:\IA\FaceID` fuera de `data\`. |

## Durante la grabación

| ✔ | Qué | Detalle |
|---|---|---|
| ☐ | Una persona por tramo | Solo una cara en cuadro en cada tramo anotado. |
| ☐ | Distancia | **40–80 cm** en los tramos base: la cara debe ocupar al menos la quinta parte del alto de la imagen (unos 150 px a 720p). Por debajo de 60 px la app la considera "demasiado lejos". |
| ☐ | Postura | De frente, con movimientos suaves de cabeza (unos 15° a cada lado), parpadeo y expresión naturales. Sin gafas de sol, mascarilla ni manos en la cara (salvo un tramo de variante a propósito). |
| ☐ | Transiciones | Entre tramos, 1–2 s para que una persona salga y entre la siguiente. Esos segundos **no** se anotan. |
| ☐ | Sin nombres en voz alta | Si alguien anuncia el tramo, usar el seudónimo ("V01, luz normal"), no el nombre real. |
| ☐ | Tiempos | Anotar a mano la hora aproximada de cada cambio. Luego se ajusta con un reproductor (VLC muestra el tiempo en segundos). |

## Duración sugerida

Con las reglas de la tarea 2.6 (1 de cada 3 fotogramas y ventanas de 5), a 30 fps cada segundo da 2 ventanas de decisión.

| Tramo | Duración | Ventanas a 30 fps |
|---|---|---|
| Voluntario, condición base (luz normal, de frente, 40–80 cm) | **30 s** | 60 |
| Voluntario, cada variante (lentes, a 1 m, poca luz o contraluz) | **15 s** | 30 |
| Persona no registrada, cada tramo | **20 s** | 40 |
| Mínimo por tramo (el validador avisa por debajo) | 5 s | 10 |

- **Por voluntario:** unos 45–60 s (base más 1 o 2 variantes). Hacen falta **al menos 2 voluntarios**, para medir también a un registrado
  haciéndose pasar por otro.
- **No registrados:** **al menos 2 personas distintas**, idealmente 3 o más, de unos 20 s cada una. Se anotan como `no registrado A`,
  `no registrado B`…
- **Total orientativo:** de 3 a 6 minutos de video.

## Anotaciones

1. Copiar la plantilla `docs/sprint3/plantilla_anotaciones.csv` a la carpeta privada y rellenarla:
   - columnas `inicio_s,fin_s,identidad,condicion`, con los tiempos en segundos desde el inicio del video;
   - en `identidad`, el seudónimo registrado en la app o `no registrado` (con letra si hay varios);
   - `condicion` es opcional y solo sirve para documentar.
2. Empezar cada tramo cuando la persona ya está quieta en su sitio y terminarlo antes de que se mueva para salir. Los tramos no pueden solaparse.
3. **Validar sin calcular métricas** (no carga el modelo):
   ```
   .venv/Scripts/python -m src.validar_video --video D:/privado/video_voluntarios/video.mp4 --anotaciones D:/privado/video_voluntarios/anotaciones.csv --almacen-app $env:USERPROFILE\FaceID_privado
   ```
   Corregir hasta que diga **VÁLIDO** y revisar los avisos. Si duda de la duración del video, añada `--contar`.
4. Solo entonces, y con todo commiteado, se ejecuta **una sola vez** la evaluación de la tarea 2.6 (`notebooks/08_video_voluntarios.ipynb`,
   con `FACEID_ALMACEN_APP`). Ver `docs/sprint2/plan_evaluacion.md`.
