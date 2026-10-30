"""Protocolo de verificacion 1 a 1.

Cada intento = (imagen de prueba, identidad que dice ser). La puntuacion compara la imagen
con la PLANTILLA de esa identidad, construida solo con sus fotos de entrenamiento.
Se trabaja con una matriz S (n_imagenes x n_registradas): S[i, p] = puntuacion de la
imagen i contra la plantilla p (mayor = mas parecido).
"""
import numpy as np


def templates(E_train, persons_train, registered):
    """Plantilla = media de los embeddings L2-normalizados de train, renormalizada."""
    T = np.stack([E_train[persons_train == p].mean(0) for p in registered])
    return T / np.linalg.norm(T, axis=1, keepdims=True)


def cosine_matrix(E_probe, T):
    return E_probe @ T.T


def strategy_matrix(E_probe, E_train, persons_train, registered, strategy, seed=42):
    """Puntuacion (n_probe, n_registradas) segun la estrategia de plantilla y la metrica.

    media_coseno       coseno contra la plantilla media renormalizada (la de la tarea 2.2)
    media_euclidea     -distancia euclidea a la plantilla media renormalizada (equivale al coseno)
    media_euclidea_sin_norm  -distancia euclidea a la media SIN renormalizar
    vecino_cercano     max coseno contra TODAS las fotos de train del usuario
    top3_media         media de los 3 cosenos mas altos contra las fotos de train
    kmeans3            max coseno contra 3 centroides k-means (renormalizados) por usuario
    """
    from sklearn.cluster import KMeans
    cols = []
    for p in registered:
        Ep = E_train[persons_train == p]
        if strategy in ("media_coseno", "media_euclidea"):
            t = Ep.mean(0)
            t = t / np.linalg.norm(t)
            cols.append(E_probe @ t if strategy == "media_coseno" else -np.linalg.norm(E_probe - t, axis=1))
        elif strategy == "media_euclidea_sin_norm":
            cols.append(-np.linalg.norm(E_probe - Ep.mean(0), axis=1))
        elif strategy == "vecino_cercano":
            cols.append((E_probe @ Ep.T).max(1))
        elif strategy == "top3_media":
            s = np.sort(E_probe @ Ep.T, axis=1)[:, -3:]
            cols.append(s.mean(1))
        elif strategy == "kmeans3":
            km = KMeans(n_clusters=min(3, len(Ep)), n_init=10, random_state=seed).fit(Ep)
            c = km.cluster_centers_ / np.linalg.norm(km.cluster_centers_, axis=1, keepdims=True)
            cols.append((E_probe @ c.T).max(1))
        else:
            raise ValueError(strategy)
    return np.stack(cols, axis=1)


def threshold_for_far(imp_scores, far_target):
    """Menor umbral t (de los valores observados) con FAR = mean(imp >= t) <= far_target.
    Con n impostoras se permiten floor(far_target * n) aceptaciones."""
    imp = np.sort(np.asarray(imp_scores))[::-1]
    k = int(np.floor(far_target * len(imp)))   # aceptaciones permitidas
    # t justo por encima de la (k+1)-esima puntuacion mas alta
    return float(np.nextafter(imp[k], np.inf)) if k < len(imp) else float(imp[-1])


def lbph_matrix(H_probe, H_train, persons_train, registered, chi2):
    """Puntuacion LBPH = -(distancia chi-cuadrado al vecino mas cercano de la identidad
    reclamada), que es la regla de decision del reconocedor LBPH de OpenCV."""
    D = chi2(H_probe, H_train)
    return np.stack([-D[:, persons_train == p].min(1) for p in registered], axis=1)


def split_scores(S, probe_persons, probe_roles, registered):
    """Separa la matriz S en comparaciones del protocolo.

    genuinas: imagen de registrada vs su propia plantilla
    impostoras: imagen de impostora (no registrada) vs TODAS las plantillas
    internas: imagen de registrada vs las plantillas de las OTRAS registradas (complementario)
    Devuelve dict de arrays y los indices (imagen, plantilla) de cada comparacion.
    """
    reg_idx = {p: k for k, p in enumerate(registered)}
    gen, imp, intl = [], [], []
    for i, (p, r) in enumerate(zip(probe_persons, probe_roles)):
        if r == "registrada":
            gen.append((i, reg_idx[p]))
            intl += [(i, k) for k in range(len(registered)) if k != reg_idx[p]]
        else:
            imp += [(i, k) for k in range(len(registered))]
    out = {}
    for name, pairs in [("genuinas", gen), ("impostoras", imp), ("internas", intl)]:
        pairs = np.array(pairs, dtype=int).reshape(-1, 2)
        out[name] = S[pairs[:, 0], pairs[:, 1]] if len(pairs) else np.array([])
        out[name + "_pares"] = pairs
    return out
