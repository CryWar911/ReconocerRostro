"""Pasos de palabra clave pendientes (entre el paso del rostro y el de la clave).

Cada token es aleatorio, de un solo uso, caduca a los CLAVE_TOKEN_SEG segundos y queda ligado a la IP que hizo el paso
del rostro. Se guarda solo en memoria. No contiene imágenes ni puntuaciones.
"""
import secrets
import threading
import time

from . import config as CFG


class Pendientes:
    def __init__(self, reloj=time.monotonic, duracion=None):
        self.reloj, self.duracion = reloj, duracion or CFG.CLAVE_TOKEN_SEG
        self.items, self.lock = {}, threading.Lock()

    def crear(self, usuario, rostro_ok, modo, ip, clave_ip=None, bloqueado=False):
        tok = secrets.token_urlsafe(24)
        with self.lock:
            t = self.reloj()
            self.items = {k: v for k, v in self.items.items() if v["expira"] > t}
            self.items[tok] = {"usuario": usuario, "rostro_ok": bool(rostro_ok), "modo": modo, "ip": ip,
                               "clave_ip": clave_ip, "bloqueado": bloqueado, "expira": t + self.duracion}
        return tok

    def tomar(self, token, ip):
        """Devuelve y elimina el paso pendiente si existe, no caducó y viene de la misma IP; si no, None."""
        if not isinstance(token, str):
            return None
        with self.lock:
            e = self.items.pop(token, None)
        if e is None or e["expira"] <= self.reloj() or e["ip"] != ip:
            return None
        return e
