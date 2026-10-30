"""Verificacion sobre un video anotado. Imprime y guarda SOLO metricas agregadas.

Uso (desde la raiz del proyecto):
    .venv/Scripts/python -m src.video_verificacion --video D:/privado/video.mp4 --anotaciones D:/privado/anotaciones.csv --salida D:/privado/resultados

- Deteccion MTCNN en 1 de cada N fotogramas, recorte 160x160, embedding FaceNet VGGFace2 congelado.
- Umbral OFICIAL fijado en validacion (config.json del paquete, 0,5514); no se recalcula.
- Decision por ventana de W fotogramas procesados con votacion por mayoria.
- anotaciones.csv: columnas inicio_s, fin_s, identidad (id del voluntario o 'no registrado').
- Con --almacen-app <FACEID_APP_DATA> usa, en solo lectura, las plantillas registradas en la app web (mismo registro
  que la demostracion). Las reglas no cambian: umbral 0,5514, ventanas de 5 fotogramas con 3 de 5.
- --salida debe estar fuera del repositorio o en data/. Se guardan metricas agregadas; el detalle por
  fotograma (sin imagenes) solo si se pide con --detalle.
"""
import argparse
import json
import sys
from pathlib import Path

from . import config as C
from . import pipeline as P
from . import video as VID


def cargar_verificador(paquete, device, voluntarios=None, almacen_app=None):
    """Verificador con las 24 plantillas del dataset más las de los voluntarios, tomadas de UNA fuente:
    almacen_app (carpeta de datos de la app web, leída en solo lectura) o el archivo `voluntarios` del paquete."""
    if almacen_app is None:
        return P.Verifier(paquete, device=device, voluntarios=voluntarios)
    import torch
    v = P.Verifier(paquete, device=device)
    ids, T = VID.cargar_plantillas_app(VID.check_private_path(almacen_app))
    if set(ids) & set(v.users):
        raise ValueError("Un usuario del almacén de la app usa el nombre de una identidad del dataset")
    v.users = v.users + ids
    v.group = v.group + ["voluntario"] * len(ids)
    v.T = torch.cat([v.T, torch.as_tensor(T, device=v.T.device)])
    return v


def run(video, anotaciones, paquete=None, voluntarios=C.PLANTILLAS_VOLUNTARIOS, device="cuda",
        every_n=C.VIDEO_CADA_N, window=C.VIDEO_VENTANA, almacen_app=None):
    paquete = Path(paquete or C.MODELS_DIR / "verificador_facenet_vggface2")
    video, anotaciones = VID.check_private_path(video), VID.check_private_path(anotaciones)
    v = cargar_verificador(paquete, device, voluntarios, almacen_app)
    thr = v.threshold
    assert abs(thr - C.UMBRAL_OFICIAL) < 1e-9, f"El umbral del paquete ({thr}) no es el oficial fijado en el plan"
    ann = VID.read_annotations(anotaciones)
    unknown = set(ann.loc[ann.registrado, "identidad"]) - {u for u, g in zip(v.users, v.group) if g == "voluntario"}
    if unknown:
        raise ValueError(f"Identidades anotadas sin plantilla de voluntario: {sorted(unknown)}")
    frames, S, fps = VID.process_video(video, VID.FaceCropper(device), v, every_n, ann)
    comps = VID.evaluate_video(frames, S, v.users, v.group, ann, thr, window)
    met, sin = VID.summarize(comps, frames, ann)
    info = {"video_fps": fps, "fotogramas_procesados": len(frames), "cada_n": every_n, "ventana": window,
            "umbral": thr, "voluntarios": [u for u, g in zip(v.users, v.group) if g == "voluntario"],
            "segundos_por_fotograma_mediana": float(frames.segundos.median()) if len(frames) else None,
            "segundos_por_fotograma_p95": float(frames.segundos.quantile(0.95)) if len(frames) else None,
            "dispositivo": device}
    return info, met, sin, frames, comps


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", required=True)
    ap.add_argument("--anotaciones", required=True)
    ap.add_argument("--salida", required=True, help="carpeta de resultados (fuera del repositorio o en data/)")
    ap.add_argument("--paquete", default=None)
    ap.add_argument("--voluntarios", default=C.PLANTILLAS_VOLUNTARIOS)
    ap.add_argument("--almacen-app", default=None,
                    help="carpeta de datos de la app web (FACEID_APP_DATA): usa sus plantillas en solo lectura en lugar de --voluntarios")
    ap.add_argument("--dispositivo", default="cuda")
    ap.add_argument("--cada-n", type=int, default=C.VIDEO_CADA_N)
    ap.add_argument("--ventana", type=int, default=C.VIDEO_VENTANA)
    ap.add_argument("--detalle", action="store_true", help="guardar tambien puntuaciones por fotograma (sin imagenes)")
    a = ap.parse_args(argv)
    out = VID.check_private_path(a.salida)
    out.mkdir(parents=True, exist_ok=True)
    info, met, sin, frames, comps = run(a.video, a.anotaciones, a.paquete, a.voluntarios, a.dispositivo, a.cada_n, a.ventana,
                                        almacen_app=a.almacen_app)
    met.to_csv(out / "metricas_video.csv", index=False)
    sin.to_csv(out / "sin_rostro.csv", index=False)
    (out / "info.json").write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding="utf-8")
    if a.detalle:
        frames.to_csv(out / "detalle_fotogramas.csv", index=False)
    print(json.dumps(info, indent=1, ensure_ascii=False))
    print(met[met.persona == "todas"].to_string(index=False))
    print(sin.to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
