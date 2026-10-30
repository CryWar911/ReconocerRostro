"""Privacidad y honestidad: sin imágenes guardadas, datos fuera del repositorio, avisos en "Acerca de",
y lectura en solo lectura del almacén por el script de video de la tarea 2.6."""
import hashlib

import numpy as np
import pytest

from app import config as CFG
from conftest import jpeg_b64

EXT_IMG = ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp", "*.mp4")


def imagenes(carpeta):
    return [p for e in EXT_IMG for p in carpeta.rglob(e)]


def test_verificar_no_guarda_imagenes(entorno_app):
    c, srv = entorno_app["c"], entorno_app["srv"]
    for res in ["permitido", "denegado", "no_concluyente"]:
        srv.resultado = res
        c.post("/api/verificar", json={"usuario": "Brad Pitt", "fotogramas": [jpeg_b64()] * 5})
    entorno_app["app"].modo_pruebas = True
    c.post("/api/verificar", json={"usuario": "Brad Pitt", "fotogramas": [jpeg_b64()] * 5, "caso": "CF01"})
    assert imagenes(entorno_app["alm"].dir) == []


def test_carpeta_por_defecto_fuera_del_repositorio(root, monkeypatch):
    import importlib
    monkeypatch.delenv("FACEID_APP_DATA", raising=False)
    cfg = importlib.reload(CFG)
    try:
        d = cfg.DATA_DIR.resolve()
        assert root.resolve() not in d.parents and d != root.resolve()
    finally:
        importlib.reload(CFG)


def test_acerca_avisos(entorno_app):
    html = entorno_app["c"].get("/acerca").get_data(as_text=True)
    assert "No tiene detección de vida" in html
    assert "Kaggle" in html and "no con una cámara web" in html
    assert "prueba con el video de los voluntarios todavía está pendiente" in html


def test_script_video_lee_almacen_en_solo_lectura(tmp_path):
    from app.almacen import Almacen
    from src import video as VID
    alm = Almacen(tmp_path / "privado")
    t = np.random.default_rng(0).normal(size=512).astype(np.float32)
    alm.guardar("V01", t, {"id": "V01"})
    f = alm.dir_usuarios / "V01" / "plantilla.npy"
    antes = (hashlib.sha256(f.read_bytes()).hexdigest(), f.stat().st_mtime_ns)
    ids, T = VID.cargar_plantillas_app(alm.dir)
    assert ids == ["V01"] and T.shape == (1, 512)
    assert np.allclose(T[0], t / np.linalg.norm(t), atol=1e-6)
    assert (hashlib.sha256(f.read_bytes()).hexdigest(), f.stat().st_mtime_ns) == antes
    assert sorted(p.name for p in alm.dir.rglob("*") if p.is_file()) == ["meta.json", "plantilla.npy"]


def test_script_video_une_almacen_y_dataset_sin_cambiar_reglas(tmp_path):
    if not (CFG.PAQUETE_MODELO / "red.ts").exists():
        pytest.skip("Falta el paquete del modelo")
    from app.almacen import Almacen
    from src import config as SC
    from src.video_verificacion import cargar_verificador
    alm = Almacen(tmp_path / "privado")
    alm.guardar("V01", np.ones(512, np.float32), {"id": "V01"})
    v = cargar_verificador(CFG.PAQUETE_MODELO, "cpu", None, alm.dir)
    assert v.users[-1] == "V01" and v.group[-1] == "voluntario" and v.T.shape == (25, 512)
    assert v.threshold == SC.UMBRAL_OFICIAL == CFG.UMBRAL_OFICIAL
    assert SC.VIDEO_VENTANA == 5 and SC.VIDEO_CADA_N == 3
