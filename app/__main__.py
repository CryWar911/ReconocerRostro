"""Arranque local:  .venv/Scripts/python -m app   ->  http://127.0.0.1:5001 (administración; FACEID_PUERTO lo cambia,
pero nunca a 5000, que es el puerto de la instancia pública y del túnel)

Dos instancias para la demostración por túnel (ver scripts/iniciar_demo_tunel.ps1):
  pública:          FACEID_MODO_PUBLICO=1, FACEID_ACCESO_PUBLICO=<clave>, FACEID_PUERTO=5000  (el túnel apunta aquí)
  administración:   FACEID_ADMIN_PASSWORD=<clave>, FACEID_PUERTO=5001                       (nunca por el túnel)
Ambas usan la misma carpeta de datos (FACEID_APP_DATA) y escuchan solo en 127.0.0.1.
"""
from . import config as CFG
from .main import comprobar_puerto, create_app

if __name__ == "__main__":
    comprobar_puerto(CFG.MODO_PUBLICO, CFG.PUERTO)
    app = create_app()
    modo = "PÚBLICA (solo verificación)" if app.modo_publico else "con administración"
    print(f"Instancia {modo}. Modelo cargado en {app.servicio.device} ({app.servicio.segundos_carga:.1f} s). "
          f"Datos: {app.almacen.dir}. Abra http://{CFG.HOST}:{CFG.PUERTO}", flush=True)
    # Solo 127.0.0.1: la app no es accesible directamente desde otras máquinas de la red.
    app.run(host=CFG.HOST, port=CFG.PUERTO, debug=False, threaded=True)
