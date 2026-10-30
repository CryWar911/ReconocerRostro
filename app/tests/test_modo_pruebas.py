"""Modo pruebas (tarea 3.4): registro de todos los intentos con caso y tiempos, y resumen por caso."""
import pandas as pd
import pytest

from app import config as CFG
from app.resumen_pruebas import resumir
from conftest import jpeg_b64

CINCO = [jpeg_b64()] * 5


@pytest.fixture
def pruebas(entorno_app):
    entorno_app["app"].modo_pruebas = True
    return entorno_app


def post(c, usuario="Brad Pitt", caso="CF01", captura=1.62):
    return c.post("/api/verificar", json={"usuario": usuario, "fotogramas": CINCO, "caso": caso, "segundos_captura": captura})


def test_registra_todos_los_intentos_con_caso(pruebas):
    c, srv = pruebas["c"], pruebas["srv"]
    j = post(c).get_json()
    assert j["id_intento"]
    srv.resultado = "denegado"
    post(c, "Tom Cruise", "CF06")
    d = pd.read_csv(pruebas["alm"].dir / "registro_pruebas.csv", dtype=str)
    assert list(d.resultado) == ["permitido", "denegado"] and list(d.caso) == ["CF01", "CF06"]
    assert d.segundos_captura.iloc[0] == "1.620"
    assert "puntuacion" not in " ".join(d.columns)


def test_intento_bloqueado_queda_registrado(pruebas):
    c, srv = pruebas["c"], pruebas["srv"]
    srv.resultado = "denegado"
    for _ in range(CFG.BLOQUEO_FALLOS + 1):
        r = post(c, "Tom Cruise", "CF10")
    assert r.status_code == 429
    d = pd.read_csv(pruebas["alm"].dir / "registro_pruebas.csv", dtype=str)
    assert list(d.resultado) == ["denegado"] * CFG.BLOQUEO_FALLOS + ["bloqueado"]


def test_tiempo_total_del_cliente_y_resumen(pruebas):
    c, srv = pruebas["c"], pruebas["srv"]
    for caso, res in [("CF01", "permitido"), ("CF01", "permitido"), ("CF08", "no_concluyente"), ("ENSAYO_E2E", "permitido")]:
        srv.resultado = res
        j = post(c, caso=caso).get_json()
        assert c.post("/api/prueba/tiempo", json={"id_intento": j["id_intento"], "segundos_total": 2.5}).status_code == 200
        pruebas["reloj"].t += 1
    res = resumir(pruebas["alm"].dir).set_index("caso")
    assert res.loc["CF01", "intentos"] == 2 and res.loc["CF01", "permitido"] == 2
    assert res.loc["CF08", "no_concluyente"] == 1 and "sin_rostro: 5" in res.loc["CF08", "problemas_por_fotograma"]
    assert res.loc["CF01", "segundos_total_cliente_mediana"] == 2.5
    assert bool(res.loc["ENSAYO_E2E", "es_ensayo"]) and not bool(res.loc["CF01", "es_ensayo"])
    assert "usuario_solicitado" not in res.reset_index().columns   # el resumen no lleva seudónimos


def test_caso_no_valido_se_vacia(pruebas):
    post(pruebas["c"], caso="../../x")
    d = pd.read_csv(pruebas["alm"].dir / "registro_pruebas.csv", dtype=str, keep_default_na=False)
    assert d.caso.iloc[0] == ""


def test_sin_modo_pruebas_no_hay_registro_ni_ruta(entorno_app):
    c = entorno_app["c"]
    j = post(c).get_json()
    assert j["id_intento"] is None
    assert not (entorno_app["alm"].dir / "registro_pruebas.csv").exists()
    assert c.post("/api/prueba/tiempo", json={"id_intento": "1.0", "segundos_total": 2}).status_code == 404
    assert "MODO PRUEBAS" not in c.get("/").get_data(as_text=True)


def test_pagina_muestra_campo_caso_en_modo_pruebas(pruebas):
    assert "Caso de prueba" in pruebas["c"].get("/").get_data(as_text=True)
