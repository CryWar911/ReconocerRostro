"""Configuración de la aplicación web (Sprint 3). Todo lo sensible viene de variables de entorno.

Variables de entorno:
  FACEID_APP_DATA        carpeta de datos privados (plantillas de usuarios, registros). Debe estar FUERA del
                         repositorio o dentro de data/ (ignorada por git). Por defecto: %USERPROFILE%/FaceID_privado
                         (fuera del repositorio)
  FACEID_DEVICE          "cuda" o "cpu" (por defecto: cuda si hay GPU)
  FACEID_ADMIN_PASSWORD  contraseña del administrador (tarea 3.3); nunca en el código ni en git
  FACEID_BLOQUEO_FALLOS  intentos fallidos consecutivos antes del bloqueo (por defecto 3)
  FACEID_BLOQUEO_SEG     duración del bloqueo en segundos (por defecto 60)
  FACEID_PUERTO          puerto local; la app escucha SOLO en 127.0.0.1. Por defecto 5001 (administración) o
                         5000 (instancia pública). La administración nunca arranca en el puerto público (5000).
  FACEID_ADMIN_HOSTS     nombres extra que acepta la instancia de administración, separados por comas
                         (p. ej. el nombre *.ts.net de `tailscale serve`); siempre acepta 127.0.0.1 y localhost
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAQUETE_MODELO = ROOT / "models" / "verificador_facenet_vggface2"
DATA_DIR = Path(os.environ.get("FACEID_APP_DATA", Path.home() / "FaceID_privado"))
MODO_PRUEBAS = os.environ.get("FACEID_MODO_PRUEBAS") == "1"   # registra también los permitidos y los tiempos (tarea 3.4)

HOST = "127.0.0.1"
PUERTO_PUBLICO = 5000     # el túnel de Cloudflare apunta SOLO aquí; la administración nunca puede usarlo
PUERTO_ADMIN = 5001
PUERTO = int(os.environ.get("FACEID_PUERTO") or (PUERTO_PUBLICO if os.environ.get("FACEID_MODO_PUBLICO") == "1" else PUERTO_ADMIN))

# Umbral OFICIAL fijado en la tarea 2.3 (validación). La app lo lee del config.json del paquete
# y comprueba que coincide con este valor; nunca lo recalcula.
UMBRAL_OFICIAL = 0.551421

# Decisión por ráfaga (igual que la votación de la tarea 2.6)
N_FOTOGRAMAS = 5          # fotogramas por intento
MIN_VOTOS = 3             # mínimo de fotogramas con rostro válido y puntuación >= umbral para aceptar
MIN_VALIDOS = 3           # con menos fotogramas válidos el intento es "no concluyente"

# Criterios de calidad por fotograma ("no se pudo verificar de forma confiable")
PROB_ROSTRO_MIN = 0.90    # probabilidad mínima de MTCNN para considerar que hay un rostro
SEGUNDO_ROSTRO_PROB = 0.95  # otro rostro con esta probabilidad...
SEGUNDO_ROSTRO_AREA = 0.25  # ...y al menos este % del área del principal => "varios rostros"
LADO_ROSTRO_MIN = 60      # px del lado menor de la caja detectada; menor => "demasiado lejos"
LAPLACIANO_MIN = 10.0     # varianza del laplaciano del recorte 160x160; menor => "muy borroso"
BRILLO_MIN = 40.0         # media de gris del recorte; menor => "muy oscuro"
BRILLO_MAX = 225.0        # media de gris del recorte; mayor => "sobreexpuesto"

# Control de intentos (tarea 3.3)
# Bloqueo: solo los intentos DENEGADOS consecutivos cuentan; un acceso permitido reinicia el contador;
# los no concluyentes se registran pero no lo cambian.
BLOQUEO_FALLOS = int(os.environ.get("FACEID_BLOQUEO_FALLOS", "3"))
BLOQUEO_SEG = int(os.environ.get("FACEID_BLOQUEO_SEG", "60"))
# Tope general por usuario (cualquier tipo de intento) para limitar la carga: si en TOPE_VENTANA_SEG hay
# TOPE_INTENTOS intentos, se hace una pausa de TOPE_PAUSA_SEG antes de admitir más.
TOPE_INTENTOS = int(os.environ.get("FACEID_TOPE_INTENTOS", "10"))
TOPE_VENTANA_SEG = int(os.environ.get("FACEID_TOPE_VENTANA_SEG", "300"))
TOPE_PAUSA_SEG = int(os.environ.get("FACEID_TOPE_PAUSA_SEG", "30"))

# Modo B, identificación 1:N (solo contra los usuarios registrados en la app, NO contra las 24 del dataset).
# Un fotograma vota por su mejor candidato si su puntuación >= umbral oficial Y supera al segundo candidato por al menos
# MARGEN_1N. Se acepta si un mismo usuario recibe >= MIN_VOTOS votos. MARGEN_1N NO se calibró: el 1:N no se evaluó en el Sprint 2.
MARGEN_1N = float(os.environ.get("FACEID_MARGEN_1N", "0.05"))
# Bloqueo por IP en el modo B: intentos no identificados consecutivos (con suficientes fotogramas válidos)
BLOQUEO_IP_FALLOS = int(os.environ.get("FACEID_BLOQUEO_IP_FALLOS", "3"))
BLOQUEO_IP_SEG = int(os.environ.get("FACEID_BLOQUEO_IP_SEG", "60"))

# Palabra clave opcional por usuario (rostro + palabra clave). Solo se guarda el hash scrypt con sal.
CLAVE_MIN = 6
CLAVE_MAX = 128
CLAVE_TOKEN_SEG = 120     # tiempo para escribir la palabra clave tras el paso del rostro

# Registro de usuarios por el administrador (tarea 3.3)
REGISTRO_MIN_FOTOS = 10
REGISTRO_MAX_FOTOS = 20
REGISTRO_MIN_VALIDAS = 8   # fotos con un rostro válido necesarias para calcular la plantilla
ID_PATRON = r"[A-Za-z0-9_\-]{1,32}"   # seudónimo corto (p. ej. V01); sin espacios ni rutas

# Modo explicación (exposición): muestra el camino de la decisión (cajas, capas de la CNN, puntuaciones y umbral).
# Solo en la instancia local; la pública del túnel nunca lo ofrece. FACEID_EXPLICACION=0 lo desactiva también en local.
EXPLICACION = os.environ.get("FACEID_EXPLICACION", "1") != "0"


# Exposición por túnel (Cloudflare Tunnel hacia 127.0.0.1:5000). La instancia PÚBLICA solo verifica: no registra
# las rutas de administración (404), exige autenticación básica y limita peticiones por IP real.
# La administración corre en OTRA instancia (puerto 5001, 127.0.0.1) a la que el túnel nunca apunta.
MODO_PUBLICO = os.environ.get("FACEID_MODO_PUBLICO") == "1"
LIMITE_IP_PETICIONES = int(os.environ.get("FACEID_LIMITE_IP_PETICIONES", "20"))   # verificaciones por IP...
LIMITE_IP_VENTANA_SEG = int(os.environ.get("FACEID_LIMITE_IP_VENTANA_SEG", "60"))  # ...en esta ventana
LIMITE_AUTH_FALLOS = int(os.environ.get("FACEID_LIMITE_AUTH_FALLOS", "10"))        # contraseñas fallidas por IP...
LIMITE_AUTH_VENTANA_SEG = int(os.environ.get("FACEID_LIMITE_AUTH_VENTANA_SEG", "600"))  # ...en esta ventana


def acceso_publico():
    """Contraseña de la autenticación básica de la instancia pública (FACEID_ACCESO_PUBLICO)."""
    p = os.environ.get("FACEID_ACCESO_PUBLICO")
    return p if p else None


# Acceso remoto a la administración desde dispositivos propios (Tailscale + `tailscale serve`, ver README).
# La instancia sigue escuchando solo en 127.0.0.1; tailscale serve es el proxy local que pone HTTPS.
ADMIN_FALLOS_MAX = int(os.environ.get("FACEID_ADMIN_FALLOS_MAX", "5"))          # contraseñas de admin fallidas...
ADMIN_FALLOS_VENTANA_SEG = int(os.environ.get("FACEID_ADMIN_FALLOS_VENTANA_SEG", "600"))  # ...en esta ventana: pausa
# Cabeceras que solo existen si la petición entró por internet: Cloudflare (túnel) o Tailscale Funnel.
CABECERAS_INTERNET = ("CF-Ray", "CF-Connecting-IP", "Tailscale-Funnel-Request")


def admin_hosts():
    """Nombres de host que acepta la instancia de administración (protege también contra DNS rebinding)."""
    extra = [h.strip().lower() for h in os.environ.get("FACEID_ADMIN_HOSTS", "").split(",") if h.strip()]
    return ["127.0.0.1", "localhost", "::1"] + extra


def admin_password():
    """Contraseña del administrador desde FACEID_ADMIN_PASSWORD. None => administración deshabilitada."""
    p = os.environ.get("FACEID_ADMIN_PASSWORD")
    return p if p else None

MAX_BYTES_PETICION = 20 * 1024 * 1024


def device():
    d = os.environ.get("FACEID_DEVICE")
    if d:
        return d
    import torch
    return "cuda" if torch.cuda.is_available() else "cpu"
