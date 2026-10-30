"""ENSAYO de tiempos del servidor (tarea 3.4) con fotos del dataset encuadradas en 640x480, no con la cámara real.

Mide, a través de la API (/api/verificar), el procesamiento de un intento de 5 fotogramas en GPU y en CPU:
decodificación JPEG + detección MTCNN + embedding FaceNet + decisión. No incluye la captura en el navegador
(unos 1,6-2 s, se mide con la cámara real en modo pruebas). Usa una carpeta de datos temporal (no toca la real).

Uso:  .venv/Scripts/python -m app.medir_tiempos_ensayo --repeticiones 20 --csv docs/sprint3/ENSAYO_tiempos_servidor.csv
"""
import argparse
import base64
import shutil
import sys
import tempfile
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.almacen import Almacen  # noqa: E402
from app.intentos import ControlIntentos  # noqa: E402
from app.main import create_app  # noqa: E402
from app.servicio import ServicioVerificacion  # noqa: E402
from src import config as SC, data as D  # noqa: E402


def marco(img, w=640, h=480):
    s = min(w / img.shape[1], h / img.shape[0])
    im = cv2.resize(img, (int(img.shape[1] * s), int(img.shape[0] * s)), interpolation=cv2.INTER_AREA)
    out = np.full((h, w, 3), 40, np.uint8)
    y, x = (h - im.shape[0]) // 2, (w - im.shape[1]) // 2
    out[y:y + im.shape[0], x:x + im.shape[1]] = im
    return out


def b64(rgb):
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


def medir(device, repeticiones, persona="Brad Pitt"):
    tmp = Path(tempfile.mkdtemp(prefix="faceid_ensayo_"))
    alm = Almacen(tmp / "privado")
    srv = ServicioVerificacion(device=device, almacen=alm)
    ctl = ControlIntentos(alm.dir, tope=10_000)          # sin pausas durante la medición
    app = create_app(srv, alm, ctl, modo_pruebas=False)
    c = app.test_client()
    sp = D.load_split_table()
    fotos = []
    for f in sp[(sp.split == "val") & (sp.person == persona)].filename:
        im = marco(D.read_rgb(SC.ORIGINALS_DIR / persona / f))
        if srv.analizar(im)[0] == "valido":
            fotos.append(b64(im))
        if len(fotos) == 5:
            break
    filas = []
    for k in range(repeticiones + 2):                    # 2 de calentamiento
        t0 = time.perf_counter()
        j = c.post("/api/verificar", json={"usuario": persona, "fotogramas": fotos}).get_json()
        dt = time.perf_counter() - t0
        if k >= 2:
            filas.append({"dispositivo": "GPU" if device == "cuda" else "CPU", "resultado": j["resultado"],
                          "segundos_servidor": j["segundos_servidor"], "segundos_peticion": dt})
    shutil.rmtree(tmp, ignore_errors=True)   # la carpeta temporal del ensayo no se conserva
    return filas


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repeticiones", type=int, default=20)
    ap.add_argument("--csv", default=None)
    a = ap.parse_args(argv)
    filas = []
    for dev in (["cuda"] if torch.cuda.is_available() else []) + ["cpu"]:
        filas += medir(dev, a.repeticiones)
    d = pd.DataFrame(filas)
    res = d.groupby("dispositivo").agg(n=("segundos_peticion", "size"),
                                       servidor_mediana_s=("segundos_servidor", "median"),
                                       servidor_p95_s=("segundos_servidor", lambda x: x.quantile(0.95)),
                                       peticion_mediana_s=("segundos_peticion", "median"),
                                       peticion_p95_s=("segundos_peticion", lambda x: x.quantile(0.95)),
                                       resultados=("resultado", lambda x: ", ".join(f"{k}: {v}" for k, v in x.value_counts().items())))
    res = res.round(3).reset_index()
    res.insert(0, "fuente", "ENSAYO: 5 fotos del dataset (val) encuadradas en 640x480; no es la cámara real")
    res["fecha"] = time.strftime("%Y-%m-%d")
    print(res.to_string(index=False))
    if a.csv:
        res.to_csv(a.csv, index=False)
        print("Guardado:", a.csv)


if __name__ == "__main__":
    sys.exit(main())
