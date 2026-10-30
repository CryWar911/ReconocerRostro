"""Modelos para verificacion facial: FaceNet preentrenado, CNN propia, ResNet-18 por
transferencia (ImageNet) y linea base LBPH. Todos producen un vector por imagen; la
verificacion compara ese vector con la plantilla del usuario (ver src/verification.py)."""
import math
import time

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


def to_tensor(x_uint8, norm, device):
    """(N,H,W,3) uint8 RGB -> (N,3,H,W) float normalizado en `device`.
    norm='facenet': (x-127.5)/128 ; norm='imagenet': media/desv. de ImageNet."""
    x = torch.from_numpy(np.ascontiguousarray(x_uint8)).to(device).permute(0, 3, 1, 2).float()
    if norm == "facenet":
        return (x - 127.5) / 128.0
    if norm == "imagenet":
        return (x / 255.0 - IMAGENET_MEAN.to(device)) / IMAGENET_STD.to(device)
    raise ValueError(norm)


# ------------------------------------------------------------------ FaceNet
def facenet(pretrained="vggface2", device="cuda"):
    """InceptionResnetV1 de facenet-pytorch (embedding de 512, L2-normalizado por la red).
    Pesos: 'vggface2' (20180402-114759) o 'casia-webface' (20180408-102900), publicados en
    https://github.com/timesler/facenet-pytorch/releases (conversion de davidsandberg/facenet)."""
    from facenet_pytorch import InceptionResnetV1
    return InceptionResnetV1(pretrained=pretrained, classify=False).eval().to(device)


# ------------------------------------------------------------------ CNN propia
def _block(cin, cout):
    return nn.Sequential(
        nn.Conv2d(cin, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
        nn.Conv2d(cout, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
        nn.MaxPool2d(2))


class SmallFaceCNN(nn.Module):
    """CNN propia entrenada desde cero: 5 bloques conv (160->5 px), embedding de 128 y
    capa de clasificacion sobre las identidades registradas."""

    def __init__(self, n_classes, emb_dim=128, dropout=0.3):
        super().__init__()
        self.body = nn.Sequential(_block(3, 32), _block(32, 64), _block(64, 128), _block(128, 256), _block(256, 256))
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.emb = nn.Sequential(nn.Flatten(), nn.Dropout(dropout), nn.Linear(256, emb_dim), nn.BatchNorm1d(emb_dim))
        self.head = nn.Linear(emb_dim, n_classes)

    def features(self, x):
        return self.emb(self.pool(self.body(x)))

    def forward(self, x):
        return self.head(F.relu(self.features(x)))


class ResNet18Face(nn.Module):
    """ResNet-18 preentrenada en ImageNet (objetos generales, no rostros), ajustada
    completa como clasificador de identidades. Embedding = salida de 512 tras el pooling."""

    def __init__(self, n_classes, dropout=0.3):
        super().__init__()
        from torchvision.models import ResNet18_Weights, resnet18
        net = resnet18(weights=ResNet18_Weights.IMAGENET1K_V1)
        net.fc = nn.Identity()
        self.backbone = net
        self.head = nn.Sequential(nn.Dropout(dropout), nn.Linear(512, n_classes))

    def features(self, x):
        return self.backbone(x)

    def forward(self, x):
        return self.head(self.features(x))


# ------------------------------------------------------------------ aumento de datos
def augment(x, gen):
    """Aumento por muestra en GPU sobre un lote normalizado (N,3,H,W): espejo horizontal,
    rotacion +-10 grados, escala 0.9-1.1, traslacion +-6 %, brillo/contraste +-20 %."""
    n = x.shape[0]
    dev = x.device
    r = lambda lo, hi: lo + (hi - lo) * torch.rand(n, device=dev, generator=gen)
    ang = r(-10, 10) * math.pi / 180
    sc = r(0.9, 1.1)
    flip = torch.where(torch.rand(n, device=dev, generator=gen) < 0.5, -1.0, 1.0)
    cos, sin = torch.cos(ang) / sc, torch.sin(ang) / sc
    theta = torch.zeros(n, 2, 3, device=dev)
    theta[:, 0, 0] = cos * flip
    theta[:, 0, 1] = -sin
    theta[:, 1, 0] = sin * flip
    theta[:, 1, 1] = cos
    theta[:, 0, 2] = r(-0.06, 0.06)
    theta[:, 1, 2] = r(-0.06, 0.06)
    grid = F.affine_grid(theta, x.shape, align_corners=False)
    x = F.grid_sample(x, grid, mode="bilinear", padding_mode="reflection", align_corners=False)
    mean = x.mean(dim=(1, 2, 3), keepdim=True)
    x = (x - mean) * r(0.8, 1.2).view(n, 1, 1, 1) + mean + r(-0.2, 0.2).view(n, 1, 1, 1)
    return x


# ------------------------------------------------------------------ entrenamiento
def train_classifier(model, X_tr, y_tr, norm, device, epochs=40, batch=64, lr=1e-3, wd=5e-4,
                     label_smoothing=0.1, seed=42, X_mon=None, y_mon=None):
    """Entrena con AdamW + coseno, numero FIJO de epocas (sin parada temprana: no se
    elige nada con validacion en la tarea 2.1). X_mon/y_mon solo se usan para registrar
    la curva de exactitud de clasificacion, no para seleccionar el modelo."""
    torch.manual_seed(seed)
    gen = torch.Generator(device=device).manual_seed(seed)
    model = model.to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)
    steps = epochs * math.ceil(len(X_tr) / batch)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps, pct_start=0.1)
    crit = nn.CrossEntropyLoss(label_smoothing=label_smoothing)
    Xt = to_tensor(X_tr, norm, device)
    yt = torch.as_tensor(y_tr, device=device)
    Xm = to_tensor(X_mon, norm, device) if X_mon is not None else None
    hist = []
    rng = np.random.default_rng(seed)
    t0 = time.time()
    for ep in range(epochs):
        model.train()
        perm = torch.as_tensor(rng.permutation(len(Xt)), device=device)
        tot, correct, n = 0.0, 0, 0
        for k in range(0, len(perm), batch):
            idx = perm[k:k + batch]
            if len(idx) < 2:
                continue
            xb = augment(Xt[idx], gen)
            out = model(xb)
            loss = crit(out, yt[idx])
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            sched.step()
            tot += loss.item() * len(idx)
            correct += (out.argmax(1) == yt[idx]).sum().item()
            n += len(idx)
        row = {"epoca": ep + 1, "loss_train": tot / n, "acc_train": correct / n}
        if Xm is not None:
            model.eval()
            with torch.no_grad():
                out = torch.cat([model(Xm[k:k + 256]) for k in range(0, len(Xm), 256)])
                row["loss_val"] = crit(out, torch.as_tensor(y_mon, device=device)).item()
                row["acc_val"] = (out.argmax(1).cpu().numpy() == y_mon).mean()
        hist.append(row)
    if device == "cuda":
        torch.cuda.synchronize()
    return model.eval(), hist, time.time() - t0


