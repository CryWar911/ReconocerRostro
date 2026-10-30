"""Modo explicación: muestra el camino que sigue la máquina para decidir (para la exposición en clase).

Recorre FaceNet (InceptionResnetV1 del paquete TorchScript) capa por capa SIN modificarla: la cadena de capas reproduce
exactamente el embedding de la red completa (diferencia 0,0 comprobada). Devuelve imágenes pequeñas generadas en memoria
(recorte, mapas de activación, mapa aproximado de "dónde mira la red") y el vector de 512 valores. No se guarda nada.

Solo está disponible en la instancia local (nunca en la pública del túnel), porque muestra puntuaciones.
"""
import base64

import cv2
import numpy as np
import torch
import torch.nn.functional as F

from src.models import to_tensor

ORDEN = ["conv2d_1a", "conv2d_2a", "conv2d_2b", "maxpool_3a", "conv2d_3b", "conv2d_4a", "conv2d_4b",
         "repeat_1", "mixed_6a", "repeat_2", "mixed_7a", "repeat_3", "block8", "avgpool_1a"]
CAPAS = [
    ("conv2d_1a", "Capa 1 (primera convolución)", "Detecta bordes, contrastes y cambios de luz."),
    ("conv2d_4b", "Capa 7 (convolución)", "Combina bordes en texturas y formas: contornos de ojos, cejas, nariz y boca."),
    ("repeat_1", "Bloques Inception-ResNet A (×5)", "Reconoce partes del rostro y cómo se relacionan entre sí."),
    ("repeat_2", "Bloques Inception-ResNet B (×10)", "Combinaciones más abstractas: proporciones y rasgos característicos."),
    ("block8", "Última capa convolucional", "Rasgos de identidad muy abstractos; de aquí sale el vector de 512 números."),
]


def _data_url(img_rgb, calidad=85):
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, calidad])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


def _color(mapa, lado):
    m = mapa - mapa.min()
    m = (255 * m / (m.max() + 1e-8)).astype(np.uint8)
    interp = cv2.INTER_NEAREST if mapa.shape[0] < 8 else cv2.INTER_CUBIC
    m = cv2.resize(m, (lado, lado), interpolation=interp)
    return cv2.cvtColor(cv2.applyColorMap(m, cv2.COLORMAP_VIRIDIS), cv2.COLOR_BGR2RGB)


def mosaico(act, n=8, lado=72, columnas=4, sep=3):
    """Los n canales con mayor activación media, cada uno coloreado (viridis), en una cuadrícula."""
    a = act[0].float().cpu().numpy()                       # (C, H, W)
    top = np.argsort(-a.mean(axis=(1, 2)))[:n]
    filas = int(np.ceil(n / columnas))
    out = np.full((filas * lado + (filas - 1) * sep, columnas * lado + (columnas - 1) * sep, 3), 255, np.uint8)
    for k, c in enumerate(top):
        y, x = (k // columnas) * (lado + sep), (k % columnas) * (lado + sep)
        out[y:y + lado, x:x + lado] = _color(a[c], lado)
    return out


def atencion(crop, act):
    """Aproximación de "dónde mira la red": activación media de una capa intermedia superpuesta al recorte.
    No es Grad-CAM; solo indica qué zonas activan más esa capa."""
    m = act[0].abs().mean(0).float().cpu().numpy()
    calor = _color(m, crop.shape[0])
    return (0.55 * crop + 0.45 * calor).astype(np.uint8)


@torch.no_grad()
def explicar_rostro(verificador, crop):
    """Recorre la red con un recorte 160x160 y devuelve las capas, el mapa de atención y el embedding (512)."""
    net = verificador.net.m
    x = to_tensor(crop[None], verificador.cfg["normalizacion"], verificador.T.device)
    salidas, h = {}, x
    with torch.jit.optimized_execution(False):
        for nombre in ORDEN:
            h = getattr(net, nombre)(h)
            salidas[nombre] = h
        h = net.last_bn(net.last_linear(h.view(h.shape[0], -1)))
        emb = F.normalize(h, dim=1)[0].cpu().numpy()
    capas = []
    for nombre, titulo, texto in CAPAS:
        a = salidas[nombre]
        capas.append({"nombre": nombre, "titulo": titulo, "texto": texto,
                      "forma": f"{a.shape[1]} mapas de {a.shape[2]}×{a.shape[3]}",
                      "mosaico": _data_url(mosaico(a))})
    return {"recorte": _data_url(crop, 90), "atencion": _data_url(atencion(crop, salidas["repeat_1"]), 90),
            "capas": capas, "embedding": [round(float(v), 4) for v in emb]}
