"""Validador del video y del CSV de anotaciones (src.validar_video): sin modelo ni métricas."""
import cv2
import numpy as np
import pytest

from app.almacen import Almacen
from src.validar_video import main, validar


@pytest.fixture
def entorno(tmp_path):
    vid = tmp_path / "video.mp4"
    w = cv2.VideoWriter(str(vid), cv2.VideoWriter_fourcc(*"mp4v"), 30, (640, 480))
    for _ in range(30 * 20):                      # 20 s a 30 fps
        w.write(np.full((480, 640, 3), 90, np.uint8))
    w.release()
    alm = Almacen(tmp_path / "privado")
    for u in ("V01", "V02"):
        alm.guardar(u, np.ones(512, np.float32), {"id": u})
    return tmp_path, vid, alm.dir


def csv(tmp_path, texto, nombre="anot.csv"):
    p = tmp_path / nombre
    p.write_text(texto, encoding="utf-8")
    return p


def test_csv_valido(entorno, capsys):
    tmp, vid, datos = entorno
    a = csv(tmp, "inicio_s,fin_s,identidad,condicion\n0,8,V01,frente\n8.5,15,V02,frente\n15.5,19.5,no registrado A,frente\n")
    r = validar(vid, a, datos)
    assert r["errores"] == []
    assert r["video"]["ancho"] == 640 and abs(r["video"]["duracion_s"] - 20) < 0.2
    assert list(r["tramos"].ventanas) == [16, 13, 8]       # 30 fps, 1 de cada 3, ventanas de 5
    assert main(["--video", str(vid), "--anotaciones", str(a), "--almacen-app", str(datos)]) == 0
    assert "VÁLIDO" in capsys.readouterr().out


def test_detecta_todos_los_errores(entorno):
    tmp, vid, datos = entorno
    a = csv(tmp, "inicio_s,fin_s,identidad\n"
                 "0,8,V01\n"                 # ok
                 "7,12,V02\n"                # se solapa con la anterior
                 "12,11,V01\n"               # fin <= inicio
                 "13,25,no registrado A\n"   # se sale del video (20 s)
                 "x,14,V01\n"                # no es número
                 "14,14.3,V01\n"             # demasiado corto para una ventana
                 "15,18,V07\n")              # no registrado en la app
    r = validar(vid, a, datos)
    texto = " | ".join(r["errores"])
    assert "se solapan" in texto and "no es mayor" in texto and "el video dura" in texto
    assert "no es un número" in texto and "demasiado corto" in texto and "'V07' no está registrado" in texto
    assert main(["--video", str(vid), "--anotaciones", str(a), "--almacen-app", str(datos)]) == 1


def test_columnas_y_archivos(entorno):
    tmp, vid, datos = entorno
    assert "Faltan columnas" in validar(vid, csv(tmp, "inicio,fin,persona\n0,1,V01\n"), datos)["errores"][0]
    assert "No se puede abrir el video" in validar(tmp / "no_existe.mp4", csv(tmp, "inicio_s,fin_s,identidad\n0,5,V01\n"), datos)["errores"][0]


def test_avisos_sin_no_registrados_y_usuario_sin_tramo(entorno):
    tmp, vid, datos = entorno
    r = validar(vid, csv(tmp, "inicio_s,fin_s,identidad\n0,10,V01\n"), datos)
    assert r["errores"] == []
    av = " | ".join(r["avisos"])
    assert "no registrado" in av and "['V02']" in av


def test_no_toca_el_almacen(entorno):
    tmp, vid, datos = entorno
    antes = sorted((p.name, p.stat().st_mtime_ns) for p in datos.rglob("*") if p.is_file())
    validar(vid, csv(tmp, "inicio_s,fin_s,identidad\n0,10,V01\n"), datos)
    assert sorted((p.name, p.stat().st_mtime_ns) for p in datos.rglob("*") if p.is_file()) == antes


def test_rechaza_rutas_del_repositorio(root):
    r = validar(root / "docs" / "x.mp4", root / "docs" / "x.csv")
    assert r["errores"] and "repositorio" in r["errores"][0]
