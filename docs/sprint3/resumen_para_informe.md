# Resumen para el informe: Sprint 3 (fase 6 de CRISP-DM, despliegue)

**Fecha:** 2026-10-29.

**Estado:**
- La aplicación está construida y probada con pruebas automáticas y ensayos con fotos del dataset.
- **Faltan las pruebas funcionales con la cámara real y los voluntarios** y la prueba con su video (tarea 2.6).
- Lo pendiente va marcado como **[PENDIENTE]**. Las cifras marcadas como **ENSAYO** no son resultados con usuarios reales.

**Commits del sprint (repositorio local, sin push):**
- `64c07ab`: tareas 3.1 y 3.2;
- `650f7c8`: tarea 3.3;
- `28672b7`: tarea 3.4;
- el de este bloque: tareas 3.5 y 3.6.

## 1. Versiones y entorno

| Elemento | Versión |
|---|---|
| Sistema operativo | Windows 10 Pro 19045 |
| Python | 3.10.4 (`.venv`) |
| Flask / Werkzeug / Jinja2 | 3.1.3 / 3.1.9 / 3.1.6 |
| PyTorch | 2.11.0+cu128 |
| facenet-pytorch (MTCNN) | 2.6.0, instalado con `--no-deps` |
| OpenCV | 5.0.0 |
| NumPy / pandas | 2.2.6 / 2.3.3 |
| pytest | 9.2.0 |
| Hardware | Intel Core i5-10400, 16 GB RAM, NVIDIA RTX 5060 8 GB |
| Navegador de la demostración | **[PENDIENTE: navegador y versión usados con la cámara real]** |

**Backend: Flask.** Es la opción más sencilla para unas pocas rutas y plantillas HTML, sin servidor asíncrono. El frontend es HTML, CSS y
JavaScript simples, sin frameworks.

## 2. Estructura de `app/`

```
app/
  __main__.py        arranque: python -m app  (solo 127.0.0.1)
  config.py          parámetros y variables de entorno (umbral oficial, votación, criterios, bloqueo, tope, carpeta privada)
  main.py            rutas: /, /acerca, /api/verificar, /api/usuarios, /api/prueba/tiempo (modo pruebas)
  servicio.py        verificación: MTCNN + FaceNet (src.pipeline.Verifier) + coseno + decisión
  decision.py        reglas puras: calidad por fotograma, varios rostros, votación y mensajes
  almacen.py         usuarios de la demo en la carpeta privada (plantilla + metadatos; permisos restringidos)
  intentos.py        bloqueo, tope general, registro de intentos y modo pruebas
  admin.py           administración: entrar, registrar, eliminar, desbloquear
  publico.py         modo público para el túnel: autenticación básica, límites por IP real (sin rutas de administración)
  claves.py          palabra clave opcional: hash scrypt con sal y comparación con hmac.compare_digest
  pendientes.py      paso 2 (palabra clave): token de un solo uso, ligado a la IP, 120 s
  resumen_pruebas.py resumen por caso del registro del modo pruebas (sin imágenes ni seudónimos)
  medir_tiempos_ensayo.py  ENSAYO de tiempos del servidor con fotos del dataset
  modelo_esperado.json     huella del modelo evaluado (hashes y umbral)
  templates/         base, index (inicio de sesión), acerca, admin_login, admin_panel, admin_registrar
  static/            app.js (cámara y ráfaga), estilo.css
  tests/             125 pruebas automáticas (pytest)
```

Además, `scripts/iniciar_demo_tunel.ps1` arranca la instancia de administración (127.0.0.1:5001), la pública (127.0.0.1:5000) y
Cloudflare Tunnel hacia el puerto 5000; `scripts/borrar_datos_app.ps1` borra los datos de la app y verifica el borrado.

El modelo, las 24 plantillas y el umbral se usan **solo como biblioteca**, desde `models/verificador_facenet_vggface2/`, y no se modifican.

## 3. Flujo de verificación implementado

