# Autenticación biométrica por reconocimiento facial — línea de ciencia de datos

Proyecto académico (Universidad Andina del Cusco, Inteligencia Artificial), metodología CRISP-DM.
Este repositorio contiene **solo** cuadernos y scripts de Python (fases 2–5). La aplicación web y la
cámara en vivo pertenecen al Sprint 3 (fase 6) y **no** están aquí.

Tarea: **verificación 1 a 1**. Se compara el embedding de una imagen con la plantilla del usuario que
dice ser, mediante una medida de similitud y un umbral.

## Estructura

```
data/            (ignorada por git)
  raw/Dataset/   dataset de Kaggle: Faces/Faces, Original Images/..., Dataset.csv
  raw/archive.zip
  processed/     splits.csv, faces160.npz (generados por el cuaderno 02)
models/          pesos entrenados (ignorados por git)
notebooks/       01_comprension_datos, 02_preparacion_datos, ...
src/             config.py (rutas, semilla, protocolo), data.py (carga, duplicados, división, preprocesado),
                 models.py (FaceNet, CNN propia, ResNet-18, LBPH), verification.py (plantillas, protocolo), metrics.py (EER, ROC, FAR/FRR),
                 pipeline.py (paquete TorchScript + plantillas + config, clase Verifier),
                 robustness.py (perturbaciones para pruebas de robustez), evaluation.py (FAR/FRR, IC, exactitud balanceada, objetivos),
                 video.py + video_verificacion.py (video con MTCNN y votación), registro_voluntario.py, ensayo_video.py
docs/sprint2/    resultados de cada tarea y figuras/
app/             aplicación web local del Sprint 3 (Flask): main.py (rutas), servicio.py (verificación), decision.py,
                 almacen.py (usuarios), intentos.py (bloqueo y registro), admin.py, templates/, static/, tests/
docs/sprint3/    casos de prueba, guion de la demostración, limitaciones y resumen para el informe
```

## Instalación (Windows, local)

```bash
python -m venv .venv
.venv/Scripts/python -m pip install --upgrade pip
.venv/Scripts/python -m pip install torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cu128
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pip install facenet-pytorch==2.6.0 --no-deps
```

Ver las notas de `requirements.txt` (GPU RTX 5060 → CUDA 12.8; facenet-pytorch con `--no-deps`).
En Colab: subir el proyecto, `pip install -r requirements.txt` y `pip install facenet-pytorch --no-deps`
(Colab ya trae torch).

## Datos

1. Descargar *Face Recognition Dataset* (vasukipatel) de Kaggle.
2. Descomprimir para que quede `data/raw/Dataset/Faces/Faces/*.jpg` y `data/raw/Dataset/Dataset.csv`.

Solo se usa `Faces/Faces` (recortes de 160×160). `Original Images` contiene las mismas fotos sin recortar,
así que no se usa, para no filtrar datos entre conjuntos.

## Reproducir

Desde la raíz del proyecto, en orden:

```bash
.venv/Scripts/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/01_comprension_datos.ipynb
.venv/Scripts/python -m jupyter nbconvert --to notebook --execute --inplace notebooks/02_preparacion_datos.ipynb
.venv/Scripts/python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks/03_seleccion_tecnica.ipynb
.venv/Scripts/python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks/04_entrenamiento.ipynb
.venv/Scripts/python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks/05_validacion_ajuste.ipynb
```

O bien abrirlos con `jupyter notebook` y ejecutar todas las celdas. La semilla es 42 (`src/config.py`).
El cuaderno 02 genera `data/processed/splits.csv`, que es la división que usan los cuadernos siguientes.

## Estado

Resumen de todo el Sprint 2 para el informe: `docs/sprint2/resumen_para_informe.md`.

