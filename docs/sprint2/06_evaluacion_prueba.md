# Tarea 2.5 — Evaluación con el conjunto de PRUEBA (ejecución única)

Fecha: 2026-10-23. Cuaderno ejecutado: `notebooks/06_evaluacion_prueba.ipynb`. Reglas: `plan_evaluacion.md`. Métricas: `06_metricas.md`.

**Registro de la ejecución** (`07_resultados_prueba.json`):
- código evaluado: commit `0a27e3db0d5053a9976d21f97fbb1dafd76c949c`, árbol limpio;
- inicio 11:57:40 y fin 11:58:42;
- **una sola ejecución, sin errores y sin re-ejecución** (`motivo_reejecucion: null`).

No se modificó modelo, umbral ni plantillas, y no se ajustó nada a la vista de los resultados. Los resultados se reportan tal cual.

Las tablas y figuras de la prueba llevan el prefijo `07_`, que es el número que usa el cuaderno al guardarlas. Este documento resume esos archivos.

## Qué se evaluó

| Modelo | Punto de operación | Papel |
|---|---|---|
| FaceNet VGGFace2 congelado (final) | **0,5514 (oficial)** | se compara con los objetivos |
| FaceNet VGGFace2 congelado (final) | 0,595 (secundario) | solo se reporta |
| Control (a2) ResNet-18 ImageNet | 0,8769 | solo se reporta (control del sesgo de famosos) |

Comparaciones en prueba:
- **299 genuinas**: las 24 registradas, cada una contra su plantilla.
- **7 848 impostoras externas**: Courtney Cox, Hugh Jackman, Kashyap y Natalie Portman contra las 24 plantillas.
- **6 877 impostoras internas**: cada registrada contra las otras 23 plantillas.

En total hay 14 725 impostoras; las genuinas son el 1,99 % de las comparaciones.

## Resultados principales

Archivo: `07_metricas_prueba.csv`. El IC 95 % es de Clopper-Pearson. En las impostoras es optimista, porque cada foto se compara con 23 o 24 plantillas y esas comparaciones no son independientes.

| Modelo / umbral | Impostoras | FA / n | **FAR** (IC 95 %) | FR / n | **FRR** (IC 95 %) | **Exactitud balanceada** | Exactitud simple | EER (descr.) | AUC |
|---|---|---|---|---|---|---|---|---|---|
| **FaceNet, oficial 0,5514** | externas | 3 / 7 848 | 0,038 % (0,008–0,112) | 3 / 299 | 1,00 % (0,21–2,90) | 99,48 % | 99,93 % | 0,36 % | 0,99995 |
| | internas | 3 / 6 877 | 0,044 % (0,009–0,127) | 3 / 299 | 1,00 % | 99,48 % | 99,92 % | 0,65 % | 0,99989 |
| | **todas** | **6 / 14 725** | **0,041 %** (0,015–0,089) | **3 / 299** | **1,00 %** (0,21–2,90) | **99,48 %** | 99,94 % | 0,67 % | 0,99992 |
| FaceNet, secundario 0,595 | externas | 1 / 7 848 | 0,013 % (0,000–0,071) | 5 / 299 | 1,67 % (0,55–3,86) | 99,16 % | 99,93 % | 0,36 % | 0,99995 |
| | internas | 1 / 6 877 | 0,015 % (0,000–0,081) | 5 / 299 | 1,67 % | 99,16 % | 99,92 % | 0,65 % | 0,99989 |
| | todas | 2 / 14 725 | 0,014 % (0,002–0,049) | 5 / 299 | 1,67 % (0,55–3,86) | 99,16 % | 99,95 % | 0,67 % | 0,99992 |
| Control (a2), 0,8769 | externas | 12 / 7 848 | 0,153 % (0,079–0,267) | 80 / 299 | **26,76 %** (21,82–32,16) | 86,55 % | 98,87 % | 5,30 % | 0,98862 |
| | internas | 0 / 6 877 | 0,000 % (0,000–0,054) | 80 / 299 | 26,76 % | 86,62 % | 98,89 % | 1,71 % | 0,99808 |
| | todas | 12 / 14 725 | 0,081 % (0,042–0,142) | 80 / 299 | 26,76 % (21,82–32,16) | 86,58 % | 99,39 % | 3,99 % | 0,99304 |

