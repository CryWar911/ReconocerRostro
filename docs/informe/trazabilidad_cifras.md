# Trazabilidad de las cifras del Informe del Sprint 2

Documento: `docs/informe/Informe_Sprint2_APA7.docx` (21 páginas). Cada cifra del informe se indica con el archivo del que sale.
Las rutas son relativas a `docs/sprint2/`, salvo que se indique otra cosa.

## Resumen

| Cifra en el informe | Fuente |
|---|---|
| 2 562 imágenes, 31 personas, 24 registradas / 7 impostoras | `01_02_preparacion_datos.md` (Dataset; Sorteo final) |
| Umbral oficial 0,5514; FAR objetivo 0,1 % | `05_validacion_ajuste.md` §3; `05_umbral_propuesto.json` |
| Prueba: FAR 0,041 %, FRR 1,00 %, exactitud balanceada 99,48 % | `07_metricas_prueba.csv` (FaceNet, oficial, todas); `06_evaluacion_prueba.md` |
| FRR 0 % → 1,00 %; EER 0 % → 0,67 % | `07_validacion_vs_prueba.csv`; `03_comparacion_validacion.csv` (EER b1 = 0); `07_metricas_prueba.csv` (EER 0,006706) |

## Recomendaciones del docente y tareas

| Cifra | Fuente |
|---|---|
| Fechas del Gantt y de la Tabla 2 (12/10–14/10 … 22/10–23/10), historias HU05–HU08 | Enunciado del usuario para el informe (plan del Sprint 2); coinciden con la Tabla 9 del Informe del Sprint 1 |
| Duraciones del Gantt (3, 5, 4, 2, 2, 2 días) | Calculadas de esas fechas (inicio y fin inclusive) en `docs/informe/gantt_sprint2.py` |
| "Los documentos de resultados llevan fecha del 23 de octubre de 2026" | Cabeceras "Fecha: 2026-10-23" de `00_revision_previa.md`, `01_02_preparacion_datos.md`, `03_*.md` a `06_*.md` |

## Fases 2 y 3

| Cifra | Fuente |
|---|---|
| Entre 30 (Kashyap) y 120 (Brad Pitt) imágenes por persona, media 82,6 | `00_revision_previa.md` §2 |
| Recortes de 160 × 160; normalización (x − 127,5)/128; semilla 42 | `01_02_preparacion_datos.md` (Preprocesado; División) |
| Correlación 32 × 32, umbral 0,90; 93 grupos, 230 imágenes, mayor de 12 | `01_02_preparacion_datos.md` (Casi duplicados) |
| 178 pares residuales con correlación 0,85–0,90 | `01_02_preparacion_datos.md` (Riesgo residual) |
| 69,3 % / 15,5 % / 15,2 % | `01_02_preparacion_datos.md` (Sorteo final) |
| Tabla 3 (12 M / 12 F; 2 M / 1 F; 2 M / 2 F; identidades; sorteo descartado) | `01_02_preparacion_datos.md` (Sorteo descartado y final) |
| Tabla 4: 1 362 / 305 / 269 / 574 / 299 / 327 / 626; 1 966 / 596 / 2 562 | `02_conteos_por_conjunto.csv`; `01_02_preparacion_datos.md` |
| Tabla 4: 6 456 / 7 015 / 7 848 / 6 877 comparaciones | `05_impostores_internos.csv` (n_ext, n_int); `06_metricas.md` (Unidad de evaluación) |

## Fase 4: Modelado