| Tarea | Estado | Resultados |
|---|---|---|
| 0 · Revisión previa + preparación (fases 2–3) | hecha, pendiente de revisión | `docs/sprint2/00_revision_previa.md`, `docs/sprint2/01_02_preparacion_datos.md` |
| 2.1 · Selección de técnica | hecha, pendiente de revisión: FaceNet VGGFace2 | `docs/sprint2/03_seleccion_tecnica.md`, `notebooks/03_seleccion_tecnica.ipynb` |
| 2.2 · Entrenamiento (registro + control) | hecha, pendiente de revisión | `docs/sprint2/04_entrenamiento.md`, `notebooks/04_entrenamiento.ipynb` |
| 2.3 · Validación y ajuste (umbral 0,5514 propuesto) | hecha, pendiente de revisión | `docs/sprint2/05_validacion_ajuste.md`, `docs/sprint2/plan_evaluacion.md`, `notebooks/05_validacion_ajuste.ipynb` |
| 2.4 · Métricas y objetivos (pendientes de confirmar con el docente) | hecha, pendiente de revisión | `docs/sprint2/06_metricas.md`, `src/evaluation.py` |
| 2.5 · Evaluación en prueba | ejecutada una vez (commit 0a27e3d), pendiente de revisión | `docs/sprint2/06_evaluacion_prueba.md`, `notebooks/06_evaluacion_prueba.ipynb`, `docs/sprint2/07_*` |
| 2.6 · Video de voluntarios | preparado y ENSAYADO con datos simulados; cuaderno real bloqueado (sin datos) | `docs/sprint2/08_video_voluntarios.md`, `notebooks/07_ensayo_video.ipynb`, `notebooks/08_video_voluntarios.ipynb` |

