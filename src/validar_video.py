"""Valida el video y el CSV de anotaciones ANTES de la evaluación de la tarea 2.6. No carga el modelo ni calcula métricas.

Uso (desde la raíz del proyecto):
    .venv/Scripts/python -m src.validar_video --video D:/privado/video.mp4 --anotaciones D:/privado/anotaciones.csv --almacen-app %USERPROFILE%/FaceID_privado

Comprueba:
  - el video se abre; resolución, fps, número de fotogramas y duración (con --contar se cuentan decodificando, sin modelo);
  - el CSV tiene las columnas inicio_s, fin_s, identidad (condicion es opcional), con números válidos y fin > inicio;
  - los tramos no se solapan y no se salen del video;
  - cada identidad es un seudónimo registrado en el almacén de la app (leído en solo lectura) o "no registrado [etiqueta]";
  - cuántas ventanas de decisión dará cada tramo con las reglas de la tarea 2.6 (1 de cada 3 fotogramas, ventanas de 5).
Errores -> código de salida 1. Avisos -> se muestran pero no impiden la evaluación.
"""
import argparse
import sys
from pathlib import Path

import cv2
import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src import config as C  # noqa: E402
from src import video as VID  # noqa: E402

NO_REG = VID.NO_REG
MIN_FPS, MIN_ANCHO, MIN_ALTO = 15, 640, 480
MIN_VENTANAS_TRAMO = 10          # aviso si un tramo da menos ventanas de decisión


def info_video(path, contar=False):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    ancho, alto = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    legible = cap.read()[0]
    if contar:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        n = 0
        while cap.grab():
            n += 1
    cap.release()
    return {"fps": fps, "fotogramas": n, "ancho": ancho, "alto": alto, "duracion_s": n / fps if fps else 0.0, "legible": legible}


