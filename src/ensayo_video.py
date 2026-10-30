"""ENSAYO de la tarea 2.6: genera datos SIMULADOS con el propio dataset para probar los scripts de
registro y de video mientras no existan el video y las fotos reales de los voluntarios.

NO es una evaluacion: los "voluntarios" son identidades del dataset NO registradas (no tienen plantilla
entre las 24): ENSAYO_V01 = Hugh Jackman, ENSAYO_V02 = Natalie Portman. Los "no registrados" son
Courtney Cox y Kashyap. Se usan fotos de Original Images (sin recortar) para ejercitar el detector.
Las fotos de registro y las del video pertenecen a grupos de casi duplicados distintos.
Todo se escribe en data/ensayo/ (ignorada por git).
"""
import cv2
import numpy as np
import pandas as pd

from . import config as C
from . import data as D

VOLUNTARIOS = {"ENSAYO_V01": "Hugh Jackman", "ENSAYO_V02": "Natalie Portman"}
NO_REGISTRADOS = {"no registrado A": "Courtney Cox", "no registrado B": "Kashyap"}
N_REGISTRO, N_VIDEO = 10, 5
FPS, SEG_POR_FOTO, W, H = 15, 1.2, 640, 480


def _pick(person, sp, rng):
    g = sp[sp.person == person]
    groups = list(dict.fromkeys(g.sort_values("filename").group_id))
    rng.shuffle(groups)
    reg, vid = [], []
    for gid in groups:
        files = g[g.group_id == gid].filename.tolist()
        if len(reg) < N_REGISTRO:
            reg += files[:N_REGISTRO - len(reg)]
        elif len(vid) < N_VIDEO:
            vid.append(files[0])
    return reg, vid


def _letterbox(img, scale=1.0, dx=0, dy=0):
    h, w = img.shape[:2]
    s = min(W / w, H / h) * scale
    M = np.float32([[s, 0, (W - w * s) / 2 + dx], [0, s, (H - h * s) / 2 + dy]])
    return cv2.warpAffine(img, M, (W, H), borderMode=cv2.BORDER_CONSTANT, borderValue=(40, 40, 40))


def build(out_dir=None, seed=C.SEED):
    """Crea fotos de registro, video .mp4 y anotaciones .csv. Devuelve dict de rutas y conteos."""
    out = (out_dir or C.ROOT / "data" / "ensayo")
    out.mkdir(parents=True, exist_ok=True)
    sp = D.load_split_table()
    rng = np.random.default_rng(seed)
    personas = {**VOLUNTARIOS, **NO_REGISTRADOS}
    plan = {k: _pick(p, sp, rng) for k, p in personas.items()}
    for vid_id, person in VOLUNTARIOS.items():
        d = out / "fotos_registro" / vid_id
        d.mkdir(parents=True, exist_ok=True)
        for f in d.glob("*"):
            f.unlink()
        for f in plan[vid_id][0]:
            img = cv2.imread(str(C.ORIGINALS_DIR / person / f))
            cv2.imwrite(str(d / f"{vid_id}_{f.rsplit('_', 1)[1]}"), img)
    vw = cv2.VideoWriter(str(out / "video_ensayo.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    n_per = int(round(FPS * SEG_POR_FOTO))
    t, ann, k = 0.0, [], 0
    for label in list(VOLUNTARIOS) + list(NO_REGISTRADOS):
        for _ in range(int(FPS * 0.5)):                       # 0,5 s de separacion sin anotar
            vw.write(np.full((H, W, 3), 40, np.uint8)); k += 1
        start = k / FPS
        for j, f in enumerate(plan[label][1]):
            img = cv2.imread(str(C.ORIGINALS_DIR / personas[label] / f))
            blur = j == len(plan[label][1]) - 1               # la ultima foto de cada tramo, desenfocada (caso dificil)
            b0 = rng.uniform(-15, 15)
            for i in range(n_per):
                a = i / max(1, n_per - 1)
                fr = _letterbox(img, 1.0 + 0.10 * a, 20 * np.sin(2 * np.pi * a), 10 * a)
                fr = np.clip(fr.astype(np.float32) + b0 + rng.normal(0, 4, fr.shape), 0, 255).astype(np.uint8)
                if blur:
                    fr = cv2.GaussianBlur(fr, (0, 0), 4)
                vw.write(fr); k += 1
        ann.append({"inicio_s": round(start, 4), "fin_s": round(k / FPS, 4), "identidad": label})
    vw.release()
    ann = pd.DataFrame(ann)
    ann.to_csv(out / "anotaciones_ensayo.csv", index=False)
    return {"carpeta": out, "video": out / "video_ensayo.mp4", "anotaciones": out / "anotaciones_ensayo.csv",
            "fotos_registro": {v: out / "fotos_registro" / v for v in VOLUNTARIOS}, "duracion_s": k / FPS,
            "fotogramas": k, "fotos_video_por_tramo": N_VIDEO, "fotos_registro_por_voluntario": N_REGISTRO,
            "anotaciones_df": ann}
