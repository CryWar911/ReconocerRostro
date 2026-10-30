"""Control de intentos por usuario y registro de intentos (HU15).

Reglas:
  - Bloqueo: BLOQUEO_FALLOS intentos DENEGADOS consecutivos para un mismo usuario -> bloqueo de BLOQUEO_SEG.
    Un acceso PERMITIDO reinicia el contador. Los NO CONCLUYENTES se registran pero no cambian el contador.
    Al bloquear, el contador vuelve a 0. El administrador puede desbloquear.
  - Tope general (independiente): si un usuario acumula TOPE_INTENTOS intentos procesados (de cualquier tipo)
    en TOPE_VENTANA_SEG segundos, se hace una pausa de TOPE_PAUSA_SEG antes de admitir más (limita la carga).
  - Registro (CSV, sin imágenes ni puntuaciones): fecha y hora, usuario solicitado, resultado y motivo, para
    los intentos denegados, no concluyentes y rechazados por bloqueo o pausa. Los permitidos no se registran.
El estado se guarda en disco (estado_intentos.json) para que reiniciar el servidor no levante un bloqueo, y se
vuelve a leer antes de cada operación: así la instancia pública (puerto 5000) y la de administración (5001)
comparten bloqueos y desbloqueos sin reiniciar.
"""
import csv
import json
import os
import threading
import time
from pathlib import Path

from . import config as CFG

CAMPOS = ["fecha_hora", "usuario_solicitado", "resultado", "motivo"]