@torch.no_grad()
def embed(model, X_uint8, norm, device, batch=128, fn=None):
    """Vectores L2-normalizados (N,D) en numpy. fn: funcion modelo->vector (por defecto
    model.features si existe, si no model(x))."""
    model.eval()
    f = fn or (model.features if hasattr(model, "features") else model)
    out = []
    for k in range(0, len(X_uint8), batch):
        out.append(F.normalize(f(to_tensor(X_uint8[k:k + batch], norm, device)), dim=1).cpu())
    return torch.cat(out).numpy()


# ------------------------------------------------------------------ LBPH (linea base)
def to_gray(X_uint8, size=None):
    out = []
    for im in X_uint8:
        g = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY)
        if size:
            g = cv2.resize(g, (size, size), interpolation=cv2.INTER_AREA)
        out.append(g)
    return out


def lbph_histograms(gray_list, radius=1, neighbors=8, grid=8):
    """Histogramas LBPH de OpenCV (cv2.face). Se 'entrena' un reconocedor solo para
    extraer el histograma concatenado de cada imagen, en el mismo orden."""
    rec = cv2.face.LBPHFaceRecognizer_create(radius=radius, neighbors=neighbors, grid_x=grid, grid_y=grid)
    rec.train(gray_list, np.zeros(len(gray_list), np.int32))
    return np.vstack([h.ravel() for h in rec.getHistograms()]).astype(np.float32)


def chi2_dist(A, B, eps=1e-10):
    """Distancia chi-cuadrado (la de LBPH en OpenCV) entre filas de A (n,d) y B (m,d) -> (n,m)."""
    out = np.empty((len(A), len(B)), np.float32)
    for i in range(len(A)):
        d = A[i][None, :] - B
        out[i] = (d * d / (A[i][None, :] + B + eps)).sum(1)
    return out