| Cifra | Fuente |
|---|---|
| Python 3.10.4, PyTorch 2.11.0 (CUDA 12.8), OpenCV 5.0.0, scikit-learn 1.7.2, facenet-pytorch 2.6.0; i5-10400, 16 GB, RTX 5060 8 GB; torch < 2.3 | `01_02_preparacion_datos.md` (Entorno) |
| Tabla 5 (EER, AUC, FAR, FRR, tiempos GPU/CPU de las 5 variantes); 305 genuinas y 6 456 impostoras | `03_comparacion_validacion.csv`; `03_seleccion_tecnica.md` |
| Regla del tres: FRR ≤ ≈ 1,0 %, FAR ≤ ≈ 0,05 % | `03_seleccion_tecnica.md` (Notas sobre b1) |
| 29 personas famosas | `00_revision_previa.md`; `01_02_preparacion_datos.md` |
| 1 362 fotos de 24 personas; de 22 a 84 fotos por persona; 512 valores por plantilla | `04_entrenamiento.md` |
| Control (a2): lr 3e-4, 40 épocas, lote 64, label smoothing 0,1, weight decay 5e-4; 72 s; 1,000 / 0,970 | `04_entrenamiento.md`; `04_resumen_entrenamiento.json`; `04_historial_control_a2.csv` |
| Tabla 6 (18,1 ms (27,5); 88,6 ms (246,3); 0,51 ms; 34,6 ms; 0,18 s (0,22); 2,22 s (2,90)) | `04_tiempos_facenet.csv` |
| Similitud entre plantillas: media 0,04, máximo 0,54 (Hrithik Roshan – Vijay Deverakonda) | `04_entrenamiento.md` (Figuras) |
| 7 015 internos; impostora máx. 0,511 → 0,583; margen 0,096 → 0,024; genuina mínima 0,607 | `05_impostores_internos.csv`; `05_validacion_ajuste.md` §1 |
| 13 471 impostoras; 18 condiciones; 17 perturbaciones | `05_validacion_ajuste.md` §2–3 |
| Tabla 7 (0,6070 / 0,5950 / 0,5469 / 0,5514; FAR y FRR limpia; FAR peor; FRR medio) | `05_umbrales_resumen.csv` (FaceNet) |
| Lo fija la rotación de +15° | `05_umbrales_resumen.csv` (cond_FAR_peor); `05_validacion_ajuste.md` §3 |
| FAR 0,052 % = 7 de 13 471 (6 Hrithik → Vijay, 1 Akshay → Hrithik); margen 0,056 | `05_validacion_ajuste.md` §3 |
| Secundario 0,595: FRR medio con perturbaciones 6,94 % | `05_umbrales_resumen.csv` (centro del hueco limpio) |
| Control: umbral 0,8769; FRR limpia 22,0 % | `05_umbrales_resumen.csv` (Control, PROPUESTO) |
| Tabla 8 (caída media, genuina mínima, FAR, FRR por condición) | `05_robustez.csv` (FaceNet); `05_validacion_ajuste.md` §2 |
| Tabla 9 (EER limpia, FRR limpia, FRR medio, FRR peor por estrategia) | `05_estrategias_plantilla.csv` (FaceNet) |
| Fotogramas: FRR 0,21 % → 0,00 %; FAR 0,064 % / 0,032 % / 0,000 %; 0,160 %; 1–5 de 3 120 | `05_agregacion_fotogramas.csv`; `05_validacion_ajuste.md` §5 |

## Fase 5: Evaluación

