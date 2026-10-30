"""Almacén privado de los usuarios de la demostración (registrados por el administrador).

Vive en config.DATA_DIR (variable FACEID_APP_DATA), que debe estar FUERA del repositorio o dentro de data/
(ignorada por git). Por usuario se guarda SOLO:
  usuarios/<id>/plantilla.npy   vector de 512 (media renormalizada de embeddings, como en la tarea 2.2)
  usuarios/<id>/meta.json       seudónimo, autorización escrita (sí + fecha), fecha de registro, conteos
  usuarios/<id>/fotos/          SOLO si el administrador pidió conservarlas (por defecto no existe)
Las 24 plantillas del dataset (models/) no se tocan.
"""
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import numpy as np

from src.video import check_private_path

from . import config as CFG


def restringir_permisos(path):
    """Solo el usuario actual puede leer/escribir. Windows: icacls sin herencia; POSIX: chmod 700/600.
    Devuelve True si se aplicó."""
    p = Path(path)
    try:
        if os.name == "nt":
            user = os.environ.get("USERNAME")
            if not user:
                return False
            r = subprocess.run(["icacls", str(p), "/inheritance:r", "/grant:r", f"{user}:(OI)(CI)F" if p.is_dir() else f"{user}:F"],
                               capture_output=True, text=True)
            return r.returncode == 0
        os.chmod(p, 0o700 if p.is_dir() else 0o600)
        return True
    except OSError:
        return False


class Almacen:
    def __init__(self, carpeta=None):
        self.dir = check_private_path(carpeta or CFG.DATA_DIR)   # error si cae dentro del repo fuera de data/
        self.dir_usuarios = self.dir / "usuarios"
        nuevo = not self.dir.exists()
        self.dir_usuarios.mkdir(parents=True, exist_ok=True)
        if nuevo:
            restringir_permisos(self.dir)
        self._cache = {}

    # ---------------------------------------------------------------- lectura
    def usuarios(self):
        return sorted(p.name for p in self.dir_usuarios.iterdir() if (p / "plantilla.npy").exists())

    def plantilla(self, uid):
        """Plantilla del usuario. La caché se invalida si el archivo cambia, así otra instancia de la app
        (p. ej. la de administración) puede registrar o reemplazar usuarios sin reiniciar esta."""
        f = self.dir_usuarios / uid / "plantilla.npy"
        clave = f.stat().st_mtime_ns
        if self._cache.get(uid, (None,))[0] != clave:
            self._cache[uid] = (clave, np.load(f))
        return self._cache[uid][1]

    def meta(self, uid):
        return json.loads((self.dir_usuarios / uid / "meta.json").read_text(encoding="utf-8"))

    # ---------------------------------------------------------------- escritura
    def guardar(self, uid, plantilla, meta, fotos_jpeg=None):
        """Guarda plantilla y metadatos. fotos_jpeg: lista de bytes JPEG, solo si se pidió conservarlas."""
        if not re.fullmatch(CFG.ID_PATRON, uid):
            raise ValueError("Seudónimo no válido")
        d = self.dir_usuarios / uid
        d.mkdir(parents=True, exist_ok=False)
        t = np.asarray(plantilla, dtype=np.float32)
        np.save(d / "plantilla.npy", t / np.linalg.norm(t))
        (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        if fotos_jpeg:
            (d / "fotos").mkdir()
            for k, b in enumerate(fotos_jpeg):
                (d / "fotos" / f"{k:02d}.jpg").write_bytes(b)
        for f in d.rglob("*"):
            restringir_permisos(f)
        restringir_permisos(d)
        self._cache.pop(uid, None)

    def actualizar_meta(self, uid, meta):
        """Reescribe meta.json (p. ej. al cambiar o quitar la palabra clave). La plantilla no cambia."""
        f = self.dir_usuarios / uid / "meta.json"
        if not re.fullmatch(CFG.ID_PATRON, uid) or not f.exists():
            raise ValueError("Usuario inexistente")
        f.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        restringir_permisos(f)

    def eliminar(self, uid):
        """Borra la plantilla, los metadatos y las fotos (si las hubiera) del usuario."""
        d = self.dir_usuarios / uid
        if not re.fullmatch(CFG.ID_PATRON, uid) or not d.exists():
            return False
        shutil.rmtree(d)
        self._cache.pop(uid, None)
        return True


def ahora():
    return time.strftime("%Y-%m-%d %H:%M:%S")