El cuaderno 03 descarga automáticamente los pesos preentrenados (FaceNet VGGFace2 y CASIA-WebFace desde
https://github.com/timesler/facenet-pytorch/releases, y ResNet-18 de torchvision) en `models/torch_hub/` (≈ 270 MB, ignorado por git).
Tarda varios minutos en la RTX 5060 (LBPH ≈ 5 min, entrenamiento de (a1)+(a2) ≈ 3 min); los resultados de (a1)/(a2) pueden variar ligeramente entre ejecuciones por el no determinismo de la GPU.
El cuaderno 04 genera los paquetes `models/verificador_facenet_vggface2/` y `models/control_resnet18_imagenet/`
(red TorchScript + plantillas + config.json), que se cargan con `src.pipeline.Verifier(carpeta)`.
El cuaderno 05 escribe el umbral propuesto en el `config.json` de cada paquete (requiere haber ejecutado el 04).

**Evaluación en prueba (cuaderno 06): ejecución única.** El cuaderno se niega a ejecutarse si no se define
`FACEID_EJECUTAR_PRUEBA=SI`, exige que el árbol de git esté limpio y registra el commit. Si ya existen resultados, pide
`FACEID_MOTIVO_REEJECUCION`. En PowerShell:

```
$env:FACEID_EJECUTAR_PRUEBA = "SI"; .venv/Scripts/python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks/06_evaluacion_prueba.ipynb
```

**Video de voluntarios (tarea 2.6).** Registro: `.venv/Scripts/python -m src.registro_voluntario --fotos <carpeta privada> --id V01`.
Video: `.venv/Scripts/python -m src.video_verificacion --video <video> --anotaciones <csv> --salida <carpeta privada>`.
Las fotos, los videos y las salidas deben estar fuera del repositorio o en `data/`. El cuaderno 07 es un ENSAYO con datos simulados
del dataset; el 08 (datos reales, ejecución única) se desbloquea con `FACEID_EJECUTAR_VIDEO=SI` (ver `docs/sprint2/08_video_voluntarios.md`).

## Sprint 3: aplicación web local (fase 6, despliegue)

Aplicación sencilla de inicio de sesión por verificación facial 1 a 1, para **una sola máquina** (escucha solo en
`127.0.0.1`). Usa el paquete del modelo del Sprint 2 como biblioteca, sin modificarlo: FaceNet VGGFace2 congelado,
las 24 plantillas del dataset y el umbral oficial 0,5514. Detalle en `docs/sprint3/resumen_para_informe.md`.

### Requisitos

1. La instalación de arriba (`.venv`, `requirements.txt` con Flask y pytest, `facenet-pytorch --no-deps`).
2. El paquete del modelo en `models/verificador_facenet_vggface2/` (`red.ts`, `plantillas.npz`, `config.json`). No está en
   git: se genera con el cuaderno 04 y el 05, o se copia de un compañero.
3. Un navegador con cámara (Chrome o Edge). `getUserMedia` funciona en `http://127.0.0.1` sin HTTPS.

### Configuración (variables de entorno)

| Variable | Para qué | Por defecto |
|---|---|---|
| `FACEID_APP_DATA` | Carpeta **privada** de datos: plantillas de usuarios, registros de intentos. Debe estar fuera del repositorio (o en `data/`, ignorada por git). | `%USERPROFILE%\FaceID_privado` |
| `FACEID_ADMIN_PASSWORD` | Contraseña del administrador. Sin ella, la administración queda deshabilitada. Nunca la escriba en el código ni en git. | (ninguna) |
| `FACEID_DEVICE` | `cuda` o `cpu` | `cuda` si hay GPU |
| `FACEID_BLOQUEO_FALLOS`, `FACEID_BLOQUEO_SEG` | Denegados seguidos para bloquear y duración del bloqueo | 3 y 60 s |
| `FACEID_TOPE_INTENTOS`, `FACEID_TOPE_VENTANA_SEG`, `FACEID_TOPE_PAUSA_SEG` | Tope general por usuario | 10 en 300 s, pausa de 30 s |
| `FACEID_MODO_PRUEBAS` | `1` registra todos los intentos con su caso de prueba y sus tiempos, sin imágenes | desactivado |
| `FACEID_MARGEN_1N` | Margen mínimo del mejor candidato sobre el segundo en el modo «Solo cámara» (1:N) | 0,05 |
| `FACEID_BLOQUEO_IP_FALLOS`, `FACEID_BLOQUEO_IP_SEG` | Bloqueo por IP del modo «Solo cámara» | 3 y 60 s |
| `FACEID_PUERTO` | Puerto local. La instancia de administración **nunca** arranca en 5000 (el puerto del túnel). | 5001 (administración) / 5000 (pública) |
| `FACEID_ADMIN_HOSTS` | Nombres extra que acepta la administración, separados por comas (p. ej. `pc-casa.tail1234.ts.net` para Tailscale). Siempre acepta `127.0.0.1` y `localhost`; otro nombre recibe 400. | (ninguno) |
| `FACEID_ADMIN_FALLOS_MAX`, `FACEID_ADMIN_FALLOS_VENTANA_SEG` | Contraseñas de administrador fallidas antes de una pausa (global) | 5 en 600 s |
| `FACEID_EXPLICACION` | `0` desactiva el modo explicación («¿Cómo decidió la máquina?»). Nunca está disponible en la instancia pública. | activado en local |

### Ejecutar (PowerShell, desde la raíz del proyecto)

```
$env:FACEID_ADMIN_PASSWORD = "<elija una contraseña>"
.venv/Scripts/python -m app
```

Abra `http://127.0.0.1:5001`. Para registrar usuarios entre en **Administración**. Tras arrancar, compruebe con
`git status` que no aparece ningún archivo de datos.

### Formas de ingresar

| Modo | Cómo funciona | Evaluado en el Sprint 2 |
|---|---|---|
| **A. Nombre + rostro** (1 a 1) | El usuario elige quién es; 5 fotogramas; acepta si al menos 3 llegan al umbral 0,5514 contra la plantilla de ese usuario. | Sí |
| **B. Solo cámara** (1:N) | Sin elegir nombre. Cada fotograma vota por su mejor candidato entre los usuarios **registrados en la app** (no las 24 del dataset) si llega a 0,5514 y supera al segundo por `MARGEN_1N` (0,05). Acepta si el mismo usuario gana en al menos 3 de 5 fotogramas y muestra «Hola, <seudónimo>»; si no, «No se pudo identificar de forma confiable». Se deshabilita si no hay usuarios registrados. | **No**: el riesgo crece con el número de usuarios |
| **Palabra clave** (opcional por usuario) | Al registrar se elige «Solo rostro» o «Rostro + palabra clave» (mínimo 6 caracteres; solo se guarda un hash scrypt con sal). Si la cuenta la tiene, se pide después del rostro (en A y en B). Al denegar no se dice si falló el rostro o la clave. | No aplica |

**Bloqueos:**
- **A:** 3 denegados seguidos por usuario bloquean 60 s. Una clave incorrecta cuenta como denegado, y solo un acceso completo reinicia el contador.
- **B:** 3 intentos sin identificar seguidos bloquean esa IP 60 s; en local, todo el equipo. Si falla la clave del usuario identificado, cuenta para el bloqueo de ese usuario.
- **Todos:** los no concluyentes no cuentan. El cambio o la eliminación de la clave se hace en el panel de administración.

### Interfaz y modo explicación

La interfaz tiene tema **claro y oscuro** (sigue al sistema; el botón de la barra superior lo cambia y el navegador lo recuerda).
En la instancia local, el interruptor **«Mostrar cómo decide la máquina»** añade debajo del resultado el camino completo del intento,
pensado para la exposición:

1. los 5 fotogramas con las cajas de MTCNN y su estado de calidad;
2. el recorte 160 × 160 que entra a la red y un mapa aproximado de dónde se activa;
3. las capas de FaceNet (Inception-ResNet v1): mosaicos de mapas de activación, de bordes a rasgos abstractos;
4. el vector de 512 números;
5. la comparación: en «Nombre + rostro», la similitud de cada fotograma contra el umbral 0,5514; en «Solo cámara», los 3 candidatos más
   parecidos de cada fotograma y el margen;
6. la votación (3 de 5) y la decisión.

Muestra puntuaciones, así que es solo para la demostración local (ver `docs/sprint3/limitaciones.md`, puntos 20 a 23).

### Pruebas

```
.venv/Scripts/python -m pytest app/tests -q                 # todas (incluye el ensayo con el modelo real)
.venv/Scripts/python -m pytest app/tests -q -m "not lento"  # sin el modelo, en segundos
```

Pruebas funcionales con la cámara real: arranque con `$env:FACEID_MODO_PRUEBAS = "1"`, escriba el ID del caso
(`docs/sprint3/casos_de_prueba.csv`) antes de cada intento y luego resuma:

```
.venv/Scripts/python -m app.resumen_pruebas --csv docs/sprint3/resumen_casos.csv
```

Tiempos del servidor (ENSAYO con fotos del dataset): `.venv/Scripts/python -m app.medir_tiempos_ensayo`.

### Video de los voluntarios con el mismo registro de la app

```
.venv/Scripts/python -m src.video_verificacion --video <video> --anotaciones <csv> --salida <carpeta privada> --almacen-app $env:USERPROFILE\FaceID_privado
```

Para el cuaderno 08 (ejecución única), defina además `$env:FACEID_ALMACEN_APP` con esa carpeta. Lee las plantillas en
solo lectura y mantiene las reglas de la tarea 2.6.

### Demostración desde teléfonos por túnel (Cloudflare Tunnel)

Dos instancias en la misma laptop, con la misma carpeta de datos:

| Instancia | Puerto | Qué hace | ¿Por el túnel? |
|---|---|---|---|
| Pública (`FACEID_MODO_PUBLICO=1`) | 5000 | Solo verificación. `/admin` y las rutas de registro, eliminación y desbloqueo dan 404. Autenticación básica con `FACEID_ACCESO_PUBLICO`. Límite de verificaciones por IP real (`CF-Connecting-IP`, solo si la petición viene del túnel). Aviso visible. | **Sí**: el túnel apunta solo aquí |
| Administración | 5001 | Registrar, eliminar y desbloquear (contraseña `FACEID_ADMIN_PASSWORD`) | **Nunca** (solo `http://127.0.0.1:5001`) |

Ambas escuchan solo en `127.0.0.1`. Por el túnel todas las peticiones llegan desde `127.0.0.1`, así que **no** sirve filtrar por IP local:
la protección es que el túnel nunca apunta al puerto 5001. Los usuarios registrados o eliminados en la administración aparecen y desaparecen
en la pública sin reiniciar. Los bloqueos y desbloqueos también se comparten: el estado se guarda en la carpeta de datos y se vuelve a leer en cada intento.

Pasos:
1. Instalar `cloudflared` una vez: `winget install --id Cloudflare.cloudflared`.
2. **Desactivar la suspensión del equipo y usar el cargador.** El script mantiene el equipo despierto mientras está abierto; la configuración
   de energía no cambia.
3. Arrancar todo (pide las dos contraseñas, que deben ser distintas, y muestra la dirección pública):
   ```
   powershell -ExecutionPolicy Bypass -File scripts\iniciar_demo_tunel.ps1
   ```
   Opciones: `-SinTunel` (solo las dos instancias, para probar en local), `-ModoPruebas` (registra los tiempos por caso) y `-Dispositivo cpu`.
4. Compartir la dirección `https://….trycloudflare.com` y la contraseña de acceso público. **La dirección cambia cada vez que se reinicia
   el túnel.**
5. Pulsar Enter en la ventana del script para cerrar el túnel y las dos instancias.

### Administración desde otro dispositivo propio (Tailscale, sin internet)

Para usar el panel (`:5001`) desde la laptop o el teléfono sin exponerlo a internet: **Tailscale** une la PC de casa, la laptop
y el teléfono en una red privada cifrada (*tailnet*), y **`tailscale serve`** publica el puerto 5001 **solo dentro de esa red** con
HTTPS (la cámara del navegador exige HTTPS para registrar usuarios desde otro equipo).

```
teléfono / laptop ──(WireGuard, solo tu tailnet)──> PC de casa: tailscale serve (HTTPS :443) ──> http://127.0.0.1:5001
```

- La app sigue escuchando **solo en 127.0.0.1**; `tailscale serve` es un proxy local que corre en la propia PC. Nadie de la red local
  (wifi de casa) puede conectarse al puerto 5001.
- La contraseña de administrador (`FACEID_ADMIN_PASSWORD`) sigue siendo obligatoria. Tras 5 contraseñas fallidas en 10 minutos el
  inicio de sesión del administrador se pausa (para todos, porque por el proxy todas las peticiones llegan desde 127.0.0.1).
- La instancia de administración responde 404 a todo lo que entra por internet (cabeceras `CF-Ray`/`CF-Connecting-IP` de Cloudflare o
  `Tailscale-Funnel-Request` de Funnel), solo responde a los nombres de `FACEID_ADMIN_HOSTS` + `127.0.0.1`/`localhost`, y nunca arranca
  en el puerto 5000. Las cabeceras `X-Forwarded-*` y `Tailscale-User-*` del proxy se aceptan pero **no** se usan para nada.
- **Nunca use `tailscale funnel`**: Funnel publica el servicio en internet. Solo `tailscale serve`.

**1. Instalar Tailscale (una vez por dispositivo)**
- PC de casa y laptop (Windows): `winget install --id Tailscale.Tailscale`, abrir Tailscale e iniciar sesión **con la misma cuenta**.
  Active la verificación en dos pasos de esa cuenta: quien entra en ella puede añadir dispositivos a su tailnet.
- Teléfono: instalar la app Tailscale (Play Store / App Store) e iniciar sesión con la misma cuenta.
- En la consola de Tailscale (<https://login.tailscale.com/admin/dns>): dejar **MagicDNS** activado y pulsar **Enable HTTPS**
  (certificados `*.ts.net`). Es una sola vez por tailnet.

**2. En la PC de casa: arrancar la administración y el proxy**

```
tailscale status                                    # la PC, la laptop y el teléfono deben aparecer
$env:FACEID_ADMIN_PASSWORD = "<contraseña larga>"
$env:FACEID_ADMIN_HOSTS = "<nombre-de-la-pc>.<su-tailnet>.ts.net"
.venv/Scripts/python -m app                         # administración en http://127.0.0.1:5001
```

En otra ventana de PowerShell (en la misma PC):

```
tailscale serve --bg http://127.0.0.1:5001
tailscale serve status                              # debe decir "(tailnet only)", nunca "Funnel on"
```

`tailscale serve status` muestra la dirección exacta, `https://<nombre-de-la-pc>.<su-tailnet>.ts.net`. Ese nombre es el que va en
`FACEID_ADMIN_HOSTS` (si el panel responde «400 Bad Request», el nombre no coincide: corríjalo y reinicie la app).

**3. Desde la laptop o el teléfono** (con Tailscale conectado): abrir `https://<nombre-de-la-pc>.<su-tailnet>.ts.net/admin/`.

**4. Al terminar** (en la PC):

```
tailscale serve reset                               # quita el proxy; el 5001 vuelve a ser solo local
```

y cierre la app con Ctrl+C. Si se pierde el teléfono, elimínelo en <https://login.tailscale.com/admin/machines>.

**Todo de una vez (túnel de Cloudflare + administración por Tailscale):** doble clic en `scripts\iniciar_demo_completa.cmd`, o

```
powershell -ExecutionPolicy Bypass -File scripts\iniciar_demo_completa.ps1
```

Comprueba que los puertos 5000 y 5001 están libres, detecta el nombre `*.ts.net` del equipo (lo pone en `FACEID_ADMIN_HOSTS`),
activa `tailscale serve` solo hacia el 5001 (se detiene si detecta Funnel) y lanza `iniciar_demo_tunel.ps1` (pública 5000 + Cloudflare,
administración 5001). Muestra las dos direcciones. Al pulsar Enter cierra todo y ejecuta `tailscale serve reset`. **No cierre la ventana
con la X**: así no se ejecuta la limpieza (si pasa, ejecute `tailscale serve reset` a mano). Acepta `-SinTunel`, `-ModoPruebas`,
`-Dispositivo cpu` y `-SinTailscale`.

Borrar todos los datos de la app (plantillas, metadatos y registros) y verificar el borrado. No toca `models/`:
```
powershell -ExecutionPolicy Bypass -File scripts\borrar_datos_app.ps1
```

Medir el tiempo de punta a punta desde un teléfono: `docs/sprint3/medir_tiempo_telefono.md`.
