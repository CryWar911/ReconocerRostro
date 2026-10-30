"""Modos de ingreso: A (nombre + rostro), B (solo cámara, 1:N) y palabra clave opcional por usuario."""
import base64
import datetime as dt

import pytest

from app import claves as K
from app import config as CFG
from app import decision as D
from conftest import jpeg_b64

U = CFG.UMBRAL_OFICIAL
CINCO = [jpeg_b64()] * 5
CLAVE = "tulipan-azul-7"


def ident(punt, estados=None, usuarios=("V01", "V02", "V03")):
    estados = estados or ["valido"] * len(punt)
    return D.identificar(estados, punt, list(usuarios), U, CFG.MARGEN_1N, CFG.MIN_VOTOS, CFG.MIN_VALIDOS)


# ------------------------------------------------------------------ decisión 1:N (pura)
def test_1n_acepta_al_usuario_correcto():
    r = ident([[0.80, 0.30, 0.20]] * 5)
    assert r["resultado"] == D.PERMITIDO and r["usuario"] == "V01" and r["motivo"] == "Hola, V01."


def test_1n_rechaza_por_margen_insuficiente():
    r = ident([[0.80, 0.80 - CFG.MARGEN_1N / 2, 0.2]] * 5)
    assert r["resultado"] == D.NO_IDENTIFICADO and r["usuario"] is None
    assert r["titulo"] == "No se pudo identificar de forma confiable"


def test_1n_margen_justo_si_vota():
    assert ident([[0.80, 0.80 - CFG.MARGEN_1N - 1e-6, 0.2]] * 5)["resultado"] == D.PERMITIDO


def test_1n_rechaza_si_el_mejor_cambia_entre_fotogramas():
    r = ident([[0.9, 0.1, 0.1], [0.1, 0.9, 0.1], [0.9, 0.1, 0.1], [0.1, 0.9, 0.1], [0.1, 0.1, 0.9]])
    assert r["resultado"] == D.NO_IDENTIFICADO


def test_1n_bajo_el_umbral_no_identifica():
    assert ident([[U - 0.01, 0.1, 0.1]] * 5)["resultado"] == D.NO_IDENTIFICADO


def test_1n_tres_de_cinco_basta():
    r = ident([[0.9, 0.1, 0.1]] * 3 + [[0.1, 0.9, 0.1], [0.5, 0.5, 0.1]])
    assert r["resultado"] == D.PERMITIDO and r["usuario"] == "V01"


def test_1n_pocos_fotogramas_validos_no_concluyente():
    r = ident([[0.9, 0.1, 0.1]] * 2 + [None] * 3, estados=["valido"] * 2 + ["sin_rostro"] * 3)
    assert r["resultado"] == D.NO_CONCLUYENTE


def test_1n_con_un_solo_usuario():
    assert ident([[0.8]] * 5, usuarios=("V01",))["resultado"] == D.PERMITIDO


def test_1n_no_revela_puntuaciones():
    r = ident([[0.8123, 0.3, 0.2]] * 5)
    assert "0.81" not in repr(r)


# ------------------------------------------------------------------ palabra clave (hash)
def test_clave_hash_scrypt_con_sal():
    h1, h2 = K.hashear(CLAVE), K.hashear(CLAVE)
    assert h1.startswith("scrypt$") and h1 != h2 and CLAVE not in h1     # sal distinta en cada hash
    assert K.comprobar(CLAVE, h1) and not K.comprobar(CLAVE + "x", h1)
    with pytest.raises(K.ErrorClave):
        K.hashear("corta")


# ------------------------------------------------------------------ app completa
@pytest.fixture
def adm(entorno_app, monkeypatch):
    monkeypatch.setenv("FACEID_ADMIN_PASSWORD", "admin-prueba")
    c = entorno_app["c"]
    assert c.post("/admin/entrar", data={"clave": "admin-prueba"}).status_code == 302
    entorno_app["app"].modo_pruebas = True

    def registrar(uid, clave=None):
        d = {"id": uid, "autorizacion": True, "fecha_autorizacion": dt.date.today().isoformat(), "fotos": [jpeg_b64()] * 12,
             "seguridad": "rostro_clave" if clave else "solo_rostro"}
        if clave:
            d["clave"] = clave
        r = c.post("/admin/api/registrar", json=d)
        assert r.status_code == 200, r.get_json()
        return r.get_json()
    entorno_app["registrar"] = registrar
    return entorno_app


