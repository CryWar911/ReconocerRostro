"""El modelo, las 24 plantillas y el umbral oficial no deben cambiar (regla de oro 1 del Sprint 3)."""
import hashlib
import json

import numpy as np
import pytest

from app import config as CFG


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


@pytest.fixture(scope="module")
def esperado(root):
    return json.loads((root / "app" / "modelo_esperado.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def paquete():
    if not (CFG.PAQUETE_MODELO / "red.ts").exists():
        pytest.skip("No está el paquete del modelo en models/ (no se versiona); cópielo para ejecutar esta prueba.")
    return CFG.PAQUETE_MODELO


def test_hash_red(paquete, esperado):
    assert sha256(paquete / "red.ts") == esperado["red_ts_sha256"]


def test_hash_plantillas_dataset(paquete, esperado):
    assert sha256(paquete / "plantillas.npz") == esperado["plantillas_npz_sha256"]
    assert len(np.load(paquete / "plantillas.npz")["usuarios"]) == esperado["n_identidades_dataset"]


def test_hash_pesos_originales_en_config(paquete, esperado):
    cfg = json.loads((paquete / "config.json").read_text(encoding="utf-8"))
    assert cfg["pesos_sha256"] == esperado["pesos_originales_sha256"]


def test_umbral_oficial(paquete, esperado):
    cfg = json.loads((paquete / "config.json").read_text(encoding="utf-8"))
    assert cfg["umbral"] == esperado["umbral"] == CFG.UMBRAL_OFICIAL
    assert cfg["umbral_estado"] == esperado["umbral_estado"]
