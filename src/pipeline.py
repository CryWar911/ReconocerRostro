"""Paquete reutilizable del verificador: red (TorchScript) + plantillas + configuracion.

Estructura en disco (models/<nombre>/, ignorado por git):
  red.ts          red de embeddings exportada con TorchScript (no requiere facenet-pytorch para cargarla)
  plantillas.npz  plantillas (n_usuarios, D) float32 + nombres de usuario
  config.json     preprocesado, metrica, umbral (null hasta la tarea 2.3), versiones, procedencia
"""
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from . import data as D
from . import models as M


def export_torchscript(model, path, norm, size=160, device="cuda"):
    """Exporta la funcion imagen->embedding con torch.jit.trace y comprueba que coincide con la red original."""
    model = model.eval().to(device)

    class _Emb(torch.nn.Module):
        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, x):
            f = self.m.features(x) if hasattr(self.m, "features") else self.m(x)
            return F.normalize(f, dim=1)

    wrap = _Emb(model).eval()
    ex = M.to_tensor(np.random.default_rng(0).integers(0, 255, (4, size, size, 3), dtype=np.uint8), norm, device)
    with torch.no_grad():
        ts = torch.jit.trace(wrap, ex)
        err = (ts(ex) - wrap(ex)).abs().max().item()
    ts.save(str(path))
    return err


def save_package(folder, ts_model_path, templates, users, config):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    np.savez(folder / "plantillas.npz", T=templates.astype(np.float32), usuarios=np.array(users))
    cfg = dict(config, red=Path(ts_model_path).name, n_usuarios=len(users), dim=int(templates.shape[1]))
    (folder / "config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


class Verifier:
    """Verificacion 1 a 1 a partir de un paquete guardado. No usa facenet-pytorch."""

    def __init__(self, folder, device="cpu", voluntarios=None):
        """voluntarios: nombre de un archivo de plantillas adicionales (p. ej. plantillas_voluntarios.npz)
        en la carpeta del paquete. Se ANADEN a las del dataset; plantillas.npz no se modifica."""
        folder = Path(folder)
        t0 = time.perf_counter()
        self.cfg = json.loads((folder / "config.json").read_text(encoding="utf-8"))
        self.net = torch.jit.load(str(folder / self.cfg["red"]), map_location=device).eval()
        z = np.load(folder / "plantillas.npz")
        self.users = [str(u) for u in z["usuarios"]]
        T = z["T"]
        self.group = ["dataset"] * len(self.users)
        if voluntarios is not None:
            zv = np.load(folder / voluntarios)
            extra = [str(u) for u in zv["usuarios"]]
            assert not set(extra) & set(self.users), "un voluntario usa el nombre de una identidad del dataset"
            self.users += extra
            self.group += ["voluntario"] * len(extra)
            T = np.concatenate([T, zv["T"]])
        self.T = torch.as_tensor(T, device=device)
        self.device = device
        self.threshold = self.cfg.get("umbral")
        self.load_seconds = time.perf_counter() - t0

    @torch.no_grad()
    def embed(self, faces_uint8):
        """faces_uint8: (N,160,160,3) RGB ya recortadas -> (N,D) normalizados."""
        return self.net(M.to_tensor(faces_uint8, self.cfg["normalizacion"], self.device))

    @torch.no_grad()
    def score(self, face_uint8, claimed_user):
        e = self.embed(face_uint8[None])
        return float(e[0] @ self.T[self.users.index(claimed_user)])

    def verify(self, face_uint8, claimed_user, threshold=None):
        """Devuelve (aceptado, puntuacion). Requiere umbral (config o argumento)."""
        thr = self.threshold if threshold is None else threshold
        if thr is None:
            raise ValueError("Umbral no fijado todavia (se fija en la tarea 2.3 con validacion).")
        s = self.score(face_uint8, claimed_user)
        return s >= thr, s

    def verify_path(self, path, claimed_user, threshold=None):
        im = D.read_rgb(path)
        if im.shape[:2] != (160, 160):
            im = D.load_images([path])[0]
        return self.verify(im, claimed_user, threshold)
