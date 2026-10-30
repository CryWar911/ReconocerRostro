# Plan de evaluación con el conjunto de PRUEBA (tarea 2.5), fijado de antemano

Fecha: 2026-10-23. Se escribe y commitea **antes** de la tarea 2.3 y **antes de ver ningún resultado de prueba**. Hasta este momento el
conjunto de prueba no se ha cargado en ningún cuaderno (01–04). Las reglas son del usuario; los detalles de procedimiento que las
concretan van marcados como *(procedimiento)*.

## Reglas

1. **El modelo final es FaceNet InceptionResnetV1 (VGGFace2), congelado**, con plantilla por usuario y similitud. Se decidió en las tareas 2.1
   y 2.2. **El resultado de la prueba no puede cambiar esa elección.** Si no alcanzara los objetivos, se reporta tal cual y se propone volver a la
   fase de modelado, pero no se cambia de modelo a la vista de la prueba.
2. **Se reportan los dos modelos en prueba, sea cual sea el resultado:** FaceNet VGGFace2 (final) y el control (a2) ResNet-18 ImageNet
   (`models/control_resnet18_imagenet/`), que sirve para estudiar el sesgo de famosos.
3. **Desglose por grupo:**
   - Marmik (registrada no famosa) frente a las demás registradas.
   - Kashyap (impostora no famosa) frente a las demás impostoras.
   - Cada uno es **una sola persona**: Marmik tiene 5 fotos genuinas en prueba y Kashyap 30 fotos. El desglose es una **señal cualitativa y no permite
     conclusiones firmes** sobre el sesgo de famosos.
4. **Las comparaciones impostoras son de dos tipos**, y se reportan por separado y juntas:
   - **Externas:** personas NO registradas (las 4 impostoras de prueba: Courtney Cox, Hugh Jackman, Kashyap, Natalie Portman) contra las
     24 plantillas, es decir 327 × 24 = 7 848 comparaciones.
   - **Internas:** usuarios registrados haciéndose pasar por OTRO registrado (fotos de prueba de cada registrada contra las otras 23
     plantillas), es decir 299 × 23 = 6 877 comparaciones.
   - Las comparaciones **genuinas** son cada foto de prueba de una registrada contra su propia plantilla: 299.

## Umbrales fijados (actualización del 2026-10-23, tras la tarea 2.3 y antes de la prueba)

Estos umbrales salen **solo de validación**, aplicando la regla fijada antes de calcularlos: el mayor umbral con FAR ≤ 0,1 %
(impostoras externas + internas) en cada una de las 18 condiciones. Detalle en `05_validacion_ajuste.md`.

| Modelo | Umbral | Papel en la prueba |
|---|---|---|
| FaceNet VGGFace2 (final) | **0,5514** | **Umbral oficial.** Las métricas y la comparación con los objetivos se hacen con este umbral. |
| FaceNet VGGFace2 (final) | 0,595 | Punto de operación **secundario**, solo para reportar (centro del hueco de validación limpia). No sirve para declarar que se cumplen los objetivos. |
| Control (a2) ResNet-18 ImageNet | 0,8769 | Solo se reporta, como control del sesgo de famosos. |

- **En prueba no se recalcula ningún umbral**, y la elección del oficial **no cambia según los resultados**: aunque 0,595 diera mejores números
  en prueba, el oficial sigue siendo 0,5514.
- El EER de prueba y su umbral se reportan como descripción, nunca como umbral de trabajo.

## Procedimiento *(procedimiento)*

- **Umbral:** se usa el umbral fijado en la tarea 2.3 **con validación** y guardado en el `config.json` de cada paquete. En prueba **no se
  recalcula ni se ajusta ningún parámetro**. El EER y la ROC de prueba se reportan como descripción, no para elegir el umbral.
- **Plantillas:** las mismas de la tarea 2.2 (solo fotos de train). Si en la tarea 2.3 se adopta otra estrategia de plantilla, se reconstruye
  con train y se documenta antes de la prueba.
