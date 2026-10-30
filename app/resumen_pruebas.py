"""Resume por caso de prueba el registro del modo pruebas (tarea 3.4). Sin imágenes ni seudónimos.

Uso:
    .venv/Scripts/python -m app.resumen_pruebas                      # lee FACEID_APP_DATA (o la carpeta por defecto)
    .venv/Scripts/python -m app.resumen_pruebas --datos D:/privado/FaceID_privado --csv docs/sprint3/resumen_casos.csv

Entrada: registro_pruebas.csv (y tiempos_cliente.csv), escritos por la app con FACEID_MODO_PRUEBAS=1.
Salida: por caso, número de intentos, conteo por resultado, problemas más frecuentes por fotograma y tiempos
(mediana y p95 de captura en el navegador, servidor, petición y total). Los casos cuyo ID empieza por "ENSAYO"
se marcan como ensayo.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import config as CFG  # noqa: E402

RESULTADOS = ["permitido", "denegado", "no_concluyente", "no_identificado", "requiere_clave", "bloqueado", "pausa"]
TIEMPOS = ["segundos_captura", "segundos_servidor", "segundos_peticion", "segundos_total_cliente"]


def resumir(carpeta):
    carpeta = Path(carpeta)
    f = carpeta / "registro_pruebas.csv"
    if not f.exists():
        raise FileNotFoundError(f"No existe {f}. Ejecute la app con FACEID_MODO_PRUEBAS=1 y haga los casos.")
    d = pd.read_csv(f, dtype={"id_intento": str, "caso": str}).fillna({"caso": "(sin caso)", "estados": ""})
    ft = carpeta / "tiempos_cliente.csv"
    if ft.exists():
        d = d.merge(pd.read_csv(ft, dtype={"id_intento": str}), on="id_intento", how="left")
    else:
        d["segundos_total_cliente"] = float("nan")
    filas = []
    for caso, g in d.groupby("caso", sort=True):
        fila = {"caso": caso, "es_ensayo": str(caso).upper().startswith("ENSAYO"), "intentos": len(g),
                "primera_fecha": g.fecha_hora.min(), "ultima_fecha": g.fecha_hora.max()}
        for r in RESULTADOS:
            fila[r] = int((g.resultado == r).sum())
        problemas = Counter(e for s in g.estados for e in str(s).split() if e != "valido")
        fila["problemas_por_fotograma"] = "; ".join(f"{k}: {v}" for k, v in problemas.most_common())
        for t in TIEMPOS:
            x = pd.to_numeric(g[t], errors="coerce").dropna()
            fila[f"{t}_mediana"] = round(float(x.median()), 3) if len(x) else None
            fila[f"{t}_p95"] = round(float(x.quantile(0.95)), 3) if len(x) else None
        filas.append(fila)
    return pd.DataFrame(filas)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datos", default=str(CFG.DATA_DIR), help="carpeta de datos de la app (FACEID_APP_DATA)")
    ap.add_argument("--csv", default=None, help="guardar el resumen (solo agregados por caso) en este CSV")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    res = resumir(a.datos)
    with pd.option_context("display.width", 220, "display.max_columns", 40):
        print(res.to_string(index=False))
    if a.csv:
        res.to_csv(a.csv, index=False)
        print("Guardado:", a.csv)


if __name__ == "__main__":
    sys.exit(main())