1. El usuario elige quién dice ser: un seudónimo registrado o, para pruebas, una de las 24 identidades del dataset.
2. El navegador captura una ráfaga de **5 fotogramas cada 400 ms** (unos 1,6 s) a 640×480 con `getUserMedia` y los envía como JPEG
   a `127.0.0.1`. El servidor los decodifica en memoria y **no los guarda**.
3. Si el usuario está bloqueado o en pausa por el tope, se responde sin procesar las imágenes.
4. En cada fotograma, **MTCNN** (facenet-pytorch) detecta los rostros. Se recorta el más grande a **160×160 con margen 0**, el mismo
   recorte que la tarea 2.6. Se comprobó una diferencia de 0 frente a `src.video.FaceCropper` en 10 imágenes.
5. Se comprueba la calidad del fotograma (sección 4).
6. Los fotogramas válidos pasan por **FaceNet InceptionResnetV1 (VGGFace2), congelada**, que produce un *embedding* de 512 valores.
   Se compara por **similitud coseno con la plantilla de ese usuario**.
7. Decisión por **votación**, igual que en la tarea 2.6:
   - **Acceso permitido** si al menos **3 de 5** fotogramas válidos tienen similitud ≥ **0,5514**, el umbral oficial del Sprint 2,
     que la app lee del `config.json` y comprueba;
   - **No se pudo verificar de forma confiable** si hay menos de 3 fotogramas válidos;
   - **Acceso denegado** en otro caso.
8. Se muestra el título, el motivo y el estado de cada fotograma, **sin la puntuación** ni la plantilla. Luego se actualiza el control de intentos.

**Registro de usuarios** (administrador):
- Requiere seudónimo, la casilla obligatoria de **autorización escrita firmada** y su fecha.
- Se capturan de 10 a 20 fotos, de las que al menos 8 deben tener un rostro válido.
- La plantilla es la **media renormalizada de los *embeddings***, como en la tarea 2.2.
- Se guardan solo `plantilla.npy` y `meta.json`. Las fotos se descartan, salvo que el administrador marque "conservar".
- Los usuarios de la demo se **añaden** a las 24 del dataset sin modificarlas.

**Control de intentos:**
- **Bloqueo:** 3 intentos **denegados** seguidos bloquean 60 s (configurable). Los no concluyentes se registran pero no cuentan, y
  solo un acceso permitido reinicia el contador. El estado persiste en disco y el administrador puede desbloquear.
- **Tope general:** 10 intentos de cualquier tipo en 5 minutos por usuario, con una pausa de 30 s (configurable).
- **Registro (CSV, sin imágenes):** fecha y hora, usuario solicitado, resultado y motivo, para los intentos denegados, no
  concluyentes, bloqueados y en pausa.

## 4. Criterios de "No se pudo verificar de forma confiable"

Un fotograma es **válido** solo si cumple todo lo siguiente. El intento es no concluyente con menos de 3 fotogramas válidos de 5, y se
muestra el motivo más frecuente.

| Estado | Criterio | Mensaje |
|---|---|---|
| `sin_rostro` | MTCNN no encuentra rostro con probabilidad ≥ 0,90 | No se detectó ningún rostro |
| `varios_rostros` | Otro rostro con probabilidad ≥ 0,95 y área ≥ 25 % del principal (las caras pequeñas del fondo se ignoran) | Hay más de un rostro |
| `lejos` | Lado menor de la caja < 60 px | El rostro está demasiado lejos |
| `oscuro` | Media de gris del recorte < 40 | La imagen está muy oscura |
| `sobreexpuesto` | Media de gris del recorte > 225 | Demasiada luz |
| `borroso` | Varianza del laplaciano del recorte < 10 | La imagen está muy borrosa |

**Calibración inicial con recortes de validación del dataset (no con la cámara):**
- **Varianza del laplaciano:**
  - imágenes limpias: p1 = 41,1 y mediana 519,2;
  - desenfoque σ1: mediana 36,6;
  - desenfoque σ2: mediana 7,9;
  - desenfoque σ3: mediana 3,9.