Matrices de confusión con todas las impostoras (`figuras/07_matrices_confusion_prueba.png`):

| | FaceNet 0,5514: aceptada | rechazada | FaceNet 0,595: aceptada | rechazada | Control 0,8769: aceptada | rechazada |
|---|---|---|---|---|---|---|
| Genuina | 296 | 3 | 294 | 5 | 219 | 80 |
| Impostora | 6 | 14 719 | 2 | 14 723 | 12 | 14 713 |

## Tabla de objetivos

Umbral oficial de FaceNet con todas las impostoras. Los objetivos están **pendientes de confirmar con el docente**. Archivo: `07_objetivos_prueba.csv`.

| Métrica | Valor en prueba | Objetivo | ¿Cumple? |
|---|---|---|---|
| FAR | 0,041 % (6 / 14 725) | ≤ 5 % | Sí |
| FRR | 1,00 % (3 / 299) | ≤ 10 % | Sí |
| Exactitud balanceada | 99,48 % | ≥ 90 % | Sí |
| Tiempo por verificación (p95, CPU) | 0,073 s | ≤ 3 s | Sí (sin detección de rostro) |
| Exactitud simple (informativa) | 99,94 % | — | — |
| Proporción de genuinas | 1,99 % | — | — |
| EER (descriptivo) | 0,67 % | sin objetivo | — |

El control (a2) **no cumpliría** el FRR ≤ 10 % (26,8 %) ni la exactitud balanceada ≥ 90 % (86,6 %). No se le aplican objetivos; se muestra solo como referencia.

**Tiempos** (`07_tiempos_prueba.csv`; leer el JPG, calcular el embedding, comparar y decidir; mediana / p95):
- FaceNet: 20 / 41 ms en GPU y 62 / 73 ms en CPU.
- Control: 6 / 8 ms en GPU y 51 / 85 ms en CPU.

## Comparación con validación (FaceNet, umbral oficial, todas las impostoras)

Archivo: `07_validacion_vs_prueba.csv`.

| Conjunto | FAR | FRR | Genuina mínima | Impostora máxima |
|---|---|---|---|---|
| Validación (2.3, imágenes limpias) | 0,052 % (7 / 13 471) | 0,00 % (0 / 305) | 0,607 | 0,583 |
| **Prueba** | 0,041 % (6 / 14 725) | **1,00 % (3 / 299)** | **0,402** | **0,628** |

- En prueba las genuinas y las impostoras **ya no están separadas del todo**. La genuina más baja (0,402) queda por debajo de la impostora más alta (0,628),
  mientras que en validación había un pequeño hueco.
- El EER pasa de 0,00 % en validación a 0,67 % en prueba. Validación estaba saturada, como ya se advirtió en las tareas 2.1 y 2.3.
- En el control (a2), el FRR pasa del 22,0 % en validación al 26,8 % en prueba, y el FAR de 0,074 % a 0,081 %.

## Desglose: Marmik y Kashyap

> **Advertencia:** cada grupo es **una sola persona**. Marmik tiene 5 comparaciones genuinas. Kashyap tiene 720 comparaciones impostoras, pero
> salen de solo 30 fotos de una persona. Esto **no permite conclusiones firmes** sobre el sesgo de famosos.

Archivo: `07_desglose_marmik_kashyap.csv`.

