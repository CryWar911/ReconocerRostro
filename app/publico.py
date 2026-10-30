"""Modo público para exponer la app por un túnel (Cloudflare Tunnel -> 127.0.0.1:5000).

- Autenticación básica en TODAS las rutas, con la contraseña de FACEID_ACCESO_PUBLICO (el usuario se ignora).
- Límite de verificaciones por IP real y límite de contraseñas fallidas por IP.
- IP real: por el túnel todas las peticiones llegan desde 127.0.0.1, así que la IP del cliente se toma de la cabecera
  CF-Connecting-IP SOLO cuando la petición viene del túnel (dirección de loopback y cabeceras CF-Connecting-IP y CF-Ray,
  que Cloudflare pone y sobrescribe). Una petición directa desde la red no puede llegar: la app solo escucha en 127.0.0.1.
- Las rutas de administración no se registran en esta instancia (responden 404); ver main.create_app.
"""
import hmac
import ipaddress
import threading
import time
from collections import defaultdict, deque

from flask import Response, jsonify, request

from . import config as CFG

LOOPBACK = {"127.0.0.1", "::1"}


def ip_real(req):
    """IP del cliente: CF-Connecting-IP si la petición viene del túnel; si no, la dirección de la conexión."""
    remota = req.remote_addr or ""
    cf_ip, cf_ray = req.headers.get("CF-Connecting-IP"), req.headers.get("CF-Ray")
    if remota in LOOPBACK and cf_ip and cf_ray:
        try:
            return str(ipaddress.ip_address(cf_ip.strip()))
        except ValueError:
            return remota
    return remota


class Limitador:
    """Ventana deslizante en memoria: como máximo `maximo` eventos por clave en `ventana` segundos."""

    def __init__(self, maximo, ventana, reloj=time.monotonic):
        self.maximo, self.ventana, self.reloj = maximo, ventana, reloj
        self.eventos = defaultdict(deque)
        self.lock = threading.Lock()

    def _limpiar(self, clave, t):
        q = self.eventos[clave]
        while q and q[0] <= t - self.ventana:
            q.popleft()
        return q

    def excedido(self, clave):
        with self.lock:
            return len(self._limpiar(clave, self.reloj())) >= self.maximo

    def anotar(self, clave):
        """Registra un evento. Devuelve True si se permite (no se había llegado al máximo)."""
        with self.lock:
            t = self.reloj()
            q = self._limpiar(clave, t)
            if len(q) >= self.maximo:
                return False
            q.append(t)
            return True

    def espera(self, clave):
        with self.lock:
            t = self.reloj()
            q = self._limpiar(clave, t)
            return int(q[0] + self.ventana - t) + 1 if q else 0


def instalar(app, clave, reloj=time.monotonic):
    """Activa la autenticación básica y los límites por IP en una app Flask."""
    if not clave:
        raise RuntimeError("Modo público sin contraseña: defina FACEID_ACCESO_PUBLICO antes de arrancar.")
    lim_verif = Limitador(CFG.LIMITE_IP_PETICIONES, CFG.LIMITE_IP_VENTANA_SEG, reloj)
    lim_auth = Limitador(CFG.LIMITE_AUTH_FALLOS, CFG.LIMITE_AUTH_VENTANA_SEG, reloj)
    app.limitadores = {"verificar": lim_verif, "auth": lim_auth}

    def pedir_credenciales(msg="Se requiere la contraseña de la demostración."):
        return Response(msg, 401, {"WWW-Authenticate": 'Basic realm="Demostracion FaceID", charset="UTF-8"'})

    @app.before_request
    def controlar():
        ip = ip_real(request)
        if lim_auth.excedido(ip):
            return Response(f"Demasiados intentos de contraseña. Espere {lim_auth.espera(ip)} s.", 429)
        auth = request.authorization
        dada = (auth.password or "") if auth and auth.type == "basic" else None
        if dada is None or not hmac.compare_digest(dada.encode(), clave.encode()):
            if dada is not None:
                lim_auth.anotar(ip)
            return pedir_credenciales()
        if request.endpoint in ("api_verificar", "api_identificar", "api_clave") and not lim_verif.anotar(ip):
            seg = lim_verif.espera(ip)
            return jsonify({"resultado": "bloqueado", "titulo": "Demasiadas peticiones",
                            "motivo": f"Se superó el límite de {CFG.LIMITE_IP_PETICIONES} verificaciones por minuto desde esta conexión. "
                                      f"Espere {seg} s.", "estados": []}), 429
        return None
