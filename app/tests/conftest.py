import base64
import sys
import threading
from pathlib import Path

import cv2
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    config.addinivalue_line("markers", "lento: usa el modelo real (MTCNN + FaceNet); tarda decenas de segundos")


@pytest.fixture(scope="session")
def root():
    return ROOT


def jpeg_b64(color=128, shape=(48, 64, 3)):
    """Imagen JPEG en data URL. color=0 hace que el servicio doble la trate como 'sin rostro'."""
    img = np.full(shape, color, np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


class Reloj:
    def __init__(self, t=1_000_000.0):
        self.t = t

    def __call__(self):
        return self.t


class ServicioDoble:
    """Imita a ServicioVerificacion sin modelo. 'resultado' fija la decisión de verificar()."""

    def __init__(self, almacen=None, resultado="permitido"):
        import torch
        self.torch = torch
        self.almacen, self.resultado = almacen, resultado
        self.lock = threading.Lock()
        self.recibidos = []
        self.explicados = []

    def usuarios(self):
        demo = self.almacen.usuarios() if self.almacen else []
        return [(u, "demo") for u in demo] + [("Brad Pitt", "dataset"), ("Tom Cruise", "dataset")]

    def analizar(self, rgb):
        if rgb.mean() < 5:
            return "sin_rostro", None
        return "valido", np.full((160, 160, 3), 100, np.uint8)

    def embeddings(self, crops):
        e = self.torch.ones((len(crops), 512))
        return e / e.norm(dim=1, keepdim=True)

    def usuarios_app(self):
        return self.almacen.usuarios() if self.almacen else []

    def _explicacion(self, modo):
        self.explicados.append(modo)
        return {"modo": modo, "umbral": 0.551421, "fotogramas": [], "rostro": None}

    def identificar(self, imgs, explicar=False):
        """1:N simulado. self.identifica_a = seudónimo que gana con claridad; None = nadie (no identificado);
        'calidad' = fotogramas sin rostro (no concluyente)."""
        from app import config as CFG, decision as D
        us = self.usuarios_app()
        objetivo = getattr(self, "identifica_a", us[0] if us else None)
        if objetivo == "calidad":
            estados, punt = ["sin_rostro"] * 5, [None] * 5
        else:
            estados = ["valido"] * 5
            punt = [[0.9 if u == objetivo else 0.1 for u in us] for _ in range(5)]
        r = D.identificar(estados, punt, us, CFG.UMBRAL_OFICIAL, CFG.MARGEN_1N, 3, 3)
        r.update(estados=estados, segundos_servidor=0.01)
        if explicar:
            r["explicacion"] = self._explicacion("B")
        return r

    def verificar(self, usuario, imgs, explicar=False):
        from app import config as CFG, decision as D
        self.recibidos.append((usuario, len(imgs), imgs[0].shape))
        estados = ["valido"] * 5 if self.resultado != "no_concluyente" else ["sin_rostro"] * 5
        punt = [0.9 if self.resultado == "permitido" else 0.1] * 5
        r = D.decidir(estados, punt, CFG.UMBRAL_OFICIAL, 3, 3)
        r.update(estados=estados, segundos_servidor=0.01)
        if explicar:
            r["explicacion"] = self._explicacion("A")
        return r


@pytest.fixture
def entorno_app(tmp_path):
    """App completa con almacén y control reales en una carpeta temporal y un servicio doble."""
    from app.almacen import Almacen
    from app.intentos import ControlIntentos
    from app.main import create_app
    alm = Almacen(tmp_path / "privado")
    reloj = Reloj()
    ctl = ControlIntentos(alm.dir, reloj=reloj)
    srv = ServicioDoble(alm)
    app = create_app(srv, alm, ctl)
    app.config["TESTING"] = True
    return {"app": app, "c": app.test_client(), "srv": srv, "alm": alm, "ctl": ctl, "reloj": reloj}
