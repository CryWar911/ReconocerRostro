"""Metricas de la tarea 2.4 en un punto de operacion (umbral fijo). Definiciones en docs/sprint2/06_metricas.md.

Convencion: puntuacion alta = mas parecido; se ACEPTA si puntuacion >= umbral.
"""
import numpy as np
from scipy.stats import beta

from . import metrics as MT
from . import verification as V


def clopper_pearson(k, n, alpha=0.05):
    """Intervalo exacto (binomial) al 95 % para una proporcion k/n."""
    if n == 0:
        return (np.nan, np.nan)
    lo = 0.0 if k == 0 else beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alpha / 2, k + 1, n - k)
    return float(lo), float(hi)


def operating_point(gen, imp, thr):
    """Matriz de confusion y metricas en el umbral `thr`.

    TA genuina aceptada | FR genuina rechazada | FA impostora aceptada | TR impostora rechazada
    """
    gen, imp = np.asarray(gen), np.asarray(imp)
    TA, FR = int((gen >= thr).sum()), int((gen < thr).sum())
    FA, TR = int((imp >= thr).sum()), int((imp < thr).sum())
    nG, nI = len(gen), len(imp)
    far, frr = FA / nI, FR / nG
    return {"umbral": float(thr), "n_genuinas": nG, "n_impostoras": nI,
            "proporcion_genuinas": nG / (nG + nI), "razon_impostoras_por_genuina": nI / nG,
            "TA": TA, "FR": FR, "FA": FA, "TR": TR,
            "FAR": far, "FAR_IC95": clopper_pearson(FA, nI), "FRR": frr, "FRR_IC95": clopper_pearson(FR, nG),
            "exactitud_balanceada": ((1 - far) + (1 - frr)) / 2,
            "exactitud_simple": (TA + TR) / (nG + nI)}


def descriptive(gen, imp):
    """ROC/EER/AUC (solo descriptivos; no se usan para elegir umbral en prueba)."""
    e, t = MT.eer(gen, imp)
    return {"EER": e, "umbral_EER_descriptivo": t, "AUC": MT.auc(gen, imp),
            "genuina_min": float(np.min(gen)), "impostora_max": float(np.max(imp))}


def evaluate(S, probe_persons, probe_roles, registered, thresholds):
    """Evalua una matriz de puntuaciones S (n_imagenes x n_registradas).

    thresholds: dict nombre -> umbral. Devuelve (filas, sc) donde filas es una lista de dicts
    por (umbral, tipo de impostora) y sc el desglose de comparaciones de V.split_scores.
    """
    sc = V.split_scores(S, probe_persons, probe_roles, registered)
    sets = {"externas": sc["impostoras"], "internas": sc["internas"],
            "todas (ext+int)": np.r_[sc["impostoras"], sc["internas"]]}
    rows = []
    for tname, t in thresholds.items():
        for iname, imp in sets.items():
            r = operating_point(sc["genuinas"], imp, t)
            r.update(descriptive(sc["genuinas"], imp))
            r.update({"punto_operacion": tname, "impostoras": iname})
            rows.append(r)
    return rows, sc


def check_objectives(r, objectives, t_verif_s=None):
    """Compara el punto de operacion r (dict de operating_point) con los objetivos.
    objectives: dict con FAR_max, FRR_max, exactitud_balanceada_min, tiempo_max_s."""
    out = {"FAR": (r["FAR"], "<=", objectives["FAR_max"], r["FAR"] <= objectives["FAR_max"]),
           "FRR": (r["FRR"], "<=", objectives["FRR_max"], r["FRR"] <= objectives["FRR_max"]),
           "exactitud_balanceada": (r["exactitud_balanceada"], ">=", objectives["exactitud_balanceada_min"],
                                    r["exactitud_balanceada"] >= objectives["exactitud_balanceada_min"])}
    if t_verif_s is not None:
        out["tiempo_verificacion_s"] = (t_verif_s, "<=", objectives["tiempo_max_s"], t_verif_s <= objectives["tiempo_max_s"])
    return out


def group_breakdown(sc, probe_persons, registered, thr, registered_focus, impostor_focus):
    """Desglose por grupo en el umbral thr.

    - genuinas de `registered_focus` (p. ej. Marmik) frente a las demas registradas
    - impostoras externas de `impostor_focus` (p. ej. Kashyap) frente a las demas impostoras externas
    - `registered_focus` como impostora interna (contra las otras plantillas) frente al resto de internas
    """
    gp, ip, np_ = sc["genuinas_pares"], sc["impostoras_pares"], sc["internas_pares"]
    pg, pi, pn = probe_persons[gp[:, 0]], probe_persons[ip[:, 0]], probe_persons[np_[:, 0]]
    groups = {
        f"genuinas {registered_focus}": sc["genuinas"][pg == registered_focus],
        "genuinas demás registradas": sc["genuinas"][pg != registered_focus],
        f"impostoras externas {impostor_focus}": sc["impostoras"][pi == impostor_focus],
        "impostoras externas demás": sc["impostoras"][pi != impostor_focus],
        f"internas: {registered_focus} se hace pasar por otro": sc["internas"][pn == registered_focus],
        "internas: demás registradas": sc["internas"][pn != registered_focus],
    }
    rows = []
    for name, s in groups.items():
        genuine = name.startswith("genuinas")
        k = int((s < thr).sum()) if genuine else int((s >= thr).sum())
        rows.append({"grupo": name, "metrica": "FRR" if genuine else "FAR", "errores": k, "n": len(s),
                     "tasa": k / len(s) if len(s) else np.nan, "IC95": clopper_pearson(k, len(s)),
                     "puntuacion_min": float(s.min()) if len(s) else np.nan,
                     "puntuacion_mediana": float(np.median(s)) if len(s) else np.nan,
                     "puntuacion_max": float(s.max()) if len(s) else np.nan})
    return rows
