"""Registro de un voluntario: plantilla FaceNet (media de embeddings) a partir de sus fotos.

Uso (desde la raiz del proyecto):
    .venv/Scripts/python -m src.registro_voluntario --fotos D:/privado/V01 --id V01

- Las fotos deben estar FUERA del repositorio (o en data/, ignorada por git).
- Usa el mismo FaceNet VGGFace2 congelado del paquete y deteccion MTCNN (margen de config).
- Guarda/actualiza <paquete>/plantillas_voluntarios.npz. NUNCA modifica plantillas.npz (24 del dataset).
- Usa un identificador seudonimo (V01, V02...), no el nombre real; la correspondencia queda fuera del repo.
- No guarda fotos ni recortes; solo la plantilla (vector de 512) y conteos.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

from . import config as C
from . import pipeline as P
from . import video as VID

EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def register(fotos, uid, paquete=None, archivo=C.PLANTILLAS_VOLUNTARIOS, device="cuda", reemplazar=False, min_rostros=3):
    paquete = Path(paquete or C.MODELS_DIR / "verificador_facenet_vggface2")
    fotos = VID.check_private_path(fotos)
    if not re.fullmatch(r"[A-Za-z0-9_\-]{1,32}", uid):
        raise ValueError("El id debe ser un codigo seudonimo corto (letras, numeros, _ o -), p. ej. V01")
    base = P.Verifier(paquete, device=device)
    if uid in base.users:
        raise ValueError(f"'{uid}' coincide con una identidad del dataset")
    paths = sorted(p for p in fotos.iterdir() if p.suffix.lower() in EXT)
    if not paths:
        raise ValueError(f"No hay imagenes en {fotos}")
    t0 = time.perf_counter()
    tpl, n_fotos, n_rostros = VID.template_from_photos(paths, VID.FaceCropper(device), base)
    secs = time.perf_counter() - t0
    if tpl is None or n_rostros < min_rostros:
        raise ValueError(f"Solo se detecto rostro en {n_rostros} de {n_fotos} fotos (minimo {min_rostros})")
    dest = paquete / archivo
    users, T, meta = [], np.zeros((0, tpl.shape[0]), np.float32), {}
    if dest.exists():
        z = np.load(dest, allow_pickle=False)
        users, T = [str(u) for u in z["usuarios"]], z["T"]
        meta = json.loads(str(z["meta"]))
    if uid in users:
        if not reemplazar:
            raise ValueError(f"'{uid}' ya esta registrado en {archivo} (usa --reemplazar)")
        k = users.index(uid)
        users.pop(k)
        T = np.delete(T, k, axis=0)
    users.append(uid)
    T = np.vstack([T, tpl[None].astype(np.float32)])
    meta[uid] = {"n_fotos": n_fotos, "n_rostros": n_rostros, "segundos": secs, "fecha": time.strftime("%Y-%m-%d %H:%M"),
                 "margen_mtcnn": C.VIDEO_MTCNN_MARGEN}
    np.savez(dest, T=T, usuarios=np.array(users), meta=json.dumps(meta))
    return {"id": uid, "archivo": str(dest), "n_fotos": n_fotos, "n_rostros": n_rostros, "segundos": round(secs, 2),
            "voluntarios_registrados": users}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fotos", required=True, help="carpeta con las fotos del voluntario (fuera del repositorio)")
    ap.add_argument("--id", required=True, help="identificador seudonimo, p. ej. V01")
    ap.add_argument("--paquete", default=None, help="carpeta del paquete FaceNet (por defecto models/verificador_facenet_vggface2)")
    ap.add_argument("--archivo", default=C.PLANTILLAS_VOLUNTARIOS, help="archivo de plantillas de voluntarios dentro del paquete")
    ap.add_argument("--dispositivo", default="cuda")
    ap.add_argument("--reemplazar", action="store_true")
    a = ap.parse_args(argv)
    r = register(a.fotos, a.id, a.paquete, a.archivo, a.dispositivo, a.reemplazar)
    print(json.dumps(r, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