- **Media de gris:**
  - imágenes limpias: p1 = 80,5;
  - brillo ×0,6: mediana 80,5;
  - brillo ×0,4: mediana 53,5;
  - brillo ×0,25: mediana 33,3.

**[PENDIENTE: ajustar y documentar los valores finales de "borroso" y "oscuro" con las observaciones de la cámara real (casos CF03, CF05 y CF06)].**

## 5. Tiempos

| Medida | GPU | CPU | Fuente |
|---|---|---|---|
| Servidor por intento de 5 fotogramas (decodificación + MTCNN + FaceNet + decisión), mediana (p95) | 0,268 s (0,294) | 0,388 s (0,402) | **ENSAYO** con 5 fotos del dataset encuadradas en 640×480, 20 repeticiones (`ENSAYO_tiempos_servidor.csv`) |
| Petición completa en el servidor, mediana (p95) | 0,278 s (0,305) | 0,398 s (0,412) | ídem |
| Captura de la ráfaga en el navegador | ≈ 1,6 s por diseño (5 fotogramas cada 400 ms) | ídem | Configuración de `app.js` |
| De punta a punta en el navegador | 2,53 s (una medición, primer intento) | — | **ENSAYO** con cámara simulada (lienzo gris) en el navegador integrado, bloque A |
| De punta a punta con la cámara real, separando captura y procesamiento | **[PENDIENTE]** | **[PENDIENTE]** | Modo pruebas + `app.resumen_pruebas` |

**Objetivo RNF02 (≤ 3 s por verificación):**
- con los ensayos se espera unos 1,6 s de captura más unos 0,3–0,4 s de servidor;
- **[PENDIENTE: confirmar con la cámara real]**.

**Problema resuelto:** en GPU, TorchScript recompilaba la red cada vez que cambiaba el número de rostros válidos (3, 4 o 5), con 13–23 s
por recompilación. Se desactivó la optimización JIT solo dentro de la app; los *embeddings* son idénticos (diferencia 0).

## 6. Resultados de las pruebas

**Pruebas automáticas** (pytest, 2026-10-29): **125 de 125 pasan**.

| Archivo | Pruebas | Qué cubre |
|---|---|---|
| `test_decision.py` | 13 | Votación 3 de 5, umbral exacto, no concluyente, motivos, calidad, varios rostros, sin puntuaciones en la respuesta |
| `test_api.py` | 8 | Rutas, validación de entrada, bloqueo con 429, solo 127.0.0.1, página "Acerca de" |
| `test_intentos.py` | 10 | Bloqueo por 3 denegados; los no concluyentes no cuentan; el permitido reinicia; expiración; tope general y ventana; desbloqueo; registro sin imágenes; persistencia |
| `test_admin.py` | 14 | Contraseña, sesión, registro sin autorización o con fecha futura rechazado, número de fotos, seudónimo no válido, solo plantilla y metadatos por defecto, conservar fotos, borrado completo, desbloqueo, carpeta del repositorio rechazada |
| `test_modo_pruebas.py` | 6 | Registro por caso con tiempos, bloqueados registrados, resumen por caso sin seudónimos, modo desactivado |
| `test_privacidad.py` | 5 | No se guardan imágenes, carpeta por defecto fuera del repositorio, avisos de "Acerca de", lectura en solo lectura del almacén por el script de video, mismas reglas |
| `test_publico.py` | 21 | Modo público: las 7 rutas de administración dan 404 y no están registradas; no arranca sin contraseña; autenticación básica en todas las rutas; límite de contraseñas fallidas y de verificaciones por IP real del túnel; cabecera falsificada sin CF-Ray ignorada; dos instancias comparten usuarios nuevos, plantillas reemplazadas y desbloqueos sin reiniciar |
| `test_modelo_integridad.py` | 4 | SHA-256 de `red.ts`, de `plantillas.npz` y de los pesos originales; umbral 0,5514 |
| `test_modos_ingreso.py` | 31 | Decisión 1:N (usuario correcto, margen insuficiente, mejor candidato que cambia, bajo el umbral, 3 de 5, un solo usuario); clave con hash scrypt y nunca en registros; no se revela si falló el rostro o la clave; la clave incorrecta no reinicia el contador; 3 claves incorrectas bloquean; token de un solo uso ligado a la IP; modo B solo con usuarios de la app, deshabilitado sin usuarios y bloqueo por IP (hash, no en claro); cambiar y quitar la clave; modo público con los tres modos y sin administración; página «Acerca de» |
| `test_validar_video.py` | 6 | Validador del video y del CSV de anotaciones (sin modelo ni métricas) |
| `test_e2e_dataset.py` | 7 | **ENSAYO** con el modelo real y fotos del dataset (ver abajo) |

