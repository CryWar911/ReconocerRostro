"""Modo público (túnel): rutas de administración 404, autenticación básica, límite por IP real y estado compartido
con la instancia de administración."""
import base64

import numpy as np
import pytest

from app import config as CFG
from app import publico as PUB
from app.almacen import Almacen
from app.intentos import ControlIntentos
from app.main import create_app
from conftest import Reloj, ServicioDoble, jpeg_b64

CLAVE = "clave-publica-de-prueba"
CINCO = [jpeg_b64()] * 5


def cabecera(clave=CLAVE, usuario="demo"):
    return {"Authorization": "Basic " + base64.b64encode(f"{usuario}:{clave}".encode()).decode()}


def tunel(ip):
    """Cabeceras que añade Cloudflare a una petición que llega por el túnel."""
    return {"CF-Connecting-IP": ip, "CF-Ray": "8a1b2c3d4e5f-LIM"}


@pytest.fixture
def publica(tmp_path, monkeypatch):
    monkeypatch.setattr(CFG, "LIMITE_IP_PETICIONES", 3)
    monkeypatch.setattr(CFG, "LIMITE_AUTH_FALLOS", 4)
    alm = Almacen(tmp_path / "privado")
    reloj = Reloj()
    ctl = ControlIntentos(alm.dir, reloj=reloj, tope=1000)
    srv = ServicioDoble(alm)
    app = create_app(srv, alm, ctl, modo_publico=True, clave_publica=CLAVE)
    app.config["TESTING"] = True
    return {"app": app, "c": app.test_client(), "alm": alm, "ctl": ctl, "srv": srv}


def verificar(c, h, usuario="Brad Pitt"):
    return c.post("/api/verificar", json={"usuario": usuario, "fotogramas": CINCO}, headers=h)


# ------------------------------------------------------------------ arranque
def test_no_arranca_sin_contrasena(tmp_path, monkeypatch):
    monkeypatch.delenv("FACEID_ACCESO_PUBLICO", raising=False)
    alm = Almacen(tmp_path / "p")
    with pytest.raises(RuntimeError):
        create_app(ServicioDoble(alm), alm, ControlIntentos(alm.dir), modo_publico=True)


# ------------------------------------------------------------------ rutas de administración
@pytest.mark.parametrize("metodo,ruta", [
    ("get", "/admin/"), ("post", "/admin/entrar"), ("post", "/admin/salir"), ("get", "/admin/registrar"),
    ("post", "/admin/api/registrar"), ("post", "/admin/api/eliminar"), ("post", "/admin/api/desbloquear"),
])
def test_rutas_de_administracion_404(publica, metodo, ruta, monkeypatch):
    monkeypatch.setenv("FACEID_ADMIN_PASSWORD", "aunque-exista")
    r = getattr(publica["c"], metodo)(ruta, headers=cabecera(), json={"id": "Brad Pitt"})
    assert r.status_code == 404


def test_no_hay_rutas_de_administracion_registradas(publica):
    reglas = [str(r) for r in publica["app"].url_map.iter_rules()]
    assert not any(r.startswith("/admin") for r in reglas)
    assert not any(k in " ".join(reglas) for k in ("registrar", "eliminar", "desbloquear"))


def test_pagina_sin_enlace_a_administracion_y_con_aviso(publica):
    html = publica["c"].get("/", headers=cabecera()).get_data(as_text=True)
    assert "/admin" not in html
    assert "no tiene detección de vida" in html and "imágenes de la cámara no se guardan" in html


# ------------------------------------------------------------------ autenticación
def test_sin_credenciales_401_en_todo(publica):
    c = publica["c"]
    for ruta in ["/", "/acerca", "/api/usuarios", "/static/app.js"]:
        r = c.get(ruta)
        assert r.status_code == 401 and "Basic" in r.headers["WWW-Authenticate"]
    assert verificar(c, {}).status_code == 401


def test_contrasena_incorrecta_401(publica):
    assert publica["c"].get("/", headers=cabecera("mala")).status_code == 401


def test_contrasena_correcta(publica):
    c = publica["c"]
    assert c.get("/", headers=cabecera()).status_code == 200
    assert verificar(c, cabecera()).status_code == 200


def test_demasiadas_contrasenas_fallidas_por_ip(publica):
    c = publica["c"]
    for _ in range(4):
        assert c.get("/", headers={**cabecera("mala"), **tunel("203.0.113.7")}).status_code == 401
    # agotado: incluso con la contraseña correcta, esa IP espera
    assert c.get("/", headers={**cabecera(), **tunel("203.0.113.7")}).status_code == 429
    # otra IP del túnel no se ve afectada
    assert c.get("/", headers={**cabecera(), **tunel("198.51.100.9")}).status_code == 200


