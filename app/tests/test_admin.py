"""Administración: contraseña, registro (autorización obligatoria, sin imágenes por defecto), eliminación y desbloqueo."""
import datetime as dt

import pytest

from app import config as CFG
from app.almacen import Almacen
from conftest import jpeg_b64

CLAVE = "clave-de-prueba"
HOY = dt.date.today().isoformat()


@pytest.fixture
def admin(entorno_app, monkeypatch):
    monkeypatch.setenv("FACEID_ADMIN_PASSWORD", CLAVE)
    c = entorno_app["c"]
    assert c.post("/admin/entrar", data={"clave": CLAVE}).status_code == 302
    return entorno_app


def peticion(uid="V01", autorizacion=True, fecha=HOY, n=12, conservar=False, color=128):
    return {"id": uid, "autorizacion": autorizacion, "fecha_autorizacion": fecha, "conservar_fotos": conservar,
            "fotos": [jpeg_b64(color)] * n}


def test_admin_deshabilitado_sin_variable(entorno_app, monkeypatch):
    monkeypatch.delenv("FACEID_ADMIN_PASSWORD", raising=False)
    assert "deshabilitada" in entorno_app["c"].get("/admin/").get_data(as_text=True)
    assert entorno_app["c"].post("/admin/entrar", data={"clave": "x"}).status_code == 401


def test_contrasena_incorrecta(entorno_app, monkeypatch):
    monkeypatch.setenv("FACEID_ADMIN_PASSWORD", CLAVE)
    assert entorno_app["c"].post("/admin/entrar", data={"clave": "mala"}).status_code == 401


def test_api_requiere_sesion(entorno_app):
    c = entorno_app["c"]
    assert c.post("/admin/api/registrar", json=peticion()).status_code == 401
    assert c.post("/admin/api/eliminar", json={"id": "V01"}).status_code == 401
    assert c.post("/admin/api/desbloquear", json={"id": "Brad Pitt"}).status_code == 401


def test_registro_sin_autorizacion_rechazado(admin):
    r = admin["c"].post("/admin/api/registrar", json=peticion(autorizacion=False))
    assert r.status_code == 400 and "autorización" in r.get_json()["error"]
    assert admin["alm"].usuarios() == []


def test_registro_sin_fecha_o_futura_rechazado(admin):
    assert admin["c"].post("/admin/api/registrar", json=peticion(fecha="")).status_code == 400
    futura = (dt.date.today() + dt.timedelta(days=1)).isoformat()
    assert admin["c"].post("/admin/api/registrar", json=peticion(fecha=futura)).status_code == 400
    assert admin["alm"].usuarios() == []


def test_registro_numero_de_fotos(admin):
    assert admin["c"].post("/admin/api/registrar", json=peticion(n=CFG.REGISTRO_MIN_FOTOS - 1)).status_code == 400
    assert admin["c"].post("/admin/api/registrar", json=peticion(n=CFG.REGISTRO_MAX_FOTOS + 1)).status_code == 400


def test_registro_sin_rostros_validos(admin):
    r = admin["c"].post("/admin/api/registrar", json=peticion(color=0))
    assert r.status_code == 400 and "rostro válido" in r.get_json()["error"]


def test_seudonimo_no_valido_o_repetido(admin):
    assert admin["c"].post("/admin/api/registrar", json=peticion(uid="../x")).status_code == 400
    assert admin["c"].post("/admin/api/registrar", json=peticion(uid="Juan Pérez")).status_code == 400
    assert admin["c"].post("/admin/api/registrar", json=peticion(uid="Brad Pitt")).status_code == 400


def test_registro_ok_guarda_solo_plantilla_y_meta(admin):
    r = admin["c"].post("/admin/api/registrar", json=peticion())
    assert r.status_code == 200 and r.get_json()["fotos_conservadas"] is False
    d = admin["alm"].dir_usuarios / "V01"
    assert sorted(p.name for p in d.rglob("*")) == ["meta.json", "plantilla.npy"]
    assert not list(admin["alm"].dir.rglob("*.jpg")) and not list(admin["alm"].dir.rglob("*.png"))
    m = admin["alm"].meta("V01")
    assert m["autorizacion_escrita"] is True and m["fecha_autorizacion"] == HOY and m["n_fotos_validas"] == 12
    # aparece como usuario de la demo y las 2 identidades del dataset siguen ahí
    us = admin["srv"].usuarios()
    assert ("V01", "demo") in us and ("Brad Pitt", "dataset") in us


def test_registro_conservando_fotos(admin):
    assert admin["c"].post("/admin/api/registrar", json=peticion(conservar=True)).status_code == 200
    assert len(list((admin["alm"].dir_usuarios / "V01" / "fotos").glob("*.jpg"))) == 12


def test_eliminar_borra_todo(admin):
    c = admin["c"]
    c.post("/admin/api/registrar", json=peticion(conservar=True))
    admin["srv"].resultado = "denegado"
    c.post("/api/verificar", json={"usuario": "V01", "fotogramas": [jpeg_b64()] * 5})
    assert c.post("/admin/api/eliminar", json={"id": "V01"}).status_code == 200
    assert not (admin["alm"].dir_usuarios / "V01").exists()
    assert "V01" not in admin["ctl"].resumen()
    assert all(r["usuario_solicitado"] != "V01" for r in admin["ctl"].ultimos_registros(100))
    assert c.post("/admin/api/eliminar", json={"id": "V01"}).status_code == 404


def test_desbloquear_desde_admin(admin):
    c, srv = admin["c"], admin["srv"]
    srv.resultado = "denegado"
    for _ in range(CFG.BLOQUEO_FALLOS):
        c.post("/api/verificar", json={"usuario": "Tom Cruise", "fotogramas": [jpeg_b64()] * 5})
    assert c.post("/api/verificar", json={"usuario": "Tom Cruise", "fotogramas": [jpeg_b64()] * 5}).status_code == 429
    assert c.post("/admin/api/desbloquear", json={"id": "Tom Cruise"}).status_code == 200
    srv.resultado = "permitido"
    assert c.post("/api/verificar", json={"usuario": "Tom Cruise", "fotogramas": [jpeg_b64()] * 5}).status_code == 200


def test_panel_muestra_usuarios_y_registros(admin):
    admin["c"].post("/admin/api/registrar", json=peticion())
    html = admin["c"].get("/admin/").get_data(as_text=True)
    assert "V01" in html and "Firmada" in html


def test_almacen_rechaza_carpeta_del_repositorio(root):
    with pytest.raises(ValueError):
        Almacen(root / "docs" / "privado_no")
