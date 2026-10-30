"""Rutas de inicio de sesión con un servicio doble (sin modelo)."""
from app import config as CFG
from conftest import jpeg_b64

CINCO = [jpeg_b64()] * 5


def test_pagina_inicio_lista_usuarios(entorno_app):
    html = entorno_app["c"].get("/").get_data(as_text=True)
    assert "Brad Pitt" in html and "detección de vida" in html


def test_pagina_acerca_explica_limitaciones(entorno_app):
    html = entorno_app["c"].get("/acerca").get_data(as_text=True)
    assert "No tiene detección de vida" in html and "suplantación" in html
    assert "bloquear temporalmente" in html


def test_verificar_ok_sin_puntuaciones(entorno_app):
    c, srv = entorno_app["c"], entorno_app["srv"]
    r = c.post("/api/verificar", json={"usuario": "Brad Pitt", "fotogramas": CINCO})
    assert r.status_code == 200
    j = r.get_json()
    assert j["resultado"] == "permitido" and j["titulo"] == "Acceso permitido"
    assert not any(k in j for k in ("puntuaciones", "puntuacion", "plantilla", "votos"))
    assert srv.recibidos == [("Brad Pitt", 5, (48, 64, 3))]


def test_usuario_desconocido_rechazado(entorno_app):
    c, srv = entorno_app["c"], entorno_app["srv"]
    assert c.post("/api/verificar", json={"usuario": "Nadie", "fotogramas": CINCO}).status_code == 400
    assert srv.recibidos == []


def test_numero_de_fotogramas_incorrecto(entorno_app):
    assert entorno_app["c"].post("/api/verificar", json={"usuario": "Brad Pitt", "fotogramas": CINCO[:2]}).status_code == 400


def test_fotograma_no_valido(entorno_app):
    r = entorno_app["c"].post("/api/verificar", json={"usuario": "Brad Pitt", "fotogramas": ["data:image/jpeg;base64,xxx"] * 5})
    assert r.status_code == 400


def test_bloqueo_tras_tres_denegados_y_429(entorno_app):
    c, srv = entorno_app["c"], entorno_app["srv"]
    srv.resultado = "denegado"
    for k in range(CFG.BLOQUEO_FALLOS):
        r = c.post("/api/verificar", json={"usuario": "Tom Cruise", "fotogramas": CINCO})
        assert r.get_json()["resultado"] == "denegado"
    assert "bloqueado" in r.get_json()["motivo"]
    n = len(srv.recibidos)
    r = c.post("/api/verificar", json={"usuario": "Tom Cruise", "fotogramas": CINCO})
    assert r.status_code == 429 and r.get_json()["titulo"] == "Usuario bloqueado temporalmente"
    assert len(srv.recibidos) == n          # bloqueado: ni siquiera se procesa
    # otro usuario no se ve afectado
    srv.resultado = "permitido"
    assert c.post("/api/verificar", json={"usuario": "Brad Pitt", "fotogramas": CINCO}).status_code == 200


def test_host_solo_local():
    assert CFG.HOST == "127.0.0.1"
