"""Servicio de verificación: usa el paquete del modelo de la tarea 2.2 como biblioteca (src.pipeline.Verifier)
y la detección MTCNN de la tarea 2.6 (src.video.FaceCropper, margen 0). No modifica el modelo, las plantillas
ni el umbral; las plantillas de los usuarios de la demostración se añaden en memoria desde la carpeta privada."""
import threading
import time

import cv2
import numpy as np
import torch

from src.pipeline import Verifier
from src.video import FaceCropper

from . import config as CFG
from . import decision as DEC


class ServicioVerificacion:
    def __init__(self, paquete=CFG.PAQUETE_MODELO, device=None, almacen=None):
        self.device = device or CFG.device()
        t0 = time.perf_counter()
        self.v = Verifier(paquete, device=self.device)
        if abs(self.v.threshold - CFG.UMBRAL_OFICIAL) > 1e-9 or self.v.cfg.get("umbral_estado") != "propuesto en validación":
            raise RuntimeError(f"El umbral del paquete ({self.v.threshold}) no es el oficial {CFG.UMBRAL_OFICIAL}")
        self.cropper = FaceCropper(self.device)            # MTCNN, mismo recorte que la tarea 2.6
        self.almacen = almacen                             # plantillas de usuarios de la demo (tarea 3.3)
        self.lock = threading.Lock()                       # una inferencia a la vez
        self.segundos_carga = time.perf_counter() - t0

    # ------------------------------------------------------------ usuarios
    def usuarios(self):
        """Lista de (id, grupo). Grupo 'demo' = registrados por el administrador; 'dataset' = 24 del conjunto."""
        demo = self.almacen.usuarios() if self.almacen else []
        return [(u, "demo") for u in demo] + [(u, "dataset") for u in self.v.users]

    def _plantilla(self, usuario):
        if self.almacen and usuario in self.almacen.usuarios():
            return torch.as_tensor(self.almacen.plantilla(usuario), device=self.v.T.device)
        if usuario in self.v.users:
            return self.v.T[self.v.users.index(usuario)]
        raise KeyError(usuario)

    # ------------------------------------------------------------ fotogramas
    def analizar(self, rgb):
        """Detecta el rostro y comprueba la calidad. Devuelve (estado, recorte 160x160 o None)."""
        d = self.analizar_detalle(rgb)
        return d["estado"], d["recorte"]

    def analizar_detalle(self, rgb):
        """Como analizar, pero devuelve también las cajas detectadas (para el modo explicación)."""
        alto, ancho = rgb.shape[:2]
        d = {"estado": "sin_rostro", "recorte": None, "caja": None, "otras": [], "ancho": ancho, "alto": alto}
        boxes, probs = self.cropper.m.detect(rgb)
        if boxes is None:
            return d
        probs = np.array([float(p) for p in probs])
        keep = probs >= CFG.PROB_ROSTRO_MIN
        if not keep.any():
            return d
        boxes, probs = boxes[keep], probs[keep]
        areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
        k = int(np.argmax(areas))
        d["caja"] = [round(float(v), 1) for v in boxes[k]]
        d["otras"] = [[round(float(v), 1) for v in b] for i, b in enumerate(boxes) if i != k]
        if DEC.hay_varios_rostros(list(probs), list(areas), CFG):
            d["estado"] = "varios_rostros"
            return d
        lado = float(min(boxes[k, 2] - boxes[k, 0], boxes[k, 3] - boxes[k, 1]))
        crop = self.cropper.m.extract(rgb, boxes[k][None, :], None)
        crop = crop.permute(1, 2, 0).clamp(0, 255).byte().cpu().numpy()
        gris = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
        d["estado"] = DEC.clasificar_calidad(cv2.Laplacian(gris, cv2.CV_64F).var(), gris.mean(), lado, CFG)
        if d["estado"] == "valido":
            d["recorte"] = crop
        return d

    def embeddings(self, crops):
        """Embeddings L2-normalizados (N,512) de recortes 160x160 RGB uint8.

        Sin la optimización JIT de TorchScript: en GPU recompila la red cada vez que cambia el tamaño del lote
        (3, 4 o 5 rostros válidos), con 13-23 s por recompilación. Los embeddings son idénticos (diferencia 0)."""
        with self.lock, torch.no_grad(), torch.jit.optimized_execution(False):
            return self.v.embed(np.stack(crops))

    def verificar(self, usuario, fotogramas_rgb, explicar=False):
        """Verificación 1 a 1 de una ráfaga. Las imágenes solo existen en memoria durante la llamada.
        explicar=True añade r["explicacion"] (cajas, puntuación por fotograma, capas de la CNN) para la exposición."""
        t0 = time.perf_counter()
        plantilla = self._plantilla(usuario)
        with self.lock:
            det = [self.analizar_detalle(f) for f in fotogramas_rgb]
        analisis = [(d["estado"], d["recorte"]) for d in det]
        estados = [e for e, _ in analisis]
        crops = [c for _, c in analisis if c is not None]
        punt = [None] * len(estados)
        if crops:
            s = (self.embeddings(crops) @ plantilla).cpu().numpy().tolist()
            it = iter(s)
            punt = [next(it) if e == "valido" else None for e in estados]
        r = DEC.decidir(estados, punt, self.v.threshold, CFG.MIN_VOTOS, CFG.MIN_VALIDOS)
        r["estados"] = estados
        r["segundos_servidor"] = time.perf_counter() - t0
        if explicar:
            fot = [{"estado": d["estado"], "caja": d["caja"], "otras": d["otras"], "ancho": d["ancho"], "alto": d["alto"],
                    "puntuacion": None if p is None else round(p, 4), "voto": p is not None and p >= self.v.threshold}
                   for d, p in zip(det, punt)]
            r["explicacion"] = self._explicacion("A", fot, crops, punt, usuario=usuario)
        return r

    # ------------------------------------------------------------ modo B (1:N)
    def usuarios_app(self):
        """Usuarios registrados en la app (los únicos candidatos del modo B; nunca las 24 del dataset)."""
        return self.almacen.usuarios() if self.almacen else []

    def identificar(self, fotogramas_rgb, explicar=False):
        """Identificación 1:N contra las plantillas de los usuarios de la app. Imágenes solo en memoria."""
        t0 = time.perf_counter()
        usuarios = self.usuarios_app()
        if not usuarios:
            raise LookupError("No hay usuarios registrados en la aplicación.")
        T = torch.as_tensor(np.stack([self.almacen.plantilla(u) for u in usuarios]), device=self.v.T.device)
        with self.lock:
            det = [self.analizar_detalle(f) for f in fotogramas_rgb]
        analisis = [(d["estado"], d["recorte"]) for d in det]
        estados = [e for e, _ in analisis]
        crops = [c for _, c in analisis if c is not None]
        punt = [None] * len(estados)
        if crops:
            S = (self.embeddings(crops) @ T.T).cpu().numpy().tolist()
            it = iter(S)
            punt = [next(it) if e == "valido" else None for e in estados]
        r = DEC.identificar(estados, punt, usuarios, self.v.threshold, CFG.MARGEN_1N, CFG.MIN_VOTOS, CFG.MIN_VALIDOS)
        r["estados"] = estados
        r["segundos_servidor"] = time.perf_counter() - t0
        if explicar:
            fot = []
            for d, p in zip(det, punt):
                f = {"estado": d["estado"], "caja": d["caja"], "otras": d["otras"], "ancho": d["ancho"], "alto": d["alto"],
                     "candidatos": [], "voto": None, "razon": None}
                if p is not None:
                    orden = sorted(range(len(usuarios)), key=lambda i: p[i], reverse=True)
                    f["candidatos"] = [{"usuario": usuarios[i], "puntuacion": round(p[i], 4)} for i in orden[:3]]
                    segundo = p[orden[1]] if len(orden) > 1 else float("-inf")
                    if p[orden[0]] < self.v.threshold:
                        f["razon"] = "el mejor candidato no llega al umbral"
                    elif p[orden[0]] - segundo < CFG.MARGEN_1N:
                        f["razon"] = "el mejor y el segundo están demasiado cerca (margen)"
                    else:
                        f["voto"] = usuarios[orden[0]]
                fot.append(f)
            r["explicacion"] = self._explicacion("B", fot, crops, punt)
        return r

    # ------------------------------------------------------------ modo explicación
    def _explicacion(self, modo, fotogramas, crops, punt, usuario=None):
        """Camino de la decisión para la exposición: cajas y puntuaciones por fotograma y, para un rostro, las
        capas de la CNN y el vector de 512. Usa el fotograma válido de mayor puntuación."""
        from .explicacion import explicar_rostro
        e = {"modo": modo, "umbral": self.v.threshold, "margen": CFG.MARGEN_1N if modo == "B" else None,
             "votos_necesarios": CFG.MIN_VOTOS, "fotogramas": fotogramas, "usuario": usuario, "rostro": None}
        if crops:
            indices = [i for i, p in enumerate(punt) if p is not None]
            valores = [max(punt[i]) if isinstance(punt[i], list) else punt[i] for i in indices]
            k = int(np.argmax(valores))
            with self.lock:
                e["rostro"] = explicar_rostro(self.v, crops[k])
            e["rostro"]["fotograma"] = indices[k] + 1
        return e