def validar(video, anotaciones, almacen_app=None, contar=False):
    errores, avisos = [], []
    try:
        video, anotaciones = VID.check_private_path(video), VID.check_private_path(anotaciones)
    except ValueError as e:
        return {"errores": [str(e)], "avisos": [], "video": None, "tramos": None}

    # ------------------------------------------------------------ video
    v = info_video(video, contar) if Path(video).exists() else None
    if v is None:
        errores.append(f"No se puede abrir el video: {video}")
    else:
        if not v["legible"]:
            errores.append("El video se abre pero no se puede leer ningún fotograma (códec no soportado).")
        if v["fps"] <= 0 or v["fotogramas"] <= 0:
            errores.append("El video no informa fps o número de fotogramas; pruebe con --contar.")
        if 0 < v["fps"] < MIN_FPS:
            avisos.append(f"fps bajos ({v['fps']:.1f}); se recomiendan 30.")
        if v["ancho"] < MIN_ANCHO or v["alto"] < MIN_ALTO:
            avisos.append(f"Resolución baja ({v['ancho']}x{v['alto']}); se recomienda 1280x720.")

    # ------------------------------------------------------------ CSV
    if not Path(anotaciones).exists():
        errores.append(f"No existe el CSV de anotaciones: {anotaciones}")
        return {"errores": errores, "avisos": avisos, "video": v, "tramos": None}
    a = pd.read_csv(anotaciones, dtype={"identidad": str})
    faltan = {"inicio_s", "fin_s", "identidad"} - set(a.columns)
    if faltan:
        errores.append(f"Faltan columnas en el CSV: {sorted(faltan)}")
        return {"errores": errores, "avisos": avisos, "video": v, "tramos": None}
    extra = set(a.columns) - {"inicio_s", "fin_s", "identidad", "condicion"}
    if extra:
        avisos.append(f"Columnas no usadas por la evaluación: {sorted(extra)}")
    a["fila"] = range(2, len(a) + 2)                       # número de fila en el archivo (1 = cabecera)
    for col in ("inicio_s", "fin_s"):
        a[col] = pd.to_numeric(a[col], errors="coerce")
    for _, r in a[a.inicio_s.isna() | a.fin_s.isna()].iterrows():
        errores.append(f"Fila {r.fila}: inicio_s o fin_s no es un número.")
    a = a.dropna(subset=["inicio_s", "fin_s"]).copy()
    a["identidad"] = a["identidad"].fillna("").astype(str).str.strip()
    for _, r in a.iterrows():
        if r.inicio_s < 0:
            errores.append(f"Fila {r.fila}: inicio_s negativo ({r.inicio_s}).")
        if r.fin_s <= r.inicio_s:
            errores.append(f"Fila {r.fila}: fin_s ({r.fin_s}) no es mayor que inicio_s ({r.inicio_s}).")
        if not r.identidad:
            errores.append(f"Fila {r.fila}: identidad vacía.")
        if v and v["duracion_s"] > 0 and r.fin_s > v["duracion_s"] + 1e-6:
            errores.append(f"Fila {r.fila}: el tramo termina en {r.fin_s} s pero el video dura {v['duracion_s']:.2f} s.")
    s = a.sort_values("inicio_s")
    for (_, x), (_, y) in zip(s.iloc[:-1].iterrows(), s.iloc[1:].iterrows()):
        if y.inicio_s < x.fin_s:
            errores.append(f"Filas {x.fila} y {y.fila}: los tramos se solapan ({x.inicio_s}-{x.fin_s} y {y.inicio_s}-{y.fin_s}).")

    # ------------------------------------------------------------ identidades
    registrados = None
    if almacen_app:
        try:
            registrados, _ = VID.cargar_plantillas_app(VID.check_private_path(almacen_app))
        except ValueError as e:
            errores.append(str(e))
    else:
        avisos.append("Sin --almacen-app: no se comprueba que los seudónimos estén registrados en la app.")
    es_noreg = a.identidad.str.lower().str.startswith(NO_REG)
    if registrados is not None:
        if not registrados:
            errores.append("El almacén de la app no tiene ningún usuario registrado.")
        for _, r in a[~es_noreg].iterrows():
            if r.identidad and r.identidad not in registrados:
                errores.append(f"Fila {r.fila}: '{r.identidad}' no está registrado en la app ni es 'no registrado'.")
        sin_tramo = sorted(set(registrados) - set(a.loc[~es_noreg, "identidad"]))
        if sin_tramo:
            avisos.append(f"Usuarios registrados sin ningún tramo en el video: {sin_tramo}")
    if not es_noreg.any():
        avisos.append("No hay tramos de 'no registrado': no se medirán impostores externos.")
    if (~es_noreg).sum() == 0:
        errores.append("No hay tramos de voluntarios registrados: no se medirán intentos genuinos.")

    # ------------------------------------------------------------ ventanas de decisión por tramo (reglas de la 2.6)
    fps = v["fps"] if v and v["fps"] > 0 else 30.0
    a["duracion_s"] = a.fin_s - a.inicio_s
    a["fotogramas_procesados"] = (a.duracion_s * fps / C.VIDEO_CADA_N).astype(int)
    a["ventanas"] = a.fotogramas_procesados // C.VIDEO_VENTANA
    for _, r in a.iterrows():
        if r.ventanas == 0 and r.duracion_s > 0:
            errores.append(f"Fila {r.fila}: el tramo ({r.duracion_s:.1f} s) es demasiado corto para una sola ventana de decisión.")
        elif 0 < r.ventanas < MIN_VENTANAS_TRAMO:
            avisos.append(f"Fila {r.fila}: el tramo solo da {r.ventanas} ventanas; se recomiendan al menos {MIN_VENTANAS_TRAMO} (>= 5 s a 30 fps).")
    return {"errores": errores, "avisos": avisos, "video": v, "tramos": a}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", required=True)
    ap.add_argument("--anotaciones", required=True)
    ap.add_argument("--almacen-app", default=None, help="carpeta de datos de la app (FACEID_APP_DATA) para comprobar los seudónimos")
    ap.add_argument("--contar", action="store_true", help="contar los fotogramas decodificando el video (más lento, más exacto)")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")    # consola o tubería en cp1252: no fallar por un acento
    r = validar(a.video, a.anotaciones, a.almacen_app, a.contar)
    v = r["video"]
    print("VALIDACIÓN (sin modelo ni métricas)")
    if v:
        print(f"Video: {v['ancho']}x{v['alto']}, {v['fps']:.2f} fps, {v['fotogramas']} fotogramas, {v['duracion_s']:.2f} s")
    t = r["tramos"]
    if t is not None and len(t):
        cols = [c for c in ["fila", "inicio_s", "fin_s", "identidad", "condicion", "duracion_s", "ventanas"] if c in t.columns]
        with pd.option_context("display.width", 200, "display.max_colwidth", 40):
            print(t[cols].round(2).to_string(index=False))
        res = t.assign(tipo=t.identidad.str.lower().str.startswith(NO_REG).map({True: "no registrado", False: "registrado"}))
        print("Duración anotada por tipo (s):", res.groupby("tipo").duracion_s.sum().round(1).to_dict(),
              "| ventanas:", res.groupby("tipo").ventanas.sum().to_dict())
    for w in r["avisos"]:
        print("AVISO:", w)
    for e in r["errores"]:
        print("ERROR:", e)
    print("Resultado:", "VÁLIDO" if not r["errores"] else f"NO VÁLIDO ({len(r['errores'])} errores)")
    return 0 if not r["errores"] else 1


if __name__ == "__main__":
    sys.exit(main())
