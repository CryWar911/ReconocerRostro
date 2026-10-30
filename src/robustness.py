"""Perturbaciones deterministas para pruebas de robustez (solo validacion).

Se aplican sobre el recorte 160x160 RGB uint8 (sin volver a detectar el rostro).
Cada perturbacion es una funcion img -> img; las aleatorias usan un rng con semilla fija.
"""
import cv2
import numpy as np


def brightness(f):
    return lambda im: np.clip(im.astype(np.float32) * f, 0, 255).astype(np.uint8)


def contrast(f):
    def _c(im):
        x = im.astype(np.float32)
        m = x.mean()
        return np.clip((x - m) * f + m, 0, 255).astype(np.uint8)
    return _c


def blur(sigma):
    return lambda im: cv2.GaussianBlur(im, (0, 0), sigma)


def jpeg(q):
    def _j(im):
        ok, buf = cv2.imencode(".jpg", cv2.cvtColor(im, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, q])
        return cv2.cvtColor(cv2.imdecode(buf, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    return _j


def rotate(deg):
    def _r(im):
        h, w = im.shape[:2]
        M = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1.0)
        return cv2.warpAffine(im, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    return _r


def occlude(region):
    """Rectangulo gris (128) sobre una zona fija del recorte alineado:
    'ojos' = banda horizontal 28-45 % de la altura (gafas de sol aprox.),
    'inferior' = tercio inferior (mascarilla/mano aprox.),
    'lateral' = mitad izquierda (oclusion lateral)."""
    def _o(im):
        im = im.copy()
        h, w = im.shape[:2]
        if region == "ojos":
            im[int(0.28 * h):int(0.45 * h), :] = 128
        elif region == "inferior":
            im[int(0.66 * h):, :] = 128
        elif region == "lateral":
            im[:, : w // 2] = 128
        else:
            raise ValueError(region)
        return im
    return _o


def random_patch(size=48, seed=42):
    """Cuadrado gris de size x size en posicion aleatoria (reproducible por indice de imagen)."""
    def _p(im, k=0):
        rng = np.random.default_rng(seed + k)
        im = im.copy()
        h, w = im.shape[:2]
        y, x = rng.integers(0, h - size), rng.integers(0, w - size)
        im[y:y + size, x:x + size] = 128
        return im
    return _p


PERTURBATIONS = {
    "limpia": lambda im: im,
    "brillo_x0.6": brightness(0.6), "brillo_x1.4": brightness(1.4),
    "contraste_x0.5": contrast(0.5), "contraste_x1.5": contrast(1.5),
    "desenfoque_s1": blur(1.0), "desenfoque_s2": blur(2.0), "desenfoque_s3": blur(3.0),
    "jpeg_q30": jpeg(30), "jpeg_q15": jpeg(15), "jpeg_q8": jpeg(8),
    "rotacion_+5": rotate(5), "rotacion_-10": rotate(-10), "rotacion_+15": rotate(15),
    "oclusion_ojos": occlude("ojos"), "oclusion_inferior": occlude("inferior"),
    "oclusion_lateral": occlude("lateral"), "oclusion_parche48": "parche",
}
FAMILY = {k: k.split("_")[0] for k in PERTURBATIONS}


def apply(name, X):
    """Aplica la perturbacion `name` a un array (N,160,160,3) uint8."""
    if PERTURBATIONS[name] == "parche":
        p = random_patch(48)
        return np.stack([p(im, k) for k, im in enumerate(X)])
    f = PERTURBATIONS[name]
    return np.stack([f(im) for im in X])
