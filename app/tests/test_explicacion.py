"""Modo explicación (exposición): camino de la decisión. Solo en la instancia local, nunca en la pública."""
import datetime as dt

import numpy as np
import pytest

from app.almacen import Almacen
from app.intentos import ControlIntentos
from app.main import create_app
from conftest import Reloj, ServicioDoble, jpeg_b64

CINCO = [jpeg_b64()] * 5
CLAVE = "tulipan-azul-7"


def verificar(c, usuario="Brad Pitt", explicar=True, **kw):
    return c.post("/api/verificar", json={"usuario": usuario, "fotogramas": CINCO, "explicar": explicar}, **kw)


def test_local_entrega_explicacion_solo_si_se_pide(entorno_app):
    c, srv = entorno_app["c"], entorno_app["srv"]
    assert "explicacion" not in verificar(c, explicar=False).get_json()
    j = verificar(c).get_json()
    assert j["explicacion"]["modo"] == "A" and srv.explicados == ["A"]


def test_pagina_local_ofrece_el_interruptor(entorno_app):
    assert 'id="explicar"' in entorno_app["c"].get("/").get_data(as_text=True)


def test_desactivable_por_configuracion(tmp_path, monkeypatch):
    from app import config as CFG
    monkeypatch.setattr(CFG, "EXPLICACION", False)
    alm = Almacen(tmp_path / "p")
    srv = ServicioDoble(alm)
    app = create_app(srv, alm, ControlIntentos(alm.dir, reloj=Reloj()))
    c = app.test_client()
    assert "explicacion" not in verificar(c).get_json() and srv.explicados == []
    assert 'id="explicar"' not in c.get("/").get_data(as_text=True)


def test_publica_nunca_explica(tmp_path):
    import base64
    alm = Almacen(tmp_path / "p")
    srv = ServicioDoble(alm)
    app = create_app(srv, alm, ControlIntentos(alm.dir, reloj=Reloj(), tope=1000), modo_publico=True, clave_publica="pub-123")
    c = app.test_client()
    h = {"Authorization": "Basic " + base64.b64encode(b"demo:pub-123").decode()}
    j = verificar(c, headers=h).get_json()
    assert j["resultado"] == "permitido" and "explicacion" not in j and srv.explicados == []
    assert 'id="explicar"' not in c.get("/", headers=h).get_data(as_text=True)


@pytest.fixture
def con_clave(entorno_app, monkeypatch):
    monkeypatch.setenv("FACEID_ADMIN_PASSWORD", "admin-prueba")
    c = entorno_app["c"]
    assert c.post("/admin/entrar", data={"clave": "admin-prueba"}).status_code == 302
    r = c.post("/admin/api/registrar", json={"id": "V01", "autorizacion": True, "fecha_autorizacion": dt.date.today().isoformat(),
                                              "fotos": [jpeg_b64()] * 12, "seguridad": "rostro_clave", "clave": CLAVE})
    assert r.status_code == 200
    return entorno_app


@pytest.mark.parametrize("texto,resultado", [(CLAVE, "permitido"), ("otra-clave-mala", "denegado")])
def test_con_palabra_clave_la_explicacion_llega_tras_el_paso_2(con_clave, texto, resultado):
    """En el paso 1 no se muestra (revelaría si el rostro coincidió); se entrega con la respuesta del paso 2."""
    c = con_clave["c"]
    j = verificar(c, "V01").get_json()
    assert j["resultado"] == "requiere_clave" and "explicacion" not in j
    j = c.post("/api/clave", json={"token": j["token"], "clave": texto}).get_json()
    assert j["resultado"] == resultado and j["explicacion"]["modo"] == "A"


def test_modo_b_con_explicacion(con_clave):
    c = con_clave["c"]
    c.post("/admin/api/clave", json={"id": "V01", "accion": "quitar"})
    j = c.post("/api/identificar", json={"fotogramas": CINCO, "explicar": True}).get_json()
    assert j["resultado"] == "permitido" and j["explicacion"]["modo"] == "B"


def test_explicacion_no_deja_archivos(entorno_app):
    antes = {p for p in entorno_app["alm"].dir.rglob("*")}
    verificar(entorno_app["c"])
    nuevos = {p for p in entorno_app["alm"].dir.rglob("*")} - antes
    assert not [p for p in nuevos if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".npy", ".npz"}]


# ------------------------------------------------------------------ con el modelo real
@pytest.mark.lento
def test_capas_reproducen_el_embedding_de_la_red():
    """Recorrer FaceNet capa por capa da el mismo vector que la red completa: la explicación no altera el modelo."""
    from app import config as CFG
    if not (CFG.PAQUETE_MODELO / "red.ts").exists():
        pytest.skip("Falta el paquete del modelo en models/")
    from app.explicacion import CAPAS, explicar_rostro
    from app.servicio import ServicioVerificacion
    srv = ServicioVerificacion()
    crop = np.random.default_rng(0).integers(0, 256, (160, 160, 3), dtype=np.uint8)
    e = explicar_rostro(srv.v, crop)
    ref = srv.embeddings([crop])[0].cpu().numpy()
    assert np.allclose(np.array(e["embedding"]), ref, atol=1e-4)
    assert len(e["embedding"]) == 512 and len(e["capas"]) == len(CAPAS)
    assert all(x["mosaico"].startswith("data:image/jpeg;base64,") for x in e["capas"])
    assert e["recorte"].startswith("data:image/jpeg") and e["atencion"].startswith("data:image/jpeg")