# ------------------------------------------------------------------ límite por IP real
def test_limite_de_verificaciones_por_ip_del_tunel(publica):
    c = publica["c"]
    h1 = {**cabecera(), **tunel("203.0.113.10")}
    for _ in range(3):
        assert verificar(c, h1).status_code == 200
    r = verificar(c, h1)
    assert r.status_code == 429 and r.get_json()["titulo"] == "Demasiadas peticiones"
    assert verificar(c, {**cabecera(), **tunel("203.0.113.11")}).status_code == 200   # otra IP real


def test_otras_rutas_no_consumen_el_limite(publica):
    c = publica["c"]
    h = {**cabecera(), **tunel("203.0.113.20")}
    for _ in range(10):
        assert c.get("/", headers=h).status_code == 200
    assert verificar(c, h).status_code == 200


def test_ip_real_solo_desde_el_tunel():
    class Req:
        def __init__(self, remota, headers):
            self.remote_addr, self.headers = remota, headers
    # por el túnel: loopback + cabeceras de Cloudflare -> IP del cliente
    assert PUB.ip_real(Req("127.0.0.1", tunel("203.0.113.5"))) == "203.0.113.5"
    # sin CF-Ray no se confía en CF-Connecting-IP
    assert PUB.ip_real(Req("127.0.0.1", {"CF-Connecting-IP": "203.0.113.5"})) == "127.0.0.1"
    # desde otra dirección (no loopback) nunca se usa la cabecera
    assert PUB.ip_real(Req("192.168.1.50", tunel("203.0.113.5"))) == "192.168.1.50"
    # valor no válido
    assert PUB.ip_real(Req("127.0.0.1", tunel("no-es-ip"))) == "127.0.0.1"


def test_cabecera_falsa_sin_cf_ray_comparte_el_limite_local(publica):
    """Sin CF-Ray, cambiar CF-Connecting-IP no da un límite nuevo: cuenta como 127.0.0.1."""
    c = publica["c"]
    for k in range(3):
        assert verificar(c, {**cabecera(), "CF-Connecting-IP": f"203.0.113.{k}"}).status_code == 200
    assert verificar(c, {**cabecera(), "CF-Connecting-IP": "203.0.113.99"}).status_code == 429


# ------------------------------------------------------------------ dos instancias, mismo almacén
def test_publica_ve_usuarios_nuevos_sin_reiniciar(tmp_path, monkeypatch):
    monkeypatch.setenv("FACEID_ADMIN_PASSWORD", "admin-prueba")
    alm_pub, alm_adm = Almacen(tmp_path / "privado"), Almacen(tmp_path / "privado")
    pub = create_app(ServicioDoble(alm_pub), alm_pub, ControlIntentos(alm_pub.dir), modo_publico=True, clave_publica=CLAVE)
    adm = create_app(ServicioDoble(alm_adm), alm_adm, ControlIntentos(alm_adm.dir), modo_publico=False)
    cp, ca = pub.test_client(), adm.test_client()
    assert "V01" not in cp.get("/", headers=cabecera()).get_data(as_text=True)
    ca.post("/admin/entrar", data={"clave": "admin-prueba"})
    import datetime as dt
    r = ca.post("/admin/api/registrar", json={"id": "V01", "autorizacion": True, "fecha_autorizacion": dt.date.today().isoformat(),
                                              "fotos": [jpeg_b64()] * 12})
    assert r.status_code == 200
    assert "V01" in cp.get("/", headers=cabecera()).get_data(as_text=True)
    assert verificar(cp, cabecera(), "V01").status_code == 200
    # eliminado en la de administración -> la pública ya no lo acepta
    ca.post("/admin/api/eliminar", json={"id": "V01"})
    assert verificar(cp, cabecera(), "V01").status_code == 400


def test_plantilla_reemplazada_se_recarga(tmp_path):
    a1, a2 = Almacen(tmp_path / "privado"), Almacen(tmp_path / "privado")
    a1.guardar("V01", np.ones(512, np.float32), {"id": "V01"})
    t1 = a2.plantilla("V01").copy()
    a1.eliminar("V01")
    import time
    time.sleep(0.02)
    v = np.zeros(512, np.float32); v[0] = 1
    a1.guardar("V01", v, {"id": "V01"})
    assert not np.allclose(a2.plantilla("V01"), t1) and a2.plantilla("V01")[0] == pytest.approx(1.0)


def test_desbloqueo_en_administracion_vale_en_la_publica(tmp_path):
    r = Reloj()
    pub, adm = ControlIntentos(tmp_path, reloj=r), ControlIntentos(tmp_path, reloj=r)
    for _ in range(CFG.BLOQUEO_FALLOS):
        pub.anotar("Tom Cruise", "denegado")
    assert pub.comprobar("Tom Cruise")["resultado"] == "bloqueado"
    assert adm.resumen()["Tom Cruise"]["bloqueado_seg"] > 0       # la de administración lo ve
    adm.desbloquear("Tom Cruise")
    assert pub.comprobar("Tom Cruise") is None                    # la pública lo ve sin reiniciar
