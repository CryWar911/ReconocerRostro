"""Verificacion facial sobre video (tarea 2.6): deteccion MTCNN -> recorte 160x160 -> embedding
FaceNet -> coseno contra las plantillas -> umbral oficial -> votacion por mayoria por ventana.

Privacidad: este modulo nunca guarda imagenes ni recortes; solo puntuaciones y metricas.
Las rutas de fotos y videos personales deben estar FUERA del repositorio o dentro de data/
(ignorada por git): ver check_private_path.
"""
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import torch

from . import config as C
from .evaluation import clopper_pearson

NO_REG = "no registrado"


# ------------------------------------------------------------------ privacidad
def check_private_path(path):
    """Error si la ruta esta dentro del repositorio y fuera de data/ (podria acabar en git)."""
    p = Path(path).resolve()
    root, data = C.ROOT.resolve(), (C.ROOT / "data").resolve()
    if (root == p or root in p.parents) and not (data == p or data in p.parents):
        raise ValueError(f"{p} esta dentro del repositorio y fuera de data/: los datos personales no pueden ir a git.")
    return p


# ------------------------------------------------------------------ deteccion
class FaceCropper:
    """MTCNN de facenet-pytorch. Devuelve el rostro mas grande recortado a 160x160 RGB uint8
    (margen C.VIDEO_MTCNN_MARGEN, igual que el recorte del dataset Faces) o None."""

    def __init__(self, device="cuda", margin=C.VIDEO_MTCNN_MARGEN):
        from facenet_pytorch import MTCNN
        self.m = MTCNN(image_size=160, margin=margin, post_process=False, select_largest=True, device=device)

    @torch.no_grad()
    def __call__(self, rgb):
        crop, prob = self.m(rgb, return_prob=True)
        if crop is None:
            return None, None
        return crop.permute(1, 2, 0).clamp(0, 255).byte().cpu().numpy(), float(prob)