| Modelo / umbral | Grupo | Métrica | Errores / n | Tasa (IC 95 %) | Puntuación mín. / mediana / máx. |
|---|---|---|---|---|---|
| FaceNet 0,5514 | genuinas **Marmik** | FRR | 0 / 5 | 0 % (0–52,2) | 0,660 / 0,773 / 0,881 |
| | genuinas demás registradas | FRR | 3 / 294 | 1,02 % (0,21–2,95) | 0,402 / 0,868 / 0,963 |
| | impostora externa **Kashyap** | FAR | **2 / 720** | **0,278 %** (0,03–1,00) | −0,337 / 0,058 / **0,628** |
| | demás impostoras externas | FAR | 1 / 7 128 | 0,014 % (0,00–0,08) | −0,407 / 0,040 / 0,594 |
| | Marmik haciéndose pasar por otra | FAR | 0 / 115 | 0 % (0–3,16) | −0,319 / 0,015 / 0,369 |
| | internas demás registradas | FAR | 3 / 6 762 | 0,044 % (0,01–0,13) | −0,488 / 0,033 / 0,596 |
| FaceNet 0,595 | genuinas Marmik | FRR | 0 / 5 | 0 % | ídem |
| | genuinas demás | FRR | 5 / 294 | 1,70 % (0,55–3,92) | ídem |
| | impostora Kashyap | FAR | 1 / 720 | 0,139 % (0,00–0,77) | ídem |
| | demás impostoras externas | FAR | 0 / 7 128 | 0 % (0–0,05) | ídem |
| | Marmik como impostora interna | FAR | 0 / 115 | 0 % | ídem |
| | internas demás | FAR | 1 / 6 762 | 0,015 % | ídem |
| Control 0,8769 | genuinas Marmik | FRR | **2 / 5** | 40 % (5,3–85,3) | 0,701 / 0,911 / 0,936 |
| | genuinas demás | FRR | 78 / 294 | 26,5 % (21,6–32,0) | 0,569 / 0,926 / 0,979 |
| | impostora Kashyap | FAR | 0 / 720 | 0 % (0–0,51) | 0,397 / 0,613 / 0,868 |
| | demás impostoras externas | FAR | 12 / 7 128 | 0,168 % (0,09–0,29) | 0,429 / 0,608 / 0,912 |
| | Marmik como impostora interna | FAR | 0 / 115 | 0 % | 0,463 / 0,560 / 0,743 |
| | internas demás | FAR | 0 / 6 762 | 0 % | 0,406 / 0,549 / 0,842 |

Hechos observados, sin generalizar:
- Con FaceNet, **las 2 aceptaciones de Kashyap son contra la plantilla de Marmik**: Kashyap_25 con 0,628 y Kashyap_17 con 0,566. Es decir, el único
  impostor no famoso fue aceptado como el único registrado no famoso. Su FAR (0,278 %) es unas 20 veces el del resto de impostoras externas
  (0,014 %), pero son 2 casos.
- En el control (a2), Kashyap no tiene ninguna aceptación, y Marmik sí tiene 2 rechazos de 5.

## Errores por identidad

Archivo completo: `07_por_identidad_prueba.csv`. Aquí solo las identidades con algún error.

**FaceNet, umbral oficial 0,5514:**

| Persona | Tipo | Errores / n | Tasa | Puntuación extrema |
|---|---|---|---|---|
| Billie Eilish | registrada (FRR) | 2 / 15 | 13,3 % | mín. 0,436 |
| Zac Efron | registrada (FRR) | 1 / 14 | 7,1 % | mín. 0,402 |
| Kashyap | impostora externa (FAR) | 2 / 720 | 0,278 % | máx. 0,628 |
| Courtney Cox | impostora externa (FAR) | 1 / 1 920 | 0,052 % | máx. 0,594 |
| (internas) | ver casos extremos | 3 / 6 877 | 0,044 % | máx. 0,596 |

Las otras 22 registradas no tienen ningún rechazo. Hugh Jackman y Natalie Portman no tienen ninguna aceptación.

