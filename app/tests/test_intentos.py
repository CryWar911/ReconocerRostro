"""Control de intentos: bloqueo por denegados, tope general, desbloqueo y registro (con reloj simulado)."""
import csv

from app.intentos import ControlIntentos
from conftest import Reloj


def nuevo(tmp_path, **kw):
    r = Reloj()
    return ControlIntentos(tmp_path, reloj=r, fallos=3, bloqueo_seg=60, tope=10, ventana=300, pausa=30, **kw), r


def filas(ctl):
    with open(ctl.f_registro, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_tres_denegados_bloquean(tmp_path):
    ctl, _ = nuevo(tmp_path)
    for _ in range(2):
        assert not ctl.anotar("V01", "denegado")["bloqueado_ahora"]
    assert ctl.anotar("V01", "denegado")["bloqueado_ahora"]
    e = ctl.comprobar("V01")
    assert e["resultado"] == "bloqueado" and 59 <= e["segundos"] <= 61


def test_bloqueo_expira(tmp_path):
    ctl, r = nuevo(tmp_path)
    for _ in range(3):
        ctl.anotar("V01", "denegado")
    r.t += 61
    assert ctl.comprobar("V01") is None


def test_no_concluyente_no_cuenta_ni_reinicia(tmp_path):
    ctl, _ = nuevo(tmp_path)
    ctl.anotar("V01", "denegado"); ctl.anotar("V01", "denegado")
    for _ in range(5):
        ctl.anotar("V01", "no_concluyente")
    assert ctl.comprobar("V01") is None and ctl.resumen()["V01"]["fallos"] == 2
    assert ctl.anotar("V01", "denegado")["bloqueado_ahora"]


def test_permitido_reinicia(tmp_path):
    ctl, _ = nuevo(tmp_path)
    ctl.anotar("V01", "denegado"); ctl.anotar("V01", "denegado"); ctl.anotar("V01", "permitido")
    ctl.anotar("V01", "denegado"); ctl.anotar("V01", "denegado")
    assert ctl.comprobar("V01") is None


def test_bloqueo_por_usuario(tmp_path):
    ctl, _ = nuevo(tmp_path)
    for _ in range(3):
        ctl.anotar("V01", "denegado")
    assert ctl.comprobar("V02") is None


def test_tope_general_pausa(tmp_path):
    ctl, r = nuevo(tmp_path)
    for k in range(10):
        assert ctl.comprobar("V01") is None
        ctl.anotar("V01", "permitido" if k % 2 else "no_concluyente")
        r.t += 1
    e = ctl.comprobar("V01")
    assert e["resultado"] == "pausa" and e["segundos"] <= 30
    r.t += 31
    assert ctl.comprobar("V01") is None


def test_tope_respeta_ventana(tmp_path):
    ctl, r = nuevo(tmp_path)
    for _ in range(9):
        ctl.anotar("V01", "permitido"); r.t += 40     # 9 intentos repartidos en 360 s > ventana de 300 s
    ctl.anotar("V01", "permitido")
    assert ctl.comprobar("V01") is None


def test_desbloquear(tmp_path):
    ctl, _ = nuevo(tmp_path)
    for _ in range(3):
        ctl.anotar("V01", "denegado")
    ctl.desbloquear("V01")
    assert ctl.comprobar("V01") is None and ctl.resumen()["V01"]["fallos"] == 0


def test_registro_sin_imagenes_y_campos(tmp_path):
    ctl, _ = nuevo(tmp_path)
    ctl.anotar("V01", "permitido")
    ctl.anotar("V01", "denegado", "El rostro no coincide")
    ctl.anotar("V01", "no_concluyente", "No se detectó ningún rostro")
    f = filas(ctl)
    assert [x["resultado"] for x in f] == ["denegado", "no_concluyente"]   # los permitidos no se registran
    assert set(f[0]) == {"fecha_hora", "usuario_solicitado", "resultado", "motivo"}
    assert all(x["usuario_solicitado"] == "V01" for x in f)


def test_estado_persiste_tras_reinicio(tmp_path):
    ctl, r = nuevo(tmp_path)
    for _ in range(3):
        ctl.anotar("V01", "denegado")
    ctl2 = ControlIntentos(tmp_path, reloj=r, fallos=3, bloqueo_seg=60, tope=10, ventana=300, pausa=30)
    assert ctl2.comprobar("V01")["resultado"] == "bloqueado"