def template_from_photos(paths, cropper, verifier):
    """Plantilla = media de los embeddings (L2) de los rostros detectados en las fotos, renormalizada.
    Devuelve (plantilla, n_fotos, n_rostros)."""
    crops = []
    for p in paths:
        img = cv2.imread(str(p), cv2.IMREAD_COLOR)
        if img is None:
            continue
        c, _ = cropper(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if c is not None:
            crops.append(c)
    if not crops:
        return None, len(paths), 0
    E = verifier.embed(np.stack(crops)).cpu().numpy()
    t = E.mean(0)
    return t / np.linalg.norm(t), len(paths), len(crops)


def cargar_plantillas_app(carpeta):
    """Lee en SOLO LECTURA las plantillas del almacén de la aplicación web (Sprint 3):
    <carpeta>/usuarios/<id>/plantilla.npy. No escribe nada. Devuelve (ids, T) con T de forma (n, 512)."""
    d = Path(carpeta) / "usuarios"
    ids, T = [], []
    for p in sorted(d.iterdir()) if d.exists() else []:
        f = p / "plantilla.npy"
        if f.is_file():
            ids.append(p.name)
            T.append(np.array(np.load(f, mmap_mode="r"), dtype=np.float32))
    return ids, (np.stack(T) if T else np.zeros((0, 512), np.float32))


# ------------------------------------------------------------------ anotaciones
def read_annotations(path):
    """CSV con columnas inicio_s, fin_s, identidad. identidad = id del voluntario registrado o
    'no registrado' (se admite 'no registrado <etiqueta>' para distinguir varias personas)."""
    a = pd.read_csv(path)
    missing = {"inicio_s", "fin_s", "identidad"} - set(a.columns)
    if missing:
        raise ValueError(f"Faltan columnas en las anotaciones: {missing}")
    a["identidad"] = a["identidad"].astype(str).str.strip()
    a["registrado"] = ~a["identidad"].str.lower().str.startswith(NO_REG)
    if (a.fin_s <= a.inicio_s).any():
        raise ValueError("Hay tramos con fin_s <= inicio_s")
    a = a.sort_values("inicio_s").reset_index(drop=True)
    if (a.inicio_s.values[1:] < a.fin_s.values[:-1]).any():
        raise ValueError("Hay tramos solapados")
    a["tramo"] = np.arange(len(a))
    return a


# ------------------------------------------------------------------ procesado del video
def process_video(path, cropper, verifier, every_n=C.VIDEO_CADA_N, annotations=None):
    """Procesa 1 de cada `every_n` fotogramas. Si hay anotaciones, solo los que caen en un tramo.

    Devuelve (frames, S, fps): frames = DataFrame por fotograma procesado (indice, t, rostro,
    prob, segundos de proceso), S = (n_procesados, n_plantillas) coseno (NaN si no hay rostro).
    El tiempo por fotograma incluye deteccion + recorte + embedding + comparacion con TODAS las plantillas.
    """
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise IOError(f"No se pudo abrir el video {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    T = verifier.T
    rows, scores = [], []
    k = -1
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        k += 1
        if k % every_n:
            continue
        t = k / fps
        tramo = None
        if annotations is not None:
            m = (annotations.inicio_s <= t) & (t < annotations.fin_s)
            if not m.any():
                continue
            tramo = int(annotations.tramo[m].iloc[0])
        t0 = time.perf_counter()
        crop, prob = cropper(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        if crop is not None:
            s = (verifier.embed(crop[None]) @ T.T)[0].cpu().numpy()
        else:
            s = np.full(len(verifier.users), np.nan, np.float32)
        dt = time.perf_counter() - t0
        rows.append({"fotograma": k, "t_s": t, "tramo": tramo, "rostro": crop is not None, "prob": prob, "segundos": dt})
        scores.append(s)
    cap.release()
    return pd.DataFrame(rows), np.array(scores, dtype=np.float32).reshape(len(rows), len(verifier.users)), fps


# ------------------------------------------------------------------ evaluacion
def _windows(frames, size):
    """Ventanas consecutivas, sin solape, de `size` fotogramas procesados dentro de cada tramo.
    Se descarta la ventana final incompleta de cada tramo."""
    out = []
    for tramo, g in frames.groupby("tramo"):
        idx = g.index.to_numpy()
        for s in range(0, len(idx) - size + 1, size):
            out.append((tramo, idx[s:s + size]))
    return out


def evaluate_video(frames, S, users, groups, annotations, thr=C.UMBRAL_OFICIAL, window=C.VIDEO_VENTANA):
    """Comparaciones por fotograma y por ventana con el protocolo de las tareas 2.1-2.5.

    - genuina: fotograma de un voluntario registrado contra SU plantilla
    - impostora: fotograma de cualquier persona contra la plantilla de OTRO voluntario
      (si es un voluntario registrado = impostora interna; si es 'no registrado' = externa)
    - impostora frente al dataset (complementaria): cualquier fotograma contra las 24 plantillas del dataset
    Fotograma sin rostro: no hay puntuacion; cuenta como RECHAZO (se reporta aparte la tasa sin rostro).
    Ventana: se acepta si al menos floor(W/2)+1 de sus W fotogramas tienen rostro y puntuacion >= umbral.
    """
    users = list(users)
    vol = [i for i, g in enumerate(groups) if g == "voluntario"]
    dset = [i for i, g in enumerate(groups) if g == "dataset"]
    ann = annotations.set_index("tramo")
    ident = frames.tramo.map(ann.identidad).to_numpy()
    acc = np.where(np.isnan(S), False, S >= thr)          # aceptacion por fotograma y plantilla
    comps = []                                            # (nivel, tipo, persona, plantilla, aceptada, rostro/votos)
    for i in range(len(frames)):
        p = ident[i]
        for j in vol + dset:
            u = users[j]
            if u == p:
                tipo = "genuina"
            elif j in vol:
                tipo = "impostora interna" if p in users else "impostora externa"
            else:
                tipo = "impostora vs dataset"
            comps.append(("fotograma", tipo, p, u, bool(acc[i, j]), bool(frames.rostro.iat[i])))
    need = window // 2 + 1
    for tramo, idx in _windows(frames, window):
        p = ann.identidad[tramo]
        for j in vol + dset:
            u = users[j]
            votes = int(acc[idx, j].sum())
            tipo = "genuina" if u == p else ("impostora interna" if (j in vol and p in users) else
                                             "impostora externa" if j in vol else "impostora vs dataset")
            comps.append(("ventana", tipo, p, u, votes >= need, int(frames.rostro.iloc[idx].sum())))
    return pd.DataFrame(comps, columns=["nivel", "tipo", "persona", "plantilla", "aceptada", "rostro_o_n_rostros"])


def summarize(comps, frames, annotations):
    """Metricas agregadas (sin datos por fotograma): FAR/FRR por nivel y tipo, por persona, y tasa sin rostro."""
    rows = []
    for (nivel, tipo), g in comps.groupby(["nivel", "tipo"]):
        if tipo == "genuina":
            k, n, met = int((~g.aceptada).sum()), len(g), "FRR"
        else:
            k, n, met = int(g.aceptada.sum()), len(g), "FAR"
        rows.append({"nivel": nivel, "tipo": tipo, "persona": "todas", "metrica": met, "errores": k, "n": n,
                     "tasa": k / n if n else np.nan, "IC95": clopper_pearson(k, n)})
        if tipo == "genuina" and nivel == "fotograma":
            gd = g[g.rostro_o_n_rostros.astype(bool)]
            k2 = int((~gd.aceptada).sum())
            rows.append({"nivel": nivel, "tipo": "genuina (solo fotogramas con rostro)", "persona": "todas", "metrica": "FRR",
                         "errores": k2, "n": len(gd), "tasa": k2 / len(gd) if len(gd) else np.nan, "IC95": clopper_pearson(k2, len(gd))})
        for p, gp in g.groupby("persona"):
            k = int((~gp.aceptada).sum()) if met == "FRR" else int(gp.aceptada.sum())
            rows.append({"nivel": nivel, "tipo": tipo, "persona": p, "metrica": met, "errores": k, "n": len(gp),
                         "tasa": k / len(gp), "IC95": clopper_pearson(k, len(gp))})
    met = pd.DataFrame(rows)
    ann = annotations.set_index("tramo")
    f = frames.assign(persona=frames.tramo.map(ann.identidad))
    sin = f.groupby("persona").rostro.agg(procesados="size", con_rostro="sum").reset_index()
    sin.loc[len(sin)] = {"persona": "todas", "procesados": len(f), "con_rostro": int(f.rostro.sum())}
    sin["tasa_sin_rostro"] = 1 - sin.con_rostro / sin.procesados
    return met, sin


def sample_frames(path, n=40, every_n=C.VIDEO_CADA_N, annotations=None):
    """Hasta n fotogramas RGB (en memoria, nunca se guardan) repartidos por el video, para medir tiempos."""
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cand = range(0, total, every_n)
    if annotations is not None:
        cand = [k for k in cand if ((annotations.inicio_s <= k / fps) & (k / fps < annotations.fin_s)).any()]
    cand = list(cand)
    pick = set(np.linspace(0, len(cand) - 1, min(n, len(cand))).astype(int).tolist()) if cand else set()
    want = {cand[i] for i in pick}
    out, k = [], -1
    while want:
        ok, fr = cap.read()
        if not ok:
            break
        k += 1
        if k in want:
            out.append(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
            want.discard(k)
    cap.release()
    return out


def timing(frames_rgb, verifier_factory, cropper_factory, devices=("cuda", "cpu"), warm=3):
    """Tiempo por verificacion INCLUYENDO deteccion: MTCNN + recorte + embedding + coseno.
    frames_rgb: lista de fotogramas RGB. Devuelve DataFrame con mediana y p95 por dispositivo."""
    out = []
    for dev in devices:
        if dev == "cuda" and not torch.cuda.is_available():
            continue
        v, c = verifier_factory(dev), cropper_factory(dev)
        ts, nf = [], 0
        for k, fr in enumerate(list(frames_rgb[:warm]) + list(frames_rgb)):
            t0 = time.perf_counter()
            crop, _ = c(fr)
            if crop is not None:
                float((v.embed(crop[None]) @ v.T.T)[0, 0])
            else:
                nf += k >= warm
            if k >= warm:
                ts.append(time.perf_counter() - t0)
        out.append({"dispositivo": "GPU" if dev == "cuda" else "CPU", "n": len(ts), "sin_rostro": nf,
                    "mediana_s": float(np.median(ts)), "p95_s": float(np.percentile(ts, 95)), "max_s": float(np.max(ts))})
    return pd.DataFrame(out)