**Control (a2):**
- Tiene rechazos en 22 de las 24 registradas; solo Amitabh Bachchan y Margot Robbie no tienen ninguno. Los peores son Akshay Kumar (5/8, 62,5 %), Anushka Sharma (6/10, 60 %), Billie Eilish (8/15, 53,3 %) y
  Charlize Theron (6/12, 50 %).
- Sus aceptaciones externas son de Courtney Cox (6/1 920), Natalie Portman (4/2 520) y Hugh Jackman (2/2 688).

## Casos extremos (FaceNet)

Archivo: `07_casos_extremos_facenet_prueba.csv`. Las comparaciones aceptadas o rechazadas por error con el umbral oficial van en **negrita**.

| Tipo | Foto | Persona real | Dice ser | Puntuación |
|---|---|---|---|---|
| externa | **Kashyap_25** | Kashyap | Marmik | **0,628** (aceptada también con 0,595) |
| externa | **Courtney Cox_58** | Courtney Cox | Charlize Theron | **0,594** |
| externa | **Kashyap_17** | Kashyap | Marmik | **0,566** |
| externa | Kashyap_22 | Kashyap | Marmik | 0,533 |
| externa | Hugh Jackman_63 | Hugh Jackman | Robert Downey Jr | 0,529 |
| interna | **Vijay Deverakonda_17** | Vijay Deverakonda | Hrithik Roshan | **0,596** (aceptada también con 0,595) |
| interna | **Hrithik Roshan_93** | Hrithik Roshan | Akshay Kumar | **0,563** |
| interna | **Vijay Deverakonda_77** | Vijay Deverakonda | Hrithik Roshan | **0,561** |
| interna | Anushka Sharma_3 | Anushka Sharma | Alia Bhatt | 0,551 |
| interna | Vijay Deverakonda_74 | Vijay Deverakonda | Hrithik Roshan | 0,548 |
| genuina | **Zac Efron_32** | Zac Efron | Zac Efron | **0,402** |
| genuina | **Billie Eilish_34** | Billie Eilish | Billie Eilish | **0,436** |
| genuina | **Billie Eilish_66** | Billie Eilish | Billie Eilish | **0,467** |
| genuina | Charlize Theron_37 | Charlize Theron | Charlize Theron | 0,584 (rechazada con 0,595) |
| genuina | Anushka Sharma_37 | Anushka Sharma | Anushka Sharma | 0,593 (rechazada con 0,595) |

En la tabla hay 5 de las 10 impostoras más altas de cada tipo; la lista completa está en el CSV. El par Hrithik Roshan / Vijay Deverakonda, ya señalado en
validación, vuelve a aparecer en las impostoras internas, ahora sobre todo en el sentido Vijay → Hrithik.

## Figuras

- `figuras/07_matrices_confusion_prueba.png`: matrices de confusión de los tres puntos de operación.
- `figuras/07_roc_det_prueba.png`: ROC y DET con los puntos de operación fijados. En la DET, los puntos con FAR = 0 se dibujan en 10⁻³ % porque la escala log
  no admite el 0; eso produce el tramo vertical de la izquierda. Las etiquetas "oficial" y "secundario" quedan muy juntas.
- `figuras/07_distribucion_puntuaciones_prueba.png`: histogramas de puntuaciones genuinas, impostoras externas e internas, con los umbrales.

## Limitaciones (se mantienen en el informe)

- Solo hay **4 identidades impostoras externas** en prueba. Las 7 848 comparaciones salen de 327 fotos de 4 personas.
- **Probable sesgo de famosos:** FaceNet se preentrenó con VGGFace2, una colección de celebridades. Marmik y Kashyap son solo una persona cada uno.
- Los intervalos de FAR son optimistas, porque las comparaciones no son independientes.
- El tiempo no incluye la detección de rostro; se medirá en la tarea 2.6.
- Las fotos son de prensa: buena iluminación y mayoría frontales, distintas de una cámara web real.
- **No hay detección de vida**: no se afirma resistencia a la suplantación con fotos o vídeos.