def verificar(c, usuario, **kw):
    return c.post("/api/verificar", json={"usuario": usuario, "fotogramas": CINCO}, **kw)


def identificar(c, **kw):
    return c.post("/api/identificar", json={"fotogramas": CINCO}, **kw)


def clave(c, token, texto, **kw):
    return c.post("/api/clave", json={"token": token, "clave": texto}, **kw)


def textos_privados(carpeta):
    return "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in carpeta.rglob("*") if p.is_file())


def test_clave_solo_se_guarda_como_hash_y_nunca_en_registros(adm):
    adm["registrar"]("V01", CLAVE)
    c = adm["c"]
    m = adm["alm"].meta("V01")
    assert m["requiere_clave"] is True and m["clave_hash"].startswith("scrypt$")
    tok = verificar(c, "V01").get_json()["token"]
    clave(c, tok, "otra-clave-mala")
    tok = verificar(c, "V01").get_json()["token"]
    clave(c, tok, CLAVE)
    c.post("/admin/api/clave", json={"id": "V01", "accion": "cambiar", "clave": "nueva-clave-99"})
    todo = textos_privados(adm["alm"].dir)
    for secreto in (CLAVE, "otra-clave-mala", "nueva-clave-99"):
        assert secreto not in todo
    assert "palabra clave incorrecta" in (adm["alm"].dir / "registro_intentos.csv").read_text(encoding="utf-8")


def test_registro_rechaza_clave_corta(adm):
    r = adm["c"].post("/admin/api/registrar", json={"id": "V01", "autorizacion": True, "fecha_autorizacion": dt.date.today().isoformat(),
                                                    "fotos": [jpeg_b64()] * 12, "seguridad": "rostro_clave", "clave": "abc"})
    assert r.status_code == 400 and adm["alm"].usuarios() == []


def test_modo_a_rostro_y_clave_correcta(adm):
    adm["registrar"]("V01", CLAVE)
    j = verificar(adm["c"], "V01").get_json()
    assert j["resultado"] == "requiere_clave" and j["token"]
    j = clave(adm["c"], j["token"], CLAVE).get_json()
    assert j["resultado"] == "permitido" and j["titulo"] == "Acceso permitido"


def test_modo_a_sin_clave_no_pide_paso_2(adm):
    adm["registrar"]("V01")
    assert verificar(adm["c"], "V01").get_json()["resultado"] == "permitido"


def test_no_revela_si_fallo_el_rostro_o_la_clave(adm):
    adm["registrar"]("V01", CLAVE)
    c, srv = adm["c"], adm["srv"]
    srv.resultado = "denegado"                                   # el rostro NO coincide...
    j = verificar(c, "V01").get_json()
    assert j["resultado"] == "requiere_clave"                    # ...pero igual se pide la clave
    r_rostro = clave(c, j["token"], CLAVE).get_json()            # clave correcta, rostro malo
    srv.resultado = "permitido"
    r_clave = clave(c, verificar(c, "V01").get_json()["token"], "clave-mala").get_json()   # rostro bueno, clave mala
    for r in (r_rostro, r_clave):
        assert r["resultado"] == "denegado" and r["titulo"] == "Acceso denegado"
    assert r_rostro["motivo"] == r_clave["motivo"]


def test_clave_incorrecta_no_reinicia_el_contador(adm):
    adm["registrar"]("V01", CLAVE)
    c, srv = adm["c"], adm["srv"]
    srv.resultado = "denegado"
    clave(c, verificar(c, "V01").get_json()["token"], CLAVE)      # fallo 1 (rostro)
    clave(c, verificar(c, "V01").get_json()["token"], CLAVE)      # fallo 2 (rostro)
    srv.resultado = "permitido"
    j = clave(c, verificar(c, "V01").get_json()["token"], "mala-mala").get_json()   # rostro OK + clave mala = fallo 3
    assert "bloqueado" in j["motivo"]
    assert verificar(c, "V01").status_code == 429


