"""ENSAYO de extremo a extremo con el modelo real y fotos del conjunto de datos (no son voluntarios).

Simula la cámara: fotos sin recortar (Original Images) de identidades REGISTRADAS, encuadradas en 640x480 y
codificadas en JPEG, enviadas a /api/verificar como lo hace el navegador. No es una evaluación del modelo
(eso fue la tarea 2.5); solo comprueba que la app funciona de punta a punta. Se usan fotos de VALIDACIÓN.
"""
import base64

import cv2
import numpy as np
import pytest

pytestmark = pytest.mark.lento


def marco(img_rgb, w=640, h=480):
    s = min(w / img_rgb.shape[1], h / img_rgb.shape[0])
    im = cv2.resize(img_rgb, (int(img_rgb.shape[1] * s), int(img_rgb.shape[0] * s)), interpolation=cv2.INTER_AREA)
    out = np.full((h, w, 3), 40, np.uint8)
    y, x = (h - im.shape[0]) // 2, (w - im.shape[1]) // 2
    out[y:y + im.shape[0], x:x + im.shape[1]] = im
    return out


def a_b64(rgb):
    ok, buf = cv2.imencode(".jpg", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode()


@pytest.fixture(scope="module")
def entorno(tmp_path_factory):
    from app import config as CFG
    if not (CFG.PAQUETE_MODELO / "red.ts").exists():
        pytest.skip("Falta el paquete del modelo en models/")
    from src import config as SC, data as D
    if not SC.CSV_PATH.exists():
        pytest.skip("Falta el dataset en data/raw/")
    from app.almacen import Almacen
    from app.intentos import ControlIntentos
    from app.main import create_app
    from app.servicio import ServicioVerificacion
    alm = Almacen(tmp_path_factory.mktemp("privado_e2e"))   # no toca la carpeta privada real
    app = create_app(ServicioVerificacion(almacen=alm), alm, ControlIntentos(alm.dir))
    srv = app.servicio
    sp = D.load_split_table()
    va = sp[(sp.split == "val") & (sp.role == "registrada")]

    def fotos(persona, n=5):
        """n fotos de validación de la persona en las que el detector ve un único rostro claro."""
        out = []
        for f in va[va.person == persona].filename:
            img = marco(D.read_rgb(SC.ORIGINALS_DIR / persona / f))
            estado, _ = srv.analizar(img)
            if estado == "valido":
                out.append(img)
            if len(out) == n:
                return out
        pytest.skip(f"No hay {n} fotos válidas de {persona}")

    return app.test_client(), fotos


def verificar(c, usuario, imgs):
    r = c.post("/api/verificar", json={"usuario": usuario, "fotogramas": [a_b64(i) for i in imgs]})
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    print(f"ENSAYO {usuario}: {j['resultado']} | {j['estados']} | servidor {j['segundos_servidor']} s")
    return j


def test_registrado_aceptado(entorno):
    c, fotos = entorno
    assert verificar(c, "Brad Pitt", fotos("Brad Pitt"))["resultado"] == "permitido"


def test_registrado_con_nombre_de_otro_denegado(entorno):
    c, fotos = entorno
    assert verificar(c, "Tom Cruise", fotos("Brad Pitt"))["resultado"] == "denegado"


def test_camara_tapada_no_concluyente(entorno):
    c, _ = entorno
    j = verificar(c, "Brad Pitt", [np.zeros((480, 640, 3), np.uint8)] * 5)
    assert j["resultado"] == "no_concluyente" and set(j["estados"]) == {"sin_rostro"}


def test_dos_personas_no_concluyente(entorno):
    c, fotos = entorno
    a, b = fotos("Brad Pitt", 3), fotos("Zac Efron", 3)
    dobles = [np.hstack([cv2.resize(x, (320, 480)), cv2.resize(y, (320, 480))]) for x, y in zip(a, b)]
    j = verificar(c, "Brad Pitt", dobles + dobles[:2])
    assert j["resultado"] == "no_concluyente" and "varios_rostros" in j["estados"]


def test_muy_oscuro_no_concluyente(entorno):
    c, fotos = entorno
    oscuras = [(i.astype(np.float32) * 0.12).astype(np.uint8) for i in fotos("Brad Pitt")]
    j = verificar(c, "Brad Pitt", oscuras)
    assert j["resultado"] == "no_concluyente"


def test_registro_y_verificacion_de_un_usuario_nuevo(entorno, monkeypatch):
    """ENSAYO: Hugh Jackman (sin plantilla entre las 24) se registra como ENSAYO_V01 con 12 fotos y luego verifica
    con otras 5 fotos distintas. Otra persona que elige ENSAYO_V01 es denegada."""
    import datetime as dt
    from src import config as SC, data as D
    c, fotos = entorno
    monkeypatch.setenv("FACEID_ADMIN_PASSWORD", "ensayo")
    assert c.post("/admin/entrar", data={"clave": "ensayo"}).status_code == 302
    sp = D.load_split_table()
    hj = sp[sp.person == "Hugh Jackman"].sort_values("filename")
    grupos = list(dict.fromkeys(hj.group_id))
    reg = [hj[hj.group_id == g].filename.iloc[0] for g in grupos[:12]]
    ver = [hj[hj.group_id == g].filename.iloc[0] for g in grupos[12:30]]
    leer = lambda f: marco(D.read_rgb(SC.ORIGINALS_DIR / "Hugh Jackman" / f))
    r = c.post("/admin/api/registrar", json={"id": "ENSAYO_V01", "autorizacion": True, "fecha_autorizacion": dt.date.today().isoformat(),
                                              "fotos": [a_b64(leer(f)) for f in reg]})
    assert r.status_code == 200, r.get_json()
    print("ENSAYO registro:", r.get_json())
    srv = c.application.servicio
    validas = [im for im in map(leer, ver) if srv.analizar(im)[0] == "valido"][:5]
    assert len(validas) == 5
    assert verificar(c, "ENSAYO_V01", validas)["resultado"] == "permitido"
    assert verificar(c, "ENSAYO_V01", fotos("Brad Pitt"))["resultado"] == "denegado"
    assert c.post("/admin/api/eliminar", json={"id": "ENSAYO_V01"}).status_code == 200


def test_modo_b_identifica_entre_usuarios_registrados(entorno, monkeypatch):
    """ENSAYO 1:N con el modelo real: Hugh Jackman (ENSAYO_V01) y Natalie Portman (ENSAYO_V02) se registran con 12 fotos;
    con otras fotos de Hugh Jackman el modo B lo identifica; Brad Pitt (no registrado en la app) no es identificado."""
    import datetime as dt
    from src import config as SC, data as D
    c, fotos = entorno
    monkeypatch.setenv("FACEID_ADMIN_PASSWORD", "ensayo")
    assert c.post("/admin/entrar", data={"clave": "ensayo"}).status_code == 302
    sp = D.load_split_table()
    srv = c.application.servicio

    def grupos(persona):
        g = sp[sp.person == persona].sort_values("filename")
        return [g[g.group_id == x].filename.iloc[0] for x in dict.fromkeys(g.group_id)]

    def leer(persona, f):
        return marco(D.read_rgb(SC.ORIGINALS_DIR / persona / f))

    reservadas = {}
    for uid, persona in [("ENSAYO_V01", "Hugh Jackman"), ("ENSAYO_V02", "Natalie Portman")]:
        gs = grupos(persona)
        r = c.post("/admin/api/registrar", json={"id": uid, "autorizacion": True, "fecha_autorizacion": dt.date.today().isoformat(),
                                                  "fotos": [a_b64(leer(persona, f)) for f in gs[:12]]})
        assert r.status_code == 200, r.get_json()
        reservadas[uid] = [im for im in (leer(persona, f) for f in gs[12:30]) if srv.analizar(im)[0] == "valido"][:5]
    j = c.post("/api/identificar", json={"fotogramas": [a_b64(i) for i in reservadas["ENSAYO_V01"]]}).get_json()
    print("ENSAYO 1:N Hugh Jackman ->", j["resultado"], j["motivo"])
    assert j["resultado"] == "permitido" and j["motivo"] == "Hola, ENSAYO_V01."
    j = c.post("/api/identificar", json={"fotogramas": [a_b64(i) for i in fotos("Brad Pitt")]}).get_json()
    print("ENSAYO 1:N Brad Pitt (no registrado en la app) ->", j["resultado"])
    assert j["resultado"] == "no_identificado"
    for uid in reservadas:
        c.post("/admin/api/eliminar", json={"id": uid})
