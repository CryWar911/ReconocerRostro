"""Aplicación web de verificación facial (Sprint 3). Usa el modelo de la carpeta models/ como biblioteca."""
import sys
from pathlib import Path

# Permite importar src/ (paquete del modelo y detección de la tarea 2.6) sin instalarlo.
_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