class ControlIntentos:
    def __init__(self, carpeta, reloj=time.time, fallos=None, bloqueo_seg=None, tope=None, ventana=None, pausa=None):
        self.carpeta = Path(carpeta)
        self.reloj = reloj
        self.fallos_max = fallos or CFG.BLOQUEO_FALLOS
        self.bloqueo_seg = bloqueo_seg or CFG.BLOQUEO_SEG
        self.tope = tope or CFG.TOPE_INTENTOS
        self.ventana = ventana or CFG.TOPE_VENTANA_SEG
        self.pausa = pausa or CFG.TOPE_PAUSA_SEG
        self.f_estado = self.carpeta / "estado_intentos.json"
        self.f_registro = self.carpeta / "registro_intentos.csv"
        self.lock = threading.Lock()
        self.estado = {}
        self._recargar()

    # ---------------------------------------------------------------- utilidades
    def _e(self, uid):
        return self.estado.setdefault(uid, {"fallos": 0, "bloqueado_hasta": 0.0, "pausa_hasta": 0.0, "recientes": []})

    def _recargar(self):
        """Lee el estado compartido del disco (lo puede haber cambiado la otra instancia)."""
        try:
            self.estado = json.loads(self.f_estado.read_text(encoding="utf-8")) if self.f_estado.exists() else {}
        except (OSError, ValueError):
            pass   # archivo a medio escribir por la otra instancia: se conserva el estado en memoria

    def _guardar(self):
        """Escritura atómica (archivo temporal + reemplazo) para que la otra instancia nunca lea un JSON a medias."""
        tmp = self.f_estado.with_name(f"{self.f_estado.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(self.estado), encoding="utf-8")
        os.replace(tmp, self.f_estado)

    def registrar(self, uid, resultado, motivo=""):
        nuevo = not self.f_registro.exists()
        with open(self.f_registro, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CAMPOS)
            if nuevo:
                w.writeheader()
            w.writerow({"fecha_hora": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.reloj())),
                        "usuario_solicitado": uid, "resultado": resultado, "motivo": motivo})

    # ---------------------------------------------------------------- antes del intento
    def comprobar(self, uid, etiqueta=None):
        """None si se puede intentar; si no, dict con 'resultado' ('bloqueado' o 'pausa') y 'segundos' de espera.
        etiqueta: texto para el registro en lugar de la clave interna (p. ej. en el bloqueo por IP del modo B)."""
        nombre = etiqueta or uid
        with self.lock:
            self._recargar()
            e, t = self._e(uid), self.reloj()
            if e["bloqueado_hasta"] > t:
                seg = int(e["bloqueado_hasta"] - t) + 1
                self.registrar(nombre, "bloqueado", f"bloqueado; faltan {seg} s")
                return {"resultado": "bloqueado", "segundos": seg}
            if e["pausa_hasta"] > t:
                seg = int(e["pausa_hasta"] - t) + 1
                self.registrar(nombre, "pausa", f"demasiados intentos; faltan {seg} s")
                return {"resultado": "pausa", "segundos": seg}
            return None

    # ---------------------------------------------------------------- después del intento
    def anotar(self, uid, resultado, motivo="", etiqueta=None, fallos_max=None, bloqueo_seg=None, contar_tope=True):
        """Actualiza el estado tras un intento procesado. Devuelve dict con 'bloqueado_ahora' y 'fallos'.

        Cuentan como fallo 'denegado' y 'no_identificado' (modo B); 'permitido' reinicia; 'no_concluyente' no cambia nada.
        contar_tope=False para el paso de la palabra clave, que forma parte del mismo intento que el rostro."""
        fallos_max, bloqueo_seg = fallos_max or self.fallos_max, bloqueo_seg or self.bloqueo_seg
        with self.lock:
            self._recargar()
            e, t = self._e(uid), self.reloj()
            e["recientes"] = [x for x in e["recientes"] if x > t - self.ventana]
            if contar_tope:
                e["recientes"].append(t)
            bloqueado_ahora = False
            if resultado == "permitido":
                e["fallos"] = 0
            elif resultado in ("denegado", "no_identificado"):
                e["fallos"] += 1
                if e["fallos"] >= fallos_max:
                    e["bloqueado_hasta"], e["fallos"], bloqueado_ahora = t + bloqueo_seg, 0, True
            if resultado in ("denegado", "no_concluyente", "no_identificado"):
                self.registrar(etiqueta or uid, resultado, motivo + (" | bloqueo activado" if bloqueado_ahora else ""))
            if len(e["recientes"]) >= self.tope:
                e["pausa_hasta"], e["recientes"] = t + self.pausa, []
            self._guardar()
            return {"bloqueado_ahora": bloqueado_ahora, "fallos": e["fallos"]}

    # ---------------------------------------------------------------- bloqueo por IP (modo B)
    def clave_ip(self, ip):
        """Clave interna para el bloqueo por IP: hash con una sal local (la IP no se guarda en claro)."""
        f = self.carpeta / "sal_ip.bin"
        if not f.exists():
            f.write_bytes(os.urandom(16))
        import hashlib
        return "ip:" + hashlib.sha256(f.read_bytes() + str(ip).encode()).hexdigest()[:16]

    # ---------------------------------------------------------------- administración
    def desbloquear(self, uid):
        with self.lock:
            self._recargar()
            e = self._e(uid)
            e.update(fallos=0, bloqueado_hasta=0.0, pausa_hasta=0.0, recientes=[])
            self._guardar()
            self.registrar(uid, "desbloqueado", "por el administrador")

    def olvidar(self, uid):
        with self.lock:
            self._recargar()
            self.estado.pop(uid, None)
            self._guardar()

    def resumen(self):
        """{uid: {'fallos', 'bloqueado_seg', 'pausa_seg'}} de los usuarios con algún estado."""
        with self.lock:
            self._recargar()
        t = self.reloj()
        return {u: {"fallos": e["fallos"], "bloqueado_seg": max(0, int(e["bloqueado_hasta"] - t)),
                    "pausa_seg": max(0, int(e["pausa_hasta"] - t))} for u, e in self.estado.items()}

    # ---------------------------------------------------------------- modo pruebas (tarea 3.4)
    CAMPOS_PRUEBA = ["id_intento", "fecha_hora", "modo", "caso", "usuario_solicitado", "resultado", "motivo", "estados",
                     "validos", "segundos_captura", "segundos_servidor", "segundos_peticion"]

    def registrar_prueba(self, fila):
        """Solo con FACEID_MODO_PRUEBAS=1: registra TODOS los intentos (también permitidos) con sus tiempos.
        Sin imágenes ni puntuaciones. Devuelve el id del intento."""
        f = self.carpeta / "registro_pruebas.csv"
        if f.exists():
            with open(f, encoding="utf-8") as fh:
                cabecera = fh.readline().strip().split(",")
            if cabecera != self.CAMPOS_PRUEBA:      # registro de una versión anterior: se conserva aparte
                os.replace(f, f.with_name(f"registro_pruebas_anterior_{int(self.reloj())}.csv"))
        nuevo = not f.exists()
        fila = dict(fila, id_intento=f"{self.reloj():.3f}", fecha_hora=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.reloj())))
        with self.lock, open(f, "a", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=self.CAMPOS_PRUEBA)
            if nuevo:
                w.writeheader()
            w.writerow({k: fila.get(k, "") for k in self.CAMPOS_PRUEBA})
        return fila["id_intento"]

    def registrar_tiempo_total(self, id_intento, segundos):
        """Tiempo total medido en el navegador (captura + envío + respuesta) de un intento del modo pruebas."""
        f = self.carpeta / "tiempos_cliente.csv"
        nuevo = not f.exists()
        with self.lock, open(f, "a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if nuevo:
                w.writerow(["id_intento", "segundos_total_cliente"])
            w.writerow([id_intento, f"{segundos:.3f}"])

    def ultimos_registros(self, n=20):
        if not self.f_registro.exists():
            return []
        with open(self.f_registro, encoding="utf-8") as f:
            return list(csv.DictReader(f))[-n:][::-1]