**ENSAYO de extremo a extremo con fotos del dataset** (no son voluntarios):

| Escenario | Resultado |
|---|---|
| Identidad registrada con 5 fotos suyas | Acceso permitido |
| La misma persona eligiendo otra identidad | Acceso denegado |
| Cámara tapada (fotogramas negros) | No concluyente (sin rostro) |
| Dos personas en el cuadro | No concluyente (varios rostros) |
| Imagen muy oscura | No concluyente (oscuro) |
| Registro de una identidad no registrada (`ENSAYO_V01`) | 11 de 12 fotos válidas; luego permitido con otras fotos suyas y denegado con otra persona; eliminado al terminar |
| Modo B (1:N) con 2 usuarios registrados (`ENSAYO_V01` = Hugh Jackman, `ENSAYO_V02` = Natalie Portman) | Otras fotos de Hugh Jackman: «Hola, ENSAYO_V01»; Brad Pitt (no registrado en la app): no identificado |

**Casos funcionales con cámara real** (`casos_de_prueba.csv`, 21 casos de CF01 a CF21; CF16 a CF21 cubren el modo B y la palabra clave):
- **[PENDIENTE: ninguno ejecutado todavía]**. Los ejecuta el equipo con los voluntarios. Los resultados se anotarán con fecha y con el
  resumen de `app.resumen_pruebas`.
- El caso **CF14 (suplantación con foto o video)** espera que **pueda ser aceptado**, porque no hay detección de vida, y se reportará lo que ocurra.

## 7. Cumplimiento de los requisitos

Texto de cada requisito tomado del Informe del Sprint 1.

