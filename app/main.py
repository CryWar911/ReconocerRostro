"""Aplicación web local de inicio de sesión por verificación facial 1 a 1 (Sprint 3, fase 6 de CRISP-DM).

Backend: Flask (el más sencillo para unas pocas rutas y plantillas HTML). Escucha solo en 127.0.0.1.
Las imágenes llegan como JPEG en base64, se decodifican en memoria y se descartan al terminar la petición.
"""
import base64
import binascii
import os
import re
import time

import cv2
import numpy as np
from flask import Flask, jsonify, render_template, request

from . import config as CFG


def decodificar_jpeg(data_url, con_bytes=False):
    """'data:image/jpeg;base64,...' -> imagen RGB uint8 (solo en memoria). Con con_bytes devuelve también el JPEG."""
    if not isinstance(data_url, str) or "," not in data_url:
        raise ValueError("fotograma con formato no válido")
    try:
        raw = base64.b64decode(data_url.split(",", 1)[1], validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("fotograma con base64 no válido")
    img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("fotograma que no es una imagen")
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return (rgb, raw) if con_bytes else rgb


def comprobar_puerto(publico, puerto):
    """La instancia con administración nunca puede ocupar el puerto al que apunta el túnel de Cloudflare."""
    if not publico and int(puerto) == CFG.PUERTO_PUBLICO:
        raise RuntimeError(f"La instancia de administración no puede usar el puerto {CFG.PUERTO_PUBLICO} (el del túnel). "
                           f"Use FACEID_PUERTO={CFG.PUERTO_ADMIN} o arranque la pública con FACEID_MODO_PUBLICO=1.")


def create_app(servicio=None, almacen=None, control=None, modo_pruebas=None, modo_publico=None, clave_publica=None):
    """servicio/almacen/control se pueden inyectar en las pruebas; si son None se crean los reales.
    modo_pruebas (por defecto FACEID_MODO_PRUEBAS=1): registra todos los intentos con su caso y tiempos (tarea 3.4).
    modo_publico (por defecto FACEID_MODO_PUBLICO=1): instancia para el túnel; solo verificación (sin rutas de
    administración), autenticación básica (FACEID_ACCESO_PUBLICO) y límite por IP real (ver publico.py)."""
    publico = CFG.MODO_PUBLICO if modo_publico is None else modo_publico
    if publico and not (clave_publica or CFG.acceso_publico()):
        raise RuntimeError("Modo público sin contraseña: defina FACEID_ACCESO_PUBLICO antes de arrancar.")
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = CFG.MAX_BYTES_PETICION
    app.secret_key = os.urandom(32)          # sesión de administrador válida solo mientras corre el servidor
    app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
    if almacen is None:
        from .almacen import Almacen
        almacen = Almacen()
    if servicio is None:
        from .servicio import ServicioVerificacion
        servicio = ServicioVerificacion(almacen=almacen)
    if control is None:
        from .intentos import ControlIntentos
        control = ControlIntentos(almacen.dir)
    app.servicio, app.almacen, app.control = servicio, almacen, control
    app.modo_pruebas = CFG.MODO_PRUEBAS if modo_pruebas is None else modo_pruebas
    app.modo_publico = publico
    app.jinja_env.globals["modo_publico"] = publico
    # Modo explicación (exposición): solo en la instancia local; muestra puntuaciones, nunca en la pública.
    app.explicacion_permitida = (not publico) and CFG.EXPLICACION
    explicaciones = {}      # token del paso 2 -> explicación (se muestra solo al terminar el paso 2)

    from .claves import comprobar as comprobar_clave
    from .pendientes import Pendientes
    from .publico import ip_real
    pendientes = Pendientes()
    app.pendientes = pendientes

    def requiere_clave(u):
        """True si el usuario de la app fue registrado con 'rostro + palabra clave'."""
        if not almacen or u not in almacen.usuarios():
            return False
        m = almacen.meta(u)
        return bool(m.get("requiere_clave") and m.get("clave_hash"))

    def n_app():
        return len(almacen.usuarios()) if almacen else 0

    @app.get("/")
    def inicio():
        us = servicio.usuarios()
        return render_template("index.html", demo=[u for u, g in us if g == "demo"], dataset=[u for u, g in us if g == "dataset"],
                               n=CFG.N_FOTOGRAMAS, modo_pruebas=app.modo_pruebas, n_app=n_app(),
                               explicacion=app.explicacion_permitida)

    @app.get("/acerca")
    def acerca():
        return render_template("acerca.html", cfg=CFG)

    @app.get("/api/usuarios")
    def api_usuarios():
        return jsonify([{"id": u, "grupo": g} for u, g in servicio.usuarios()])

    # ------------------------------------------------------------------ utilidades comunes
    def leer_peticion(datos):
        caso = str(datos.get("caso") or "").strip()[:20]
        if not re.fullmatch(r"[A-Za-z0-9_\-]*", caso):
            caso = ""
        try:
            seg_captura = float(datos.get("segundos_captura") or 0.0)
        except (TypeError, ValueError):
            seg_captura = 0.0
        return caso, seg_captura

    def anotar_prueba(t0, modo, caso, usuario, resultado, motivo, estados=(), validos="", seg_servidor="", seg_captura=0.0):
        """Modo pruebas: registra el intento (nunca la palabra clave ni puntuaciones)."""
        if not app.modo_pruebas:
            return None
        return control.registrar_prueba({"modo": modo, "caso": caso, "usuario_solicitado": usuario, "resultado": resultado,
                                         "motivo": motivo, "estados": " ".join(estados), "validos": validos,
                                         "segundos_captura": f"{seg_captura:.3f}", "segundos_servidor": seg_servidor,
                                         "segundos_peticion": f"{time.perf_counter() - t0:.3f}"})

    def texto_espera(espera, titulo_bloqueo, motivo_bloqueo):
        if espera["resultado"] == "bloqueado":
            return titulo_bloqueo, motivo_bloqueo.replace("{s}", str(espera["segundos"]))
        return "Demasiados intentos", f"Se alcanzó el máximo de intentos en poco tiempo. Espere {espera['segundos']} s."

    def quiere_explicacion(datos):
        return app.explicacion_permitida and bool(datos.get("explicar"))

    def con_explicacion(respuesta, r):
        if "explicacion" in r:
            respuesta["explicacion"] = r["explicacion"]
        return respuesta

    def decodificar_fotos(fotos):
        if len(fotos) != CFG.N_FOTOGRAMAS:
            raise ValueError(f"Se esperaban {CFG.N_FOTOGRAMAS} fotogramas y llegaron {len(fotos)}.")
        return [decodificar_jpeg(f) for f in fotos]

    def pedir_clave(r, token, t0, idp):
        # La explicación se guarda y se entrega tras el paso 2: antes revelaría si el rostro coincidió.
        if "explicacion" in r:
            while len(explicaciones) >= 20:                      # pasos abandonados: se descartan los más antiguos
                explicaciones.pop(next(iter(explicaciones)))
            explicaciones[token] = r["explicacion"]
        return jsonify({"resultado": "requiere_clave", "titulo": "Paso 2: palabra clave",
                        "motivo": "Escriba su palabra clave para terminar el inicio de sesión.", "token": token,
                        "estados": r["estados"], "validos": r["validos"], "fotogramas": r["fotogramas"],
                        "segundos_servidor": round(r["segundos_servidor"], 3),
                        "segundos_peticion": round(time.perf_counter() - t0, 3), "id_intento": idp})

    def aviso_bloqueo(bloqueado):
        return (f" Se alcanzaron {CFG.BLOQUEO_FALLOS} intentos denegados seguidos: el usuario queda bloqueado {CFG.BLOQUEO_SEG} s."
                if bloqueado else "")

    # ------------------------------------------------------------------ modo A: nombre + rostro (1 a 1)
    @app.post("/api/verificar")
    def api_verificar():
        t0 = time.perf_counter()
        datos = request.get_json(silent=True) or {}
        usuario = datos.get("usuario")
        fotos = datos.get("fotogramas") or []
        caso, seg_captura = leer_peticion(datos)
        if usuario not in {u for u, _ in servicio.usuarios()}:
            return jsonify({"error": "Usuario no registrado o no seleccionado."}), 400
        if len(fotos) != CFG.N_FOTOGRAMAS:
            return jsonify({"error": f"Se esperaban {CFG.N_FOTOGRAMAS} fotogramas y llegaron {len(fotos)}."}), 400
        espera = control.comprobar(usuario)
        if espera:
            titulo, motivo = texto_espera(espera, "Usuario bloqueado temporalmente",
                                          f"Hubo {CFG.BLOQUEO_FALLOS} intentos denegados seguidos. Espere {{s}} s o avise al administrador.")
            idp = anotar_prueba(t0, "A", caso, usuario, espera["resultado"], motivo, seg_captura=seg_captura)
            return jsonify({"resultado": "bloqueado", "titulo": titulo, "motivo": motivo, "estados": [],
                            "segundos_espera": espera["segundos"], "id_intento": idp}), 429
        try:
            imgs = decodificar_fotos(fotos)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        r = servicio.verificar(usuario, imgs, explicar=True) if quiere_explicacion(datos) else servicio.verificar(usuario, imgs)
        del imgs, fotos  # las imágenes no se guardan
        seg_srv = f"{r['segundos_servidor']:.3f}"
        if r["resultado"] != "no_concluyente" and requiere_clave(usuario):
            # Paso 2 SIEMPRE, también si el rostro no coincide, para no revelar cuál de los dos falló.
            bloqueado = False
            if r["resultado"] == "denegado":
                bloqueado = control.anotar(usuario, "denegado", "rostro no coincide (paso 1 de rostro + clave)")["bloqueado_ahora"]
            tok = pendientes.crear(usuario, r["resultado"] == "permitido", "A", ip_real(request), bloqueado=bloqueado)
            idp = anotar_prueba(t0, "A", caso, usuario, "requiere_clave", "paso 2", r["estados"], r["validos"], seg_srv, seg_captura)
            return pedir_clave(r, tok, t0, idp)
        estado = control.anotar(usuario, r["resultado"], r["motivo"])
        motivo = r["motivo"] + aviso_bloqueo(estado["bloqueado_ahora"])
        idp = anotar_prueba(t0, "A", caso, usuario, r["resultado"], motivo, r["estados"], r["validos"], seg_srv, seg_captura)
        # Respuesta sin puntuaciones ni plantillas
        return jsonify(con_explicacion({"resultado": r["resultado"], "titulo": r["titulo"], "motivo": motivo,
                        "estados": r["estados"], "validos": r["validos"], "fotogramas": r["fotogramas"],
                        "segundos_servidor": round(r["segundos_servidor"], 3),
                        "segundos_peticion": round(time.perf_counter() - t0, 3), "id_intento": idp}, r))

    # ------------------------------------------------------------------ modo B: solo cámara (1:N)
    @app.post("/api/identificar")
    def api_identificar():
        t0 = time.perf_counter()
        datos = request.get_json(silent=True) or {}
        caso, seg_captura = leer_peticion(datos)
        if n_app() == 0:
            return jsonify({"error": "El modo «Solo cámara» está deshabilitado: no hay usuarios registrados en la aplicación."}), 409
        ip = ip_real(request)
        kip, etiqueta = control.clave_ip(ip), "(solo cámara)"
        espera = control.comprobar(kip, etiqueta=etiqueta)
        if espera:
            titulo, motivo = texto_espera(espera, "Bloqueado temporalmente",
                                          f"Hubo {CFG.BLOQUEO_IP_FALLOS} intentos sin identificar seguidos desde este equipo. Espere {{s}} s.")
            idp = anotar_prueba(t0, "B", caso, etiqueta, espera["resultado"], motivo, seg_captura=seg_captura)
            return jsonify({"resultado": "bloqueado", "titulo": titulo, "motivo": motivo, "estados": [],
                            "segundos_espera": espera["segundos"], "id_intento": idp}), 429
        try:
            imgs = decodificar_fotos(datos.get("fotogramas") or [])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        r = servicio.identificar(imgs, explicar=True) if quiere_explicacion(datos) else servicio.identificar(imgs)
        del imgs
        seg_srv = f"{r['segundos_servidor']:.3f}"
        u = r.get("usuario")
        if r["resultado"] == "permitido":
            espera_u = control.comprobar(u)
            if espera_u:
                motivo = f"Inicio de sesión bloqueado temporalmente. Espere {espera_u['segundos']} s o avise al administrador."
                idp = anotar_prueba(t0, "B", caso, etiqueta, espera_u["resultado"], motivo, r["estados"], r["validos"], seg_srv, seg_captura)
                return jsonify({"resultado": "bloqueado", "titulo": "Bloqueado temporalmente", "motivo": motivo,
                                "estados": [], "segundos_espera": espera_u["segundos"], "id_intento": idp}), 429
            if requiere_clave(u):
                tok = pendientes.crear(u, True, "B", ip, clave_ip=kip)
                idp = anotar_prueba(t0, "B", caso, etiqueta, "requiere_clave", "paso 2", r["estados"], r["validos"], seg_srv, seg_captura)
                return pedir_clave(r, tok, t0, idp)       # el seudónimo no se muestra hasta completar la clave
            control.anotar(u, "permitido")
            control.anotar(kip, "permitido", etiqueta=etiqueta, contar_tope=False)
            motivo = f"Hola, {u}."
        else:
            res = "no_concluyente" if r["resultado"] == "no_concluyente" else "no_identificado"
            estado = control.anotar(kip, res, r["motivo"], etiqueta=etiqueta,
                                    fallos_max=CFG.BLOQUEO_IP_FALLOS, bloqueo_seg=CFG.BLOQUEO_IP_SEG)
            motivo = r["motivo"] + (f" Se alcanzaron {CFG.BLOQUEO_IP_FALLOS} intentos sin identificar seguidos: este equipo queda "
                                    f"bloqueado {CFG.BLOQUEO_IP_SEG} s." if estado["bloqueado_ahora"] else "")
        idp = anotar_prueba(t0, "B", caso, etiqueta, r["resultado"], motivo, r["estados"], r["validos"], seg_srv, seg_captura)
        return jsonify(con_explicacion({"resultado": r["resultado"], "titulo": r["titulo"], "motivo": motivo,
                        "estados": r["estados"], "validos": r["validos"], "fotogramas": r["fotogramas"],
                        "segundos_servidor": round(r["segundos_servidor"], 3),
                        "segundos_peticion": round(time.perf_counter() - t0, 3), "id_intento": idp}, r))

    # ------------------------------------------------------------------ paso 2: palabra clave (modos A y B)
    @app.post("/api/clave")
    def api_clave():
        t0 = time.perf_counter()
        datos = request.get_json(silent=True) or {}
        caso, _ = leer_peticion(datos)
        e = pendientes.tomar(datos.get("token"), ip_real(request))
        expl = explicaciones.pop(datos.get("token"), None) if isinstance(datos.get("token"), str) else None
        if e is None:
            return jsonify({"error": "El paso de la palabra clave caducó o no es válido. Vuelva a empezar."}), 400
        u = e["usuario"]
        guardado = almacen.meta(u).get("clave_hash", "") if (almacen and u in almacen.usuarios()) else ""
        clave_ok = comprobar_clave(datos.get("clave"), guardado)      # se calcula siempre (mismo tiempo de respuesta)
        etiqueta = "(solo cámara)" if e["modo"] == "B" else u
        if e["rostro_ok"] and clave_ok:
            control.anotar(u, "permitido", contar_tope=False)          # solo un acceso completo reinicia el contador
            if e["clave_ip"]:
                control.anotar(e["clave_ip"], "permitido", etiqueta="(solo cámara)", contar_tope=False)
            motivo = f"Hola, {u}." if e["modo"] == "B" else "El rostro y la palabra clave son correctos."
            idp = anotar_prueba(t0, "clave", caso, etiqueta, "permitido", motivo)
            return jsonify(con_explicacion({"resultado": "permitido", "titulo": "Acceso permitido", "motivo": motivo, "estados": [],
                                            "id_intento": idp}, {"explicacion": expl} if expl else {}))
        bloqueado = e["bloqueado"]
        if e["rostro_ok"]:                                              # rostro aceptado + clave incorrecta: cuenta como denegado
            bloqueado = control.anotar(u, "denegado", "palabra clave incorrecta (paso 2)", contar_tope=False)["bloqueado_ahora"]
            if e["clave_ip"]:
                control.anotar(e["clave_ip"], "no_identificado", "palabra clave incorrecta (paso 2)", etiqueta="(solo cámara)",
                               fallos_max=CFG.BLOQUEO_IP_FALLOS, bloqueo_seg=CFG.BLOQUEO_IP_SEG, contar_tope=False)
        # Mismo mensaje tanto si falló el rostro como la clave
        motivo = "No se pudo completar el inicio de sesión." + aviso_bloqueo(bloqueado)
        idp = anotar_prueba(t0, "clave", caso, etiqueta, "denegado", motivo)
        return jsonify(con_explicacion({"resultado": "denegado", "titulo": "Acceso denegado", "motivo": motivo, "estados": [],
                                        "id_intento": idp}, {"explicacion": expl} if expl else {}))

    @app.post("/api/prueba/tiempo")
    def api_prueba_tiempo():
        """Modo pruebas: el navegador envía el tiempo total del intento (captura + envío + respuesta)."""
        if not app.modo_pruebas:
            return jsonify({"error": "Solo en modo pruebas."}), 404
        d = request.get_json(silent=True) or {}
        try:
            seg = float(d.get("segundos_total"))
        except (TypeError, ValueError):
            return jsonify({"error": "tiempo no válido"}), 400
        if not re.fullmatch(r"[0-9.]{1,20}", str(d.get("id_intento", ""))) or not 0 < seg < 600:
            return jsonify({"error": "datos no válidos"}), 400
        control.registrar_tiempo_total(d["id_intento"], seg)
        return jsonify({"ok": True})

    if publico:
        # Instancia pública: NO se registran /admin ni las rutas de registro, eliminación o desbloqueo (404).
        from .publico import instalar
        instalar(app, clave_publica or CFG.acceso_publico())
    else:
        # Instancia con administración: solo se usa en este equipo o por `tailscale serve` (proxy local con HTTPS).
        # - Solo responde a nombres de host conocidos (127.0.0.1, localhost y FACEID_ADMIN_HOSTS): evita DNS rebinding.
        # - Rechaza (404) toda petición que haya entrado por internet (Cloudflare Tunnel o Tailscale Funnel), por si
        #   alguien apuntara un túnel a este puerto por error. Las cabeceras X-Forwarded-* del proxy no se usan para nada.
        app.config["TRUSTED_HOSTS"] = CFG.admin_hosts()

        @app.before_request
        def solo_local_o_tailnet():
            if any(h in request.headers for h in CFG.CABECERAS_INTERNET):
                return "No encontrado.", 404
            return None

        from .admin import crear_blueprint
        app.register_blueprint(crear_blueprint())
    return app