- **Una sola ejecución:** el cuaderno de prueba se ejecuta una vez sobre un commit identificado. Si hubiera un error de código, se corrige y
  se vuelve a ejecutar, documentando el motivo, pero sin cambiar modelo, umbral ni plantillas.
- **Métricas que se reportan** (definiciones y objetivos en `06_metricas.md`, tarea 2.4):
  - FAR, FRR, exactitud **balanceada**, exactitud simple y proporción genuinas/impostoras, en el umbral fijado;
  - matriz de confusión (aceptado/rechazado frente a genuino/impostor);
  - ROC, AUC y EER;
  - tiempo por verificación;
  - todo ello para los impostores externos, internos y todos juntos, y con el desglose de la regla 3.
- **Limitaciones que se mantienen en el informe:**
  - solo hay 4 identidades impostoras externas en prueba;
  - probable sesgo de famosos en el preentrenamiento de FaceNet;
  - no hay detección de vida (no se afirma resistencia a fotos o vídeos de suplantación).

## Prueba con video de voluntarios (tarea 2.6), fijada antes de tener los datos (2026-10-23)

- **Ejecución única** del cuaderno `notebooks/08_video_voluntarios.ipynb` con los datos reales, con las mismas protecciones que la prueba:
  - no se ejecuta sin `FACEID_EJECUTAR_VIDEO=SI`;
  - exige el árbol limpio y registra el commit;
  - pide `FACEID_MOTIVO_REEJECUCION` si ya hay resultados.

  Antes se ensayó el mismo código con datos simulados (`notebooks/07_ensayo_video.ipynb`); esas cifras de ensayo **no** son resultados.
- **Modelo y decisión fijos:**
  - FaceNet VGGFace2 congelado, umbral oficial **0,5514** (no se recalcula);
  - detección MTCNN con margen 0, elegido solo con imágenes de validación porque es el que reproduce el recorte de `Faces`;
  - se procesa 1 de cada 3 fotogramas;
  - decisión por **ventana de 5 fotogramas procesados con votación por mayoría** (al menos 3 de 5 con rostro y puntuación ≥ umbral), la variante propuesta en la tarea 2.3.
- **Registro:** plantilla = media de los embeddings de las fotos de registro de cada voluntario (`src/registro_voluntario.py`). Se guarda en
  `plantillas_voluntarios.npz`, separada de las 24 del dataset, que no se modifican. Las fotos de registro deben ser distintas del video.
- **Anotaciones:** CSV con `inicio_s, fin_s, identidad`, donde la identidad es el seudónimo del voluntario o `no registrado`. Solo se evalúan los fotogramas dentro de un tramo.
- **Comparaciones** (mismo protocolo que en prueba):
  - genuina: fotograma o ventana de un voluntario contra su plantilla;
  - impostora interna: voluntario contra la plantilla de otro voluntario;
  - impostora externa: `no registrado` contra cada plantilla de voluntario;
  - complementaria: todos contra las 24 plantillas del dataset.
- **Métricas:**
  - FAR y FRR por fotograma y por ventana, desglosados por voluntario, con IC de Clopper-Pearson;
  - tasa de fotogramas sin rostro (un fotograma sin rostro cuenta como rechazo; también se da el FRR solo con fotogramas con rostro);
  - tiempo por verificación **incluyendo la detección**, en GPU y CPU (mediana y p95), comparado con el objetivo de 3 s.
- **Privacidad:**
  - el video, las anotaciones y las fotos se guardan fuera del repositorio (o en `data/`), y los voluntarios se identifican con seudónimos;
  - en git, figuras y salidas de cuadernos **solo** hay métricas agregadas: ninguna imagen, recorte ni dato por fotograma;
  - el detalle por fotograma (sin imágenes) queda en `data/video_real/`, fuera de git.
- **Limitación:** con pocos voluntarios y pocos minutos de video, los intervalos serán muy anchos; se reportan tal cual.
