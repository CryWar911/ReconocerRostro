"""Administración (HU10, HU11): registrar usuarios de la demostración, eliminarlos y desbloquearlos.

La contraseña viene de FACEID_ADMIN_PASSWORD (nunca del código ni de git). Sin ella, la administración
queda deshabilitada. Registrar exige la casilla de autorización escrita firmada y su fecha.
"""
import csv
import datetime as dt
import hmac
import re
import time
from functools import wraps

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

from . import claves as K
from . import config as CFG


class ErrorRegistro(ValueError):
    pass


def registrar_admin(carpeta, accion, uid):
    f = carpeta / "registro_admin.csv"
    nuevo = not f.exists()
    with open(f, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if nuevo:
            w.writerow(["fecha_hora", "accion", "usuario"])
        w.writerow([time.strftime("%Y-%m-%d %H:%M:%S"), accion, uid])


def registrar_usuario(servicio, almacen, datos, decodificar):
    """Valida la petición, calcula la plantilla (media renormalizada de embeddings) y la guarda.
    Las fotos se descartan salvo que datos['conservar_fotos'] sea True."""
    uid = str(datos.get("id") or "").strip()
    if not re.fullmatch(CFG.ID_PATRON, uid):
        raise ErrorRegistro("El seudónimo debe tener de 1 a 32 letras, números, '_' o '-' (por ejemplo V01).")
    if uid in {u for u, _ in servicio.usuarios()}:
        raise ErrorRegistro(f"Ya existe un usuario '{uid}'.")
    if datos.get("autorizacion") is not True:
        raise ErrorRegistro("No se puede registrar sin la autorización escrita firmada.")
    try:
        fecha = dt.date.fromisoformat(str(datos.get("fecha_autorizacion")))
    except ValueError:
        raise ErrorRegistro("Indique la fecha de la autorización escrita (AAAA-MM-DD).")
    if fecha > dt.date.today():
        raise ErrorRegistro("La fecha de la autorización no puede ser futura.")
    seguridad = datos.get("seguridad", "solo_rostro")
    if seguridad not in ("solo_rostro", "rostro_clave"):
        raise ErrorRegistro("Opción de seguridad no válida.")
    clave_hash = None
    if seguridad == "rostro_clave":
        try:
            clave_hash = K.hashear(datos.get("clave"))      # solo se guarda el hash scrypt con sal
        except K.ErrorClave as e:
            raise ErrorRegistro(str(e))
    fotos = datos.get("fotos") or []
    if not CFG.REGISTRO_MIN_FOTOS <= len(fotos) <= CFG.REGISTRO_MAX_FOTOS:
        raise ErrorRegistro(f"Se necesitan entre {CFG.REGISTRO_MIN_FOTOS} y {CFG.REGISTRO_MAX_FOTOS} fotos; llegaron {len(fotos)}.")
    try:
        decod = [decodificar(f, con_bytes=True) for f in fotos]
    except ValueError as e:
        raise ErrorRegistro(str(e))
    with servicio.lock:
        analisis = [servicio.analizar(img) for img, _ in decod]
    crops = [c for _, c in analisis if c is not None]
    if len(crops) < CFG.REGISTRO_MIN_VALIDAS:
        malos = {}
        for e, _ in analisis:
            if e != "valido":
                malos[e] = malos.get(e, 0) + 1
        raise ErrorRegistro(f"Solo {len(crops)} de {len(fotos)} fotos tienen un rostro válido (se necesitan "
                            f"{CFG.REGISTRO_MIN_VALIDAS}). Problemas: {malos}. Repita con mejor luz y de frente.")
    E = servicio.embeddings(crops).cpu().numpy()
    plantilla = E.mean(0)
    conservar = datos.get("conservar_fotos") is True
    meta = {"id": uid, "autorizacion_escrita": True, "fecha_autorizacion": fecha.isoformat(),
            "fecha_registro": time.strftime("%Y-%m-%d %H:%M:%S"), "n_fotos": len(fotos), "n_fotos_validas": len(crops),
            "fotos_conservadas": conservar, "plantilla": "media renormalizada de embeddings FaceNet (como en la tarea 2.2)",
            "requiere_clave": clave_hash is not None, "clave_hash": clave_hash}
    almacen.guardar(uid, plantilla, meta, [raw for _, raw in decod] if conservar else None)
    del decod, crops, fotos
    return {"id": uid, "n_fotos": meta["n_fotos"], "n_fotos_validas": meta["n_fotos_validas"], "fotos_conservadas": conservar,
            "requiere_clave": clave_hash is not None}


def purgar_registro(f, uid):
    """Quita del registro de intentos las filas de un usuario eliminado."""
    if not f.exists():
        return
    with open(f, encoding="utf-8") as fh:
        filas = list(csv.DictReader(fh))
    if not filas:
        return
    with open(f, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows([r for r in filas if r["usuario_solicitado"] != uid])


def crear_blueprint():
    from .publico import Limitador
    bp = Blueprint("admin", __name__, url_prefix="/admin")
    # Por `tailscale serve` todas las peticiones llegan desde 127.0.0.1: el límite es global, no por IP.
    fallos = Limitador(CFG.ADMIN_FALLOS_MAX, CFG.ADMIN_FALLOS_VENTANA_SEG)
    bp.fallos_admin = fallos

    def requiere_admin(api=False):
        def deco(f):
            @wraps(f)
            def w(*a, **k):
                if not session.get("admin"):
                    return (jsonify({"error": "Sesión de administrador requerida."}), 401) if api else redirect(url_for("admin.panel"))
                return f(*a, **k)
            return w
        return deco

    @bp.get("/")
    def panel():
        app = current_app
        if not session.get("admin"):
            return render_template("admin_login.html", habilitado=CFG.admin_password() is not None)
        demo = [app.almacen.meta(u) for u in app.almacen.usuarios()]
        estados = {u: e for u, e in app.control.resumen().items() if e["fallos"] or e["bloqueado_seg"] or e["pausa_seg"]}
        return render_template("admin_panel.html", demo=demo, estados=estados,
                               registros=app.control.ultimos_registros(20), cfg=CFG, carpeta=str(app.almacen.dir))

    @bp.post("/entrar")
    def entrar():
        clave = CFG.admin_password()
        if fallos.excedido("admin"):
            return render_template("admin_login.html", habilitado=clave is not None,
                                   error=f"Demasiadas contraseñas incorrectas. Espere {fallos.espera('admin')} s."), 429
        dada = request.form.get("clave", "")
        if clave is None or not hmac.compare_digest(dada.encode(), clave.encode()):
            fallos.anotar("admin")
            time.sleep(1)   # frena los intentos de adivinar la contraseña
            return render_template("admin_login.html", habilitado=clave is not None, error="Contraseña incorrecta."), 401
        session["admin"] = True
        return redirect(url_for("admin.panel"))

    @bp.post("/salir")
    def salir():
        session.clear()
        return redirect(url_for("inicio"))

    @bp.get("/registrar")
    @requiere_admin()
    def registrar_pagina():
        return render_template("admin_registrar.html", cfg=CFG, hoy=dt.date.today().isoformat())

    @bp.post("/api/registrar")
    @requiere_admin(api=True)
    def api_registrar():
        from .main import decodificar_jpeg
        app = current_app
        try:
            r = registrar_usuario(app.servicio, app.almacen, request.get_json(silent=True) or {}, decodificar_jpeg)
        except ErrorRegistro as e:
            return jsonify({"error": str(e)}), 400
        app.control.olvidar(r["id"])
        registrar_admin(app.almacen.dir, "registro", r["id"])
        return jsonify(r)

    @bp.post("/api/eliminar")
    @requiere_admin(api=True)
    def api_eliminar():
        app = current_app
        uid = (request.get_json(silent=True) or {}).get("id", "")
        if not app.almacen.eliminar(uid):
            return jsonify({"error": "No existe ese usuario de demostración."}), 404
        app.control.olvidar(uid)
        purgar_registro(app.control.f_registro, uid)
        registrar_admin(app.almacen.dir, "eliminacion (plantilla, metadatos, fotos e intentos)", uid)
        return jsonify({"eliminado": uid})

    @bp.post("/api/desbloquear")
    @requiere_admin(api=True)
    def api_desbloquear():
        app = current_app
        uid = (request.get_json(silent=True) or {}).get("id", "")
        if uid not in {u for u, _ in app.servicio.usuarios()} and uid not in app.control.resumen():
            return jsonify({"error": "Usuario desconocido."}), 404
        app.control.desbloquear(uid)
        registrar_admin(app.almacen.dir, "desbloqueo", uid)
        return jsonify({"desbloqueado": uid})

    @bp.post("/api/clave")
    @requiere_admin(api=True)
    def api_clave():
        """Cambiar o quitar la palabra clave de un usuario de la demo. La clave nunca se registra ni se devuelve."""
        app = current_app
        d = request.get_json(silent=True) or {}
        uid, accion = d.get("id", ""), d.get("accion")
        if uid not in app.almacen.usuarios():
            return jsonify({"error": "No existe ese usuario de demostración."}), 404
        meta = app.almacen.meta(uid)
        if accion == "cambiar":
            try:
                meta.update(requiere_clave=True, clave_hash=K.hashear(d.get("clave")))
            except K.ErrorClave as e:
                return jsonify({"error": str(e)}), 400
        elif accion == "quitar":
            meta.update(requiere_clave=False, clave_hash=None)
        else:
            return jsonify({"error": "Acción no válida."}), 400
        app.almacen.actualizar_meta(uid, meta)
        registrar_admin(app.almacen.dir, "palabra clave cambiada" if accion == "cambiar" else "palabra clave quitada", uid)
        return jsonify({"id": uid, "requiere_clave": meta["requiere_clave"]})

    return bp