| Cifra | Fuente |
|---|---|
| 14 725 impostoras, 299 genuinas, unas 49 por genuina, 2,0 %; 98,0 % y 50 % del sistema que rechaza todo | `06_metricas.md` (Por qué exactitud balanceada) |
| Tabla 10 (definiciones; objetivos ≤ 5 %, ≤ 10 %, ≥ 90 %, ≤ 3 s) | `06_metricas.md` (Definiciones) |
| Ejecución única, árbol limpio | `06_evaluacion_prueba.md` (Registro de la ejecución); `07_resultados_prueba.json` |
| Tabla 11 (FA/n, FAR, IC, FR/n, FRR, IC, exactitud balanceada, EER de los 3 puntos de operación) | `07_metricas_prueba.csv`; `06_evaluacion_prueba.md` (Resultados principales) |
| AUC 0,99992 (FaceNet) y 0,99304 (control); exactitud simple 99,94 %; genuinas 1,99 % | `07_metricas_prueba.csv`; `07_objetivos_prueba.csv` |
| Tabla 12 (0,041 %, 1,00 %, 99,48 %, 0,073 s) | `07_objetivos_prueba.csv` |
| Mediana del tiempo: 20 ms GPU, 62 ms CPU | `07_tiempos_prueba.csv` (FaceNet) |
| Control: FRR 26,76 %, exactitud balanceada 86,58 % | `07_metricas_prueba.csv` (Control, todas) |
| Tabla 13 (FAR 0,052 % / 0,041 %; FRR 0,00 % / 1,00 %; EER 0,00 % / 0,67 %; 0,607 / 0,402; 0,583 / 0,628) | `07_validacion_vs_prueba.csv`; `03_comparacion_validacion.csv`; `07_metricas_prueba.csv` |
| Rechazos: 2 de 15 (Billie Eilish), 1 de 14 (Zac Efron); 22 registradas sin rechazos | `07_por_identidad_prueba.csv`; `06_evaluacion_prueba.md` (Errores por identidad) |
| Control con rechazos en 22 de las 24 registradas | `07_por_identidad_prueba.csv`; `06_evaluacion_prueba.md` |
| Tabla 14 (fotos, identidades y puntuaciones de los 9 errores; secundario: Charlize 0,584, Anushka 0,593) | `07_casos_extremos_facenet_prueba.csv`; `06_evaluacion_prueba.md` (Casos extremos) |
| Tabla 15 y texto (0/5; 3/294; 2/720 = 0,278 %; 1/7 128 = 0,014 %; 0/115; control 2/5, 78/294, 0/720, 12/7 128; IC); "unas 20 veces"; 30 fotos de Kashyap | `07_desglose_marmik_kashyap.csv`; `06_evaluacion_prueba.md` (Desglose); `01_02_preparacion_datos.md` |
| Tarea 2.6: 1 de cada 3 fotogramas; ventana de 5, ≥ 3 votos; margen MTCNN 0; coseno mediano 0,989 en 150 imágenes de validación | `08_video_voluntarios.md`; `08_margen_mtcnn_validacion.csv`; `plan_evaluacion.md` (Prueba con video) |

## Limitaciones y conclusiones

| Cifra | Fuente |
|---|---|
| 4 identidades impostoras en prueba (3 en validación) | `01_02_preparacion_datos.md` |
| 178 pares residuales | `01_02_preparacion_datos.md` |
| FRR 28,52 % (ojos), 23,28 % (media cara), 9,51 % (desenfoque σ = 3) | `05_robustez.csv` |
| Conclusiones: 0,041 %, 1,00 %, 99,48 %, 0,073 s | `07_objetivos_prueba.csv` |

## Datos que NO salen de los archivos de `docs/sprint2/`

Ninguno de estos datos es una métrica del sistema.

| Dato | De dónde sale |
|---|---|
| Autor del dataset (Vasuki Patel), año 2020 y licencia "CC0: Public Domain" | API pública de Kaggle (`/api/v1/datasets/view/vasukipatel/face-recognition-dataset`), consultada el 2026-10-23. Queda como [PENDIENTE] confirmarlo en la página y anotar la fecha de consulta/descarga. |
| Autor y año de facenet-pytorch (Tim Esler, versión 2.6.0, 2024) | PyPI (`pypi.org/pypi/facenet-pytorch/2.6.0/json`, subida 2024-04-29) |
| Datos bibliográficos de las referencias (páginas, volúmenes, DOI) | Verificados por búsqueda web (CVF Open Access, arXiv, ORA Oxford, catálogos); ver la lista en el mensaje de entrega |
| Integrantes, docente, asignatura, equipo | Portada de la plantilla `Informe_Sprint1_APA7_CRISP-DM.docx` |

## Cifras no trazables

No se identificó ninguna cifra del informe sin fuente. Las fechas del Gantt vienen del enunciado del usuario (fechas planificadas), no de un archivo de resultados.