| Requisito | Cómo se cumple | Evidencia | Estado |
|---|---|---|---|
| **RF01** El administrador registra usuarios de prueba y asocia su cuenta con sus datos faciales, previa autorización | Panel de administración con contraseña de entorno. Registro con seudónimo, autorización escrita firmada y fecha obligatorias; plantilla calculada con 10 a 20 fotos | `admin.py`; `test_admin.py`; ENSAYO de registro con el modelo real | Implementado. Con voluntario real: **[PENDIENTE: CF13, CF15]** |
| **RF02** Captura una imagen del rostro con la cámara durante el inicio de sesión | `getUserMedia` y ráfaga de 5 fotogramas | `app.js`; flujo probado con cámara simulada | Implementado. Cámara real: **[PENDIENTE: CF01]** |
| **RF03** Detecta el rostro, lo preprocesa y obtiene sus características | MTCNN, recorte 160×160 (igual que la tarea 2.6), FaceNet (512 valores) | `servicio.py`; diferencia 0 frente al recorte de 2.6; `test_e2e_dataset.py` | Implementado (ENSAYO) |
| **RF04** Compara con el usuario registrado mediante similitud o distancia | Coseno con la plantilla del usuario elegido (verificación 1 a 1) | `servicio.py`; ENSAYO permitido/denegado | Implementado (ENSAYO) |
| **RF05** Permite el acceso si cumple el umbral | Umbral oficial 0,5514 con votación de al menos 3 de 5 | `decision.py`; `test_decision.py`; `test_modelo_integridad.py` | Implementado |
| **RF06** Deniega el acceso si no cumple el umbral | ídem | ídem | Implementado |
| **RF07** Muestra un mensaje comprensible | "Acceso permitido", "Acceso denegado", "No se pudo verificar de forma confiable" y "Usuario bloqueado temporalmente", con motivo | `decision.py`; `index.html`; `test_api.py` | Implementado. Comprensión: **[PENDIENTE: opinión de los voluntarios]** |
| **RNF01** Interfaz sencilla y comprensible | Una pantalla, 3 pasos, HTML y JS sin frameworks, mensajes en lenguaje llano | `templates/`, `static/` | Implementado. **[PENDIENTE: valoración en las pruebas funcionales]** |
| **RNF02** Tiempo adecuado para una demostración | Servidor 0,27 s (GPU) y 0,39 s (CPU) de mediana más unos 1,6 s de captura | `ENSAYO_tiempos_servidor.csv` | ENSAYO bajo 3 s. Cámara real: **[PENDIENTE]** |
| **RNF03** Acceso a imágenes y datos biométricos restringido y autorizado | Imágenes solo en memoria; carpeta privada fuera del repositorio con permisos del usuario (`icacls`); solo plantillas; contraseña de administrador por entorno; seudónimos; solo 127.0.0.1; borrado completo | `almacen.py`; `test_privacidad.py`; `test_admin.py` | Implementado (sin cifrado: ver limitaciones) |
| **RNF04** El modelo se evalúa con métricas sobre un conjunto de prueba independiente | Evaluado en el Sprint 2 (prueba única): FAR 0,041 %, FRR 1,00 %, con fotos de Kaggle. La app usa ese mismo modelo y umbral, y lo comprueba por hash | `docs/sprint2/06_evaluacion_prueba.md`; `test_modelo_integridad.py` | Cumplido en el Sprint 2. Con video de voluntarios: **[PENDIENTE: tarea 2.6]** |
| **RNF05** Se controlan los intentos de acceso no autorizado | Bloqueo tras 3 denegados, tope general, registro de intentos, desbloqueo por el administrador | `intentos.py`; `test_intentos.py`; `test_api.py` | Implementado. Con cámara real: **[PENDIENTE: CF11, CF12]** |
| **RNF06** Informa cuando no es posible una verificación confiable | Criterios de la sección 4 con su motivo | `decision.py`; `test_decision.py`; ENSAYO (cámara tapada, dos personas, oscuro) | Implementado. Umbrales de calidad finales: **[PENDIENTE]** |

## 7 bis. Formas de ingresar (modos A, B y palabra clave)

| Modo | Implementación | Parámetros |
|---|---|---|
| **A. Nombre + rostro** (1 a 1, evaluado en el Sprint 2) | Sin cambios: coseno con la plantilla del usuario elegido y votación | Umbral 0,5514; al menos 3 de 5 |
| **B. Solo cámara** (1:N, **no evaluado en el Sprint 2**) | Solo contra los usuarios registrados en la app (nunca las 24 del dataset). Un fotograma vota por su mejor candidato si llega al umbral y supera al segundo por el margen. Si gana un único usuario, «Hola, <seudónimo>»; si no, «No se pudo identificar de forma confiable». Deshabilitado con 0 usuarios | Umbral 0,5514; **`MARGEN_1N` = 0,05 (no calibrado)**; al menos 3 de 5 |
| **Palabra clave** (opcional, elegida al registrar) | Se pide después del rostro, en A y en B; también si el rostro no coincide, para no revelar cuál falló. Solo se guarda un hash scrypt con sal (n = 2¹⁴, r = 8, p = 1); se compara con `hmac.compare_digest`. El administrador puede cambiarla o quitarla. Sin correo electrónico | Mínimo 6 caracteres; el paso 2 caduca a los 120 s |