def test_tres_claves_incorrectas_bloquean_al_usuario(adm):
    adm["registrar"]("V01", CLAVE)
    c = adm["c"]
    for _ in range(CFG.BLOQUEO_FALLOS):
        j = clave(c, verificar(c, "V01").get_json()["token"], "incorrecta").get_json()
    assert j["resultado"] == "denegado" and "bloqueado" in j["motivo"]
    assert verificar(c, "V01").status_code == 429


def test_acceso_completo_reinicia(adm):
    adm["registrar"]("V01", CLAVE)
    c = adm["c"]
    for _ in range(2):
        clave(c, verificar(c, "V01").get_json()["token"], "incorrecta")
    clave(c, verificar(c, "V01").get_json()["token"], CLAVE)          # acceso completo
    for _ in range(2):
        clave(c, verificar(c, "V01").get_json()["token"], "incorrecta")
    assert verificar(c, "V01").status_code == 200                       # solo 2 fallos tras el reinicio


def test_token_de_un_solo_uso_y_ligado_a_la_ip(adm):
    adm["registrar"]("V01", CLAVE)
    c = adm["c"]
    tok = verificar(c, "V01").get_json()["token"]
    assert clave(c, tok, CLAVE, environ_base={"REMOTE_ADDR": "10.0.0.9"}).status_code == 400   # otra IP
    tok = verificar(c, "V01").get_json()["token"]
    assert clave(c, tok, CLAVE).get_json()["resultado"] == "permitido"
    assert clave(c, tok, CLAVE).status_code == 400                     # ya usado
    assert clave(c, "inventado", CLAVE).status_code == 400


def test_modo_b_deshabilitado_sin_usuarios(entorno_app):
    c = entorno_app["c"]
    r = identificar(c)
    assert r.status_code == 409 and "deshabilitado" in r.get_json()["error"]
    assert "está deshabilitado" in c.get("/").get_data(as_text=True)


def test_modo_b_identifica_y_saluda_sin_puntuaciones(adm):
    adm["registrar"]("V01"); adm["registrar"]("V02")
    adm["srv"].identifica_a = "V02"
    j = identificar(adm["c"]).get_json()
    assert j["resultado"] == "permitido" and j["motivo"] == "Hola, V02."
    assert not any(k in j for k in ("puntuacion", "puntuaciones", "usuario"))


def test_modo_b_solo_compara_con_usuarios_de_la_app(adm):
    adm["registrar"]("V01")
    adm["srv"].identifica_a = "Brad Pitt"         # identidad del dataset: nunca es candidata
    assert identificar(adm["c"]).get_json()["resultado"] == "no_identificado"


def test_modo_b_no_registrado_no_identificado(adm):
    adm["registrar"]("V01")
    adm["srv"].identifica_a = None
    j = identificar(adm["c"]).get_json()
    assert j["resultado"] == "no_identificado" and j["titulo"] == "No se pudo identificar de forma confiable"


def test_modo_b_bloqueo_por_ip(adm):
    adm["registrar"]("V01")
    c = adm["c"]
    adm["srv"].identifica_a = None
    for _ in range(CFG.BLOQUEO_IP_FALLOS):
        j = identificar(c).get_json()
    assert "bloqueado" in j["motivo"]
    adm["srv"].identifica_a = "V01"
    assert identificar(c).status_code == 429                                         # misma IP: bloqueada
    assert identificar(c, environ_base={"REMOTE_ADDR": "10.0.0.7"}).status_code == 200   # otra IP: libre
    estado = (adm["alm"].dir / "estado_intentos.json").read_text(encoding="utf-8")
    assert "127.0.0.1" not in estado and "10.0.0.7" not in estado                    # la IP se guarda con hash


def test_modo_b_no_concluyente_no_suma_al_bloqueo_por_ip(adm):
    adm["registrar"]("V01")
    adm["srv"].identifica_a = "calidad"
    for _ in range(5):
        assert identificar(adm["c"]).get_json()["resultado"] == "no_concluyente"
    adm["srv"].identifica_a = "V01"
    assert identificar(adm["c"]).get_json()["resultado"] == "permitido"


