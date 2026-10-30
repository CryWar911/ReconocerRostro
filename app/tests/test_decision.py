"""Reglas de decisión y votación (sin modelo)."""
from app import config as CFG
from app import decision as D

U = CFG.UMBRAL_OFICIAL


def dec(estados, punt):
    return D.decidir(estados, punt, U, CFG.MIN_VOTOS, CFG.MIN_VALIDOS)


def test_cinco_validos_cinco_votos_permitido():
    r = dec(["valido"] * 5, [0.8] * 5)
    assert r["resultado"] == D.PERMITIDO and r["titulo"] == "Acceso permitido"


def test_tres_votos_de_cinco_permitido():
    assert dec(["valido"] * 5, [0.8, 0.7, 0.6, 0.3, 0.2])["resultado"] == D.PERMITIDO


def test_dos_votos_de_cinco_denegado():
    r = dec(["valido"] * 5, [0.8, 0.7, 0.3, 0.3, 0.2])
    assert r["resultado"] == D.DENEGADO and r["titulo"] == "Acceso denegado"


def test_umbral_exacto_cuenta_como_voto():
    assert dec(["valido"] * 5, [U, U, U, 0.0, 0.0])["resultado"] == D.PERMITIDO


def test_justo_debajo_del_umbral_no_vota():
    eps = 1e-6
    assert dec(["valido"] * 5, [U - eps] * 5)["resultado"] == D.DENEGADO


def test_menos_de_tres_validos_no_concluyente():
    r = dec(["valido", "valido", "sin_rostro", "sin_rostro", "borroso"], [0.9, 0.9, None, None, None])
    assert r["resultado"] == D.NO_CONCLUYENTE
    assert r["titulo"] == "No se pudo verificar de forma confiable"
    assert "ningún rostro" in r["motivo"] and "2 de 5" in r["motivo"]


def test_tres_validos_con_votos_permitido_aunque_haya_fallos():
    assert dec(["valido", "valido", "valido", "oscuro", "sin_rostro"], [0.9, 0.9, 0.9, None, None])["resultado"] == D.PERMITIDO


def test_tres_validos_sin_votos_suficientes_denegado():
    assert dec(["valido", "valido", "valido", "oscuro", "sin_rostro"], [0.9, 0.9, 0.1, None, None])["resultado"] == D.DENEGADO


def test_camara_tapada_no_concluyente():
    r = dec(["sin_rostro"] * 5, [None] * 5)
    assert r["resultado"] == D.NO_CONCLUYENTE and r["validos"] == 0


def test_motivo_varios_rostros():
    r = dec(["varios_rostros"] * 4 + ["valido"], [None] * 4 + [0.9])
    assert r["resultado"] == D.NO_CONCLUYENTE and "más de un rostro" in r["motivo"]


def test_respuesta_no_incluye_puntuaciones():
    r = dec(["valido"] * 5, [0.81, 0.82, 0.83, 0.84, 0.85])
    texto = repr(r)
    assert "0.81" not in texto and "0.85" not in texto


def test_calidad():
    assert D.clasificar_calidad(500, 120, 150, CFG) == "valido"
    assert D.clasificar_calidad(5, 120, 150, CFG) == "borroso"
    assert D.clasificar_calidad(500, 20, 150, CFG) == "oscuro"
    assert D.clasificar_calidad(500, 240, 150, CFG) == "sobreexpuesto"
    assert D.clasificar_calidad(500, 120, 30, CFG) == "lejos"


def test_varios_rostros():
    assert not D.hay_varios_rostros([0.99], [10000], CFG)
    assert D.hay_varios_rostros([0.99, 0.98], [10000, 6000], CFG)
    assert not D.hay_varios_rostros([0.99, 0.98], [10000, 1000], CFG)    # cara pequeña al fondo
    assert not D.hay_varios_rostros([0.99, 0.91], [10000, 9000], CFG)    # segunda cara dudosa