**Bloqueos:**
- **A:** 3 denegados seguidos por usuario bloquean 60 s. La clave incorrecta cuenta como denegado, y el rostro aceptado con clave incorrecta no reinicia el contador; solo lo reinicia un acceso completo.
- **B:** 3 intentos sin identificar seguidos bloquean esa IP 60 s. La IP real se toma de `CF-Connecting-IP` solo si viene del túnel, y se guarda como hash con sal. Si el usuario identificado falla la clave 3 veces, se bloquea a ese usuario.
- **Todos:** los no concluyentes no cuentan; se mantienen el tope global y la persistencia en disco.
- La instancia pública ofrece los tres modos; el registro, el cambio de clave y la eliminación siguen solo en la de administración.

## 7 ter. Exposición por túnel (demostración con teléfonos)

- **Instancia pública (5000):** solo verifica; las rutas de administración responden 404; autenticación básica (`FACEID_ACCESO_PUBLICO`);
  20 verificaciones por minuto por IP real (`CF-Connecting-IP`, solo si la petición viene del túnel); aviso visible.
- **Instancia de administración (5001):** solo en 127.0.0.1; el túnel nunca apunta a ella.
- **Comprobado en esta laptop sin el túnel** (2026-10-29), con las dos instancias arrancadas por el script y peticiones HTTP que imitan
  las cabeceras de Cloudflare:
  - la pública responde 401 sin contraseña y 404 en `/admin` y en registrar o desbloquear;
  - a partir de la verificación 21 desde la misma IP responde "Demasiadas peticiones", y otra IP sigue pudiendo;
  - el panel de la 5001 muestra el estado que escribe la 5000.
- **[PENDIENTE: prueba real con `cloudflared`]**, que no estaba instalado en el equipo de desarrollo, y tiempo de punta a punta desde un
  teléfono (ver `medir_tiempo_telefono.md`).

## 8. Limitaciones conocidas

Detalle en `limitaciones.md`.

- **Sin detección de vida:** no protege contra fotos, pantallas ni videos del usuario. Se avisa en la app.
- **Cualquiera puede bloquear temporalmente a un usuario** eligiendo su nombre y fallando 3 veces. El administrador puede desbloquear.
- Las cifras del modelo son del Sprint 2, con fotos de Kaggle de personas famosas, no con cámara web. La prueba con el video de los voluntarios está pendiente.
- **El modo «Solo cámara» (1:N) no se evaluó en el Sprint 2**: el riesgo de aceptar a otra persona crece con el número de usuarios y el margen de 0,05 no está calibrado.
  **[PENDIENTE: casos CF16, CF17, CF20 y CF21 con voluntarios]**.
- La palabra clave solo protege si es difícil de adivinar; en local, el bloqueo por IP del modo B afecta a todo el equipo.
- Los criterios de calidad están calibrados con el dataset, no con la cámara real.
- Los datos privados no están cifrados; hay una sola contraseña de administrador; se usa el servidor de desarrollo de Flask.
- Con el túnel, las imágenes pasan por la infraestructura de Cloudflare (cifradas hasta allí; la app no las guarda). La dirección
  `trycloudflare.com` cambia en cada reinicio.

## 9. Problemas encontrados

| Problema | Solución |
|---|---|
| Recompilación JIT de TorchScript en GPU (13–23 s en el segundo intento) | Optimización JIT desactivada en la app; *embeddings* idénticos |
| El navegador integrado del entorno de desarrollo bloquea la cámara | Flujo probado con una cámara simulada (lienzo); la cámara real queda para las pruebas del equipo |
| Fotos con caras pequeñas al fondo marcaban "varios rostros" | Solo cuenta otro rostro con probabilidad ≥ 0,95 y área ≥ 25 % del principal |
| Los ensayos dejaban registros de intentos en las carpetas temporales de pytest, una carpeta vacía en `data/app_privado` y las plantillas `ENSAYO_V01/V02` de la tarea 2.6 en el paquete del modelo | Todo eliminado antes de las pruebas reales; el ensayo de extremo a extremo usa una carpeta temporal propia; la carpeta por defecto se movió fuera del repositorio |