def test_modo_b_con_clave_y_tres_fallos_bloquea_al_usuario(adm):
    adm["registrar"]("V01", CLAVE)
    c = adm["c"]
    adm["srv"].identifica_a = "V01"
    j = identificar(c).get_json()
    assert j["resultado"] == "requiere_clave" and "V01" not in j["motivo"]    # no se revela el seudónimo antes de la clave
    clave(c, j["token"], "incorrecta-1")
    for k in range(CFG.BLOQUEO_FALLOS - 1):
        ip = {"REMOTE_ADDR": f"10.0.1.{k}"}                                    # IP distinta para no caer en el bloqueo por IP
        clave(c, identificar(c, environ_base=ip).get_json()["token"], "incorrecta", environ_base=ip)
    assert verificar(c, "V01").status_code == 429                               # usuario bloqueado (también en el modo A)
    r = identificar(c, environ_base={"REMOTE_ADDR": "10.0.2.1"})
    assert r.status_code == 429 and "V01" not in r.get_json()["motivo"]


def test_modo_b_clave_correcta_saluda(adm):
    adm["registrar"]("V01", CLAVE)
    adm["srv"].identifica_a = "V01"
    tok = identificar(adm["c"]).get_json()["token"]
    j = clave(adm["c"], tok, CLAVE).get_json()
    assert j["resultado"] == "permitido" and j["motivo"] == "Hola, V01."


def test_admin_cambiar_y_quitar_clave(adm):
    adm["registrar"]("V01")
    c = adm["c"]
    assert c.post("/admin/api/clave", json={"id": "V01", "accion": "cambiar", "clave": "corta"}).status_code == 400
    assert c.post("/admin/api/clave", json={"id": "V01", "accion": "cambiar", "clave": CLAVE}).get_json()["requiere_clave"]
    assert verificar(c, "V01").get_json()["resultado"] == "requiere_clave"
    assert c.post("/admin/api/clave", json={"id": "V01", "accion": "quitar"}).get_json()["requiere_clave"] is False
    assert adm["alm"].meta("V01")["clave_hash"] is None
    assert verificar(c, "V01").get_json()["resultado"] == "permitido"


def test_registro_de_pruebas_lleva_modo_y_no_la_clave(adm):
    adm["registrar"]("V01", CLAVE)
    c = adm["c"]
    clave(c, verificar(c, "V01").get_json()["token"], CLAVE)
    adm["srv"].identifica_a = "V01"
    clave(c, identificar(c).get_json()["token"], CLAVE)
    txt = (adm["alm"].dir / "registro_pruebas.csv").read_text(encoding="utf-8")
    assert ",A," in txt and ",B," in txt and ",clave," in txt and CLAVE not in txt


# ------------------------------------------------------------------ modo público
def test_publico_tiene_los_tres_modos_y_no_la_administracion(tmp_path):
    from app.almacen import Almacen
    from app.intentos import ControlIntentos
    from app.main import create_app
    from conftest import ServicioDoble
    alm = Almacen(tmp_path / "privado")
    alm.guardar("V01", [1.0] * 512, {"id": "V01", "requiere_clave": True, "clave_hash": K.hashear(CLAVE)})
    srv = ServicioDoble(alm)
    srv.identifica_a = "V01"
    app = create_app(srv, alm, ControlIntentos(alm.dir), modo_publico=True, clave_publica="pub-123456")
    c = app.test_client()
    h = {"Authorization": "Basic " + base64.b64encode(b"demo:pub-123456").decode()}
    j = c.post("/api/verificar", json={"usuario": "V01", "fotogramas": CINCO}, headers=h).get_json()
    assert j["resultado"] == "requiere_clave"
    assert c.post("/api/clave", json={"token": j["token"], "clave": CLAVE}, headers=h).get_json()["resultado"] == "permitido"
    j = c.post("/api/identificar", json={"fotogramas": CINCO}, headers=h).get_json()
    assert j["resultado"] == "requiere_clave"
    for ruta in ("/admin/api/clave", "/admin/api/registrar", "/admin/api/eliminar", "/admin/api/desbloquear"):
        assert c.post(ruta, json={"id": "V01", "accion": "quitar"}, headers=h).status_code == 404
    assert c.post("/api/identificar", json={"fotogramas": CINCO}).status_code == 401


def test_acerca_explica_modos_y_limitacion_1n(entorno_app):
    html = entorno_app["c"].get("/acerca").get_data(as_text=True)
    assert "Solo cámara" in html and "no fue evaluado en el Sprint 2" in html
    assert "crece con el número de usuarios" in html and "scrypt" in html
