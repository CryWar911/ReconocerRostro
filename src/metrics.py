"""Metricas de verificacion 1 a 1 (puntuacion alta = mas parecido a la plantilla)."""
import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve


def far_frr(gen, imp, thr):
    """FAR = impostores aceptados (score >= thr); FRR = genuinos rechazados (score < thr)."""
    gen, imp = np.asarray(gen), np.asarray(imp)
    return float((imp >= thr).mean()), float((gen < thr).mean())


def eer(gen, imp):
    """EER y su umbral. Se recorren los umbrales de la curva ROC y se toma el punto
    donde |FAR - FRR| es minimo; EER = media de FAR y FRR en ese punto."""
    y = np.r_[np.ones(len(gen)), np.zeros(len(imp))]
    s = np.r_[gen, imp]
    fpr, tpr, thr = roc_curve(y, s)
    fnr = 1 - tpr
    k = int(np.nanargmin(np.abs(fpr - fnr)))
    return float((fpr[k] + fnr[k]) / 2), float(thr[k])


def auc(gen, imp):
    y = np.r_[np.ones(len(gen)), np.zeros(len(imp))]
    return float(roc_auc_score(y, np.r_[gen, imp]))


def roc(gen, imp):
    y = np.r_[np.ones(len(gen)), np.zeros(len(imp))]
    fpr, tpr, thr = roc_curve(y, np.r_[gen, imp])
    return fpr, tpr, thr


def summary(gen, imp, thr=None):
    """EER, AUC y FAR/FRR en el umbral dado (por defecto el del EER)."""
    e, t_eer = eer(gen, imp)
    t = t_eer if thr is None else thr
    far, frr = far_frr(gen, imp, t)
    return {"EER": e, "AUC": auc(gen, imp), "umbral": t, "FAR": far, "FRR": frr,
            "n_genuinas": len(gen), "n_impostoras": len(imp)}


def bootstrap_eer(gen, imp, n=1000, seed=42):
    """Intervalo del 95 % del EER remuestreando comparaciones genuinas e impostoras por separado."""
    rng = np.random.default_rng(seed)
    gen, imp = np.asarray(gen), np.asarray(imp)
    vals = [eer(rng.choice(gen, len(gen)), rng.choice(imp, len(imp)))[0] for _ in range(n)]
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))
