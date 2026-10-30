"""Rutas y constantes compartidas del proyecto."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Pesos preentrenados (FaceNet, ResNet-18) dentro del proyecto, en models/ (ignorado por git)
os.environ.setdefault("TORCH_HOME", str(ROOT / "models" / "torch_hub"))
DATA_RAW = ROOT / "data" / "raw" / "Dataset"
FACES_DIR = DATA_RAW / "Faces" / "Faces"          # unica fuente de imagenes usada
ORIGINALS_DIR = DATA_RAW / "Original Images" / "Original Images"  # NO se usa (mismas fotos)
CSV_PATH = DATA_RAW / "Dataset.csv"
DATA_PROCESSED = ROOT / "data" / "processed"
MODELS_DIR = ROOT / "models"
DOCS = ROOT / "docs" / "sprint2"
FIGS = DOCS / "figuras"

SEED = 42
IMG_SIZE = 160  # las caras de Faces ya vienen a 160x160; entrada nativa de FaceNet

# Protocolo de verificacion (confirmado por el usuario, 2026-10-23)
FORCED_REGISTERED = ["Marmik"]          # usuario no famoso registrado
FORCED_IMPOSTOR_TEST = ["Kashyap"]      # impostora no famosa, solo en prueba
SPLIT_FRACTIONS = {"train": 0.70, "val": 0.15, "test": 0.15}

# Genero APROXIMADO, asignado solo a partir del nombre de pila (no de los rostros) y
# confirmado por el usuario el 2026-10-23. Se usa UNICAMENTE para estratificar el sorteo
# de impostoras. Casos ambiguos por nombre: Billie Eilish, Courtney Cox, Kashyap, Marmik.
GENDER_BY_NAME = {
    "Akshay Kumar": "M", "Alexandra Daddario": "F", "Alia Bhatt": "F", "Amitabh Bachchan": "M",
    "Andy Samberg": "M", "Anushka Sharma": "F", "Billie Eilish": "F", "Brad Pitt": "M",
    "Camila Cabello": "F", "Charlize Theron": "F", "Claire Holt": "F", "Courtney Cox": "F",
    "Dwayne Johnson": "M", "Elizabeth Olsen": "F", "Ellen Degeneres": "F", "Henry Cavill": "M",
    "Hrithik Roshan": "M", "Hugh Jackman": "M", "Jessica Alba": "F", "Kashyap": "M",
    "Lisa Kudrow": "F", "Margot Robbie": "F", "Marmik": "M", "Natalie Portman": "F",
    "Priyanka Chopra": "F", "Robert Downey Jr": "M", "Roger Federer": "M", "Tom Cruise": "M",
    "Vijay Deverakonda": "M", "Virat Kohli": "M", "Zac Efron": "M",
}
# Impostoras por conjunto y genero (incluye las forzadas): val 2M+1F, test 2M+2F -> registradas 12M/12F
IMPOSTOR_QUOTA = {"val": {"M": 2, "F": 1}, "test": {"M": 2, "F": 2}}
# Primer sorteo (sin estratificar), DESCARTADO antes de entrenar ningun modelo por desequilibrio
# de genero: val = Claire Holt, Ellen Degeneres, Jessica Alba (todas F).

# Video (tarea 2.6). Margen MTCNN 0: reproduce el recorte de Faces (coseno mediano 0.989 entre
# embeddings MTCNN(Original) y Faces en 150 imagenes de VALIDACION; margenes 10-44 dan 0.974-0.926).
VIDEO_MTCNN_MARGEN = 0
VIDEO_CADA_N = 3          # se procesa 1 de cada N fotogramas
VIDEO_VENTANA = 5         # fotogramas procesados por ventana de decision (votacion por mayoria)
UMBRAL_OFICIAL = 0.551421 # FaceNet VGGFace2, fijado en validacion (plan_evaluacion.md); NO se recalcula
PLANTILLAS_VOLUNTARIOS = "plantillas_voluntarios.npz"   # junto al paquete; no toca plantillas.npz

# Casi duplicados: correlacion de pixeles (32x32 color, tambien espejo) >= umbral, misma persona.
# Elegido revisando pares a ojo (cuaderno 01): hay fotos identicas hasta ~0.91; con 0.89 las
# cadenas de union-find ya forman grupos de 24 fotos distintas. 0.90 es el compromiso conservador.
DUP_CORR_THRESHOLD = 0.90
