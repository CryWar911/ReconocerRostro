"""Carga del dataset, deteccion de casi duplicados, division y preprocesado.

Fuente unica: Faces/Faces (recortes 160x160 ya hechos). No se usa Original Images
porque contiene las mismas fotos sin recortar (usarlas filtraria datos entre conjuntos).
"""
import hashlib
import random

import cv2
import numpy as np
import pandas as pd

from . import config as C


# ---------------------------------------------------------------- indice
def load_index():
    """DataFrame con filename, person (desde Dataset.csv) y ruta a Faces."""
    df = pd.read_csv(C.CSV_PATH).rename(columns={"id": "filename", "label": "person"})
    df["path"] = df["filename"].map(lambda f: str(C.FACES_DIR / f))
    return df.sort_values("filename").reset_index(drop=True)


def read_rgb(path):
    """Lee una imagen como RGB uint8 (cv2 lee BGR)."""
    img = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if img is None:
        raise IOError(f"No se pudo leer {path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


# ---------------------------------------------------------- duplicados
def md5_of(path):
    with open(path, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()


def _small_vec(img_rgb, size=32):
    v = cv2.resize(img_rgb, (size, size), interpolation=cv2.INTER_AREA).astype(np.float32).ravel()
    v -= v.mean()
    return v / (np.linalg.norm(v) + 1e-8)


def pixel_similarity(paths):
    """Matriz de correlacion de pixeles (32x32 color) considerando tambien el espejo horizontal."""
    imgs = [read_rgb(p) for p in paths]
    X = np.stack([_small_vec(im) for im in imgs])
    Xf = np.stack([_small_vec(im[:, ::-1]) for im in imgs])
    return np.maximum(X @ X.T, X @ Xf.T)


def group_near_duplicates(df, threshold=C.DUP_CORR_THRESHOLD):
    """Asigna group_id: misma foto (MD5) o casi identica (corr >= threshold) de la misma persona.

    Union-find sobre pares de la MISMA persona. Devuelve (df con group_id, DataFrame de pares).
    """
    df = df.copy()
    parent = list(range(len(df)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    S = pixel_similarity(df["path"].tolist())
    md5 = df["path"].map(md5_of).to_numpy()
    persons = df["person"].to_numpy()
    pairs = []
    n = len(df)
    for i in range(n):
        for j in range(i + 1, n):
            if persons[i] != persons[j]:
                continue
            exact = md5[i] == md5[j]
            if exact or S[i, j] >= threshold:
                pairs.append((df.at[i, "filename"], df.at[j, "filename"], persons[i], float(S[i, j]), bool(exact)))
                parent[find(i)] = find(j)
    roots = [find(i) for i in range(n)]
    remap = {r: k for k, r in enumerate(dict.fromkeys(roots))}
    df["group_id"] = [remap[r] for r in roots]
    pairs = pd.DataFrame(pairs, columns=["file_a", "file_b", "person", "corr", "md5_identico"])
    return df, pairs, S


# ---------------------------------------------------------- division
def assign_roles(persons, seed=C.SEED):
    """Reparto de identidades: registradas / impostora_val / impostora_test (por identidad).

    Sorteo estratificado por genero aproximado (C.GENDER_BY_NAME) con las cuotas de
    C.IMPOSTOR_QUOTA. Las identidades forzadas cuentan dentro de la cuota de su genero.
    """
    persons = sorted(set(persons))
    gender = C.GENDER_BY_NAME
    roles = {p: "registrada" for p in persons}
    for p in C.FORCED_IMPOSTOR_TEST:
        roles[p] = "impostora_test"
    rng = random.Random(seed)
    for g in ["F", "M"]:  # orden fijo para que el sorteo sea reproducible
        free = [p for p in persons if gender[p] == g
                and p not in C.FORCED_REGISTERED + C.FORCED_IMPOSTOR_TEST]
        rng.shuffle(free)
        for split in ["val", "test"]:
            forced = sum(1 for p in C.FORCED_IMPOSTOR_TEST if gender[p] == g) if split == "test" else 0
            n = C.IMPOSTOR_QUOTA[split][g] - forced
            for p in free[:n]:
                roles[p] = f"impostora_{split}"
            free = free[n:]
    return roles


def split_groups(group_sizes, fractions=C.SPLIT_FRACTIONS, seed=C.SEED):
    """Reparte grupos enteros entre train/val/test acercandose a las fracciones por n de imagenes.

    group_sizes: dict group_id -> n imagenes. Orden aleatorio (semilla) y cada grupo va al
    conjunto con mayor deficit relativo respecto a su objetivo.
    """
    gids = sorted(group_sizes)
    random.Random(seed).shuffle(gids)
    total = sum(group_sizes.values())
    target = {k: f * total for k, f in fractions.items()}
    count = {k: 0 for k in fractions}
    out = {}
    for g in gids:
        k = max(fractions, key=lambda s: (target[s] - count[s]) / target[s])
        out[g] = k
        count[k] += group_sizes[g]
    return out


def make_splits(df, seed=C.SEED):
    """Columnas role y split. Registradas: 70/15/15 por persona y por grupos.
    Impostoras: todas sus imagenes en su conjunto (val o test); nunca en train."""
    df = df.copy()
    roles = assign_roles(df["person"], seed)
    df["role"] = df["person"].map(roles)
    df["split"] = None
    for person, sub in df[df["role"] == "registrada"].groupby("person"):
        sizes = sub.groupby("group_id").size().to_dict()
        # semilla distinta (pero fija) por persona para no repetir el mismo patron
        per_seed = seed + sum(ord(c) for c in person)
        g2s = split_groups(sizes, seed=per_seed)
        df.loc[sub.index, "split"] = sub["group_id"].map(g2s)
    df.loc[df["role"] == "impostora_val", "split"] = "val"
    df.loc[df["role"] == "impostora_test", "split"] = "test"
    return df


def check_splits(df):
    """Comprobaciones de integridad; lanza AssertionError si algo falla."""
    assert df["filename"].is_unique, "nombres repetidos"
    g = df.groupby("group_id")["split"].nunique()
    assert (g == 1).all(), "un grupo de casi duplicados cae en varios conjuntos"
    assert not ((df["role"] != "registrada") & (df["split"] == "train")).any(), "impostor en train"
    imp_v = set(df.loc[df.role == "impostora_val", "person"])
    imp_t = set(df.loc[df.role == "impostora_test", "person"])
    assert not (imp_v & imp_t), "identidad impostora en val y test"
    gen = df.groupby("person")["role"].first().rename("role").to_frame()
    gen["g"] = gen.index.map(C.GENDER_BY_NAME)
    q = gen.groupby(["role", "g"]).size()
    for split, quota in C.IMPOSTOR_QUOTA.items():
        for g, n in quota.items():
            assert q.get((f"impostora_{split}", g), 0) == n, f"cuota de genero incumplida: {split} {g}"
    assert gen.loc[gen.role == "impostora_val", "g"].nunique() == 2, "impostoras de val de un solo genero"
    assert set(C.FORCED_REGISTERED) <= set(gen.index[gen.role == "registrada"])
    assert set(C.FORCED_IMPOSTOR_TEST) <= set(gen.index[gen.role == "impostora_test"])
    md5 = df["path"].map(md5_of)
    assert (df.assign(m=md5).groupby("m")["split"].nunique() == 1).all(), "imagen identica en dos conjuntos"
    return True


# ---------------------------------------------------------- preprocesado
def load_images(paths, size=C.IMG_SIZE):
    """Array uint8 (N, size, size, 3) RGB. Faces ya es 160x160: solo reescala si hiciera falta."""
    out = np.empty((len(paths), size, size, 3), np.uint8)
    for k, p in enumerate(paths):
        im = read_rgb(p)
        if im.shape[:2] != (size, size):
            im = cv2.resize(im, (size, size), interpolation=cv2.INTER_AREA)
        out[k] = im
    return out


def standardize(x_uint8):
    """Normalizacion de FaceNet (facenet-pytorch): (x - 127.5) / 128 -> aprox. [-1, 1].
    Entrada (N,H,W,3) uint8; salida float32 (N,3,H,W) para PyTorch."""
    x = (x_uint8.astype(np.float32) - 127.5) / 128.0
    return np.ascontiguousarray(x.transpose(0, 3, 1, 2))


def load_split_table():
    return pd.read_csv(C.DATA_PROCESSED / "splits.csv")
