# Tarea 2.2 — Entrenamiento del modelo

Fecha: 2026-10-23. Estado: **pendiente de visto bueno**. Cuaderno: `notebooks/04_entrenamiento.ipynb` (ejecutado completo, sin errores).
Código nuevo: `src/pipeline.py` (exportación, paquete y verificador). **El conjunto de prueba no se cargó.**

## Qué se entrenó y por qué

**Modelo elegido: FaceNet InceptionResnetV1 (VGGFace2), preentrenado y congelado.** Sin ajuste fino, "entrenar" equivale al **registro
(enrolamiento)**: la plantilla de cada una de las 24 registradas es la media de los embeddings de sus fotos de *train* (de 22 a 84 fotos por
persona, mediana 54), renormalizada. Este modelo **no tiene curvas de entrenamiento**, porque no se actualiza ningún peso.

No se hizo ajuste fino, por tres motivos:
1. La validación ya está saturada (EER 0,00 %), así que no podría mostrar si un ajuste mejora o empeora.
2. Con 1 362 fotos de 24 personas, el ajuste especializaría la red en esas personas. Es lo que se vio en (a1) y (a2), que llegan a casi 100 % en train y sobreajustan.
3. Con la red congelada, registrar un usuario nuevo no requiere reentrenar.

**Modelo de control: (a2) ResNet-18 ImageNet**, para evaluar en prueba el sesgo de famosos (acordado). Se usaron los mismos hiperparámetros
fijos de la tarea 2.1 (AdamW + OneCycle, lr 3e-4, 40 épocas, lote 64, label smoothing 0,1, weight decay 5e-4, mismo aumento de datos) y se
guarda la última época.

## Modelos guardados (formato reutilizable)

Están en `models/`, que git ignora (contienen pesos y plantillas biométricas). Cada paquete se carga con `src.pipeline.Verifier(carpeta)`,
**sin necesitar facenet-pytorch**:

| Paquete | Archivos | Contenido |
|---|---|---|
| `models/verificador_facenet_vggface2/` | `red.ts` (112,9 MB, TorchScript), `plantillas.npz` (24×512), `config.json` | preprocesado, métrica, pesos de origen con SHA-256, versiones, fotos de registro por usuario, `umbral: null` |
| `models/control_resnet18_imagenet/` | `red.ts` (45,0 MB), `pesos_entrenados.pt` (state_dict), `plantillas.npz` (24×512), `config.json` | ídem + hiperparámetros |

Comprobaciones:
- La exportación a TorchScript coincide con la red original: diferencia máxima 3,1e-5 en FaceNet y 0 en el control.
- Al recargar el paquete de FaceNet se reproduce la validación de la tarea 2.1: EER 0,00 % y AUC 1,0000, tanto en GPU como en CPU. La diferencia
  máxima de puntuaciones con 2.1 es de 1,5e-4 en GPU y 5,3e-4 en CPU (redondeo numérico).
- Control (a2) recargado: EER en validación 3,55 % y AUC 0,9929, igual que en la tarea 2.1.
- Pesos de origen de FaceNet: `20180402-114759-vggface2.pt`, SHA-256 `281cebca8662831a…` (el hash completo está en `config.json`); 27,91 M parámetros.
- El umbral queda **vacío a propósito**: se fija en la tarea 2.3 con validación.

## Tiempos (RTX 5060 / i5-10400)

Archivos `04_tiempos_facenet.csv` y `04_resumen_entrenamiento.json`. Medianas, con el p95 entre paréntesis.

| Medida (FaceNet) | GPU | CPU |
|---|---|---|
| Verificación 1 a 1 (leer JPG + embedding + coseno) | 18,1 ms (p95 27,5) | 88,6 ms (p95 246,3) |
| Embedding por imagen, en lotes de 64 | 0,51 ms | 34,6 ms |
| Registro de un usuario (54 fotos, con lectura de disco) | 0,18 s (máx. 0,53 s) | 2,22 s (máx. 3,23 s) |
| Registro de las 24 identidades (imágenes ya en memoria) | 1,39 s | — |
| Carga del paquete | 1,0–2,6 s | 0,65–1,4 s |

La carga del paquete se midió dos veces y salió distinta; la primera carga en GPU incluye la inicialización de CUDA.

| Control (a2) | Valor |
|---|---|
| Entrenamiento (40 épocas, 1 362 imágenes, GPU) | 72 s |
| Exactitud de clasificación final: train / validación | 1,000 / 0,970 |

Todas las verificaciones están muy por debajo del objetivo de 3 s. No incluyen la detección de rostro, que se medirá en la tarea 2.6.

## Figuras

- `figuras/04_similitud_plantillas.png`: coseno entre las 24 plantillas de FaceNet. Fuera de la diagonal, la media es 0,04 y el máximo 0,54
  (Hrithik Roshan – Vijay Deverakonda). Es el par de registrados más difícil de distinguir.
- `figuras/04_curvas_control_a2.png`: pérdida y exactitud de train/validación del control (a2). Converge hacia la época 10–15; la
  diferencia train/val (1,000 frente a 0,970) indica algo de sobreajuste.
- Las curvas de (a1) y (a2) de la tarea 2.1 siguen en `figuras/03_curvas_entrenamiento_a.png`.

## Observaciones

- La primera verificación tras cargar el modelo es más lenta. Por eso todas las medidas descartan 5 repeticiones de calentamiento.
- En CPU el p95 de la verificación (246 ms) es bastante mayor que la mediana: hay picos esporádicos del sistema operativo o de la lectura de disco.
- `models/` también conserva los modelos de la tarea 2.1 (`tarea21_*.pt`), como evidencia de la comparación.
