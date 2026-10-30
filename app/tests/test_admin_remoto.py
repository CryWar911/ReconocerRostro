"""Administración desde dispositivos propios por Tailscale (`tailscale serve` -> 127.0.0.1:5001), sin exponerla a internet.

- La instancia pública (la del túnel de Cloudflare) sigue dando 404 en todo /admin.
- La de administración rechaza cualquier petición que haya entrado por internet (Cloudflare o Tailscale Funnel),
  solo responde a nombres de host conocidos y nunca arranca en el puerto público.
- scripts/iniciar_demo_tunel.ps1 nunca apunta el túnel al puerto 5001.
"""
import base64
import re

import pytest

from app import config as CFG
from app.almacen import Almacen
from app.intentos import ControlIntentos
from app.main import comprobar_puerto, create_app
from conftest import Reloj, ServicioDoble

CLAVE_ADMIN = "admin-remoto-123"
TS_HOST = "pc-casa.tail1234.ts.net"
# Cabeceras que añade `tailscale serve` al reenviar a 127.0.0.1:5001
PROXY_TS = {"X-Forwarded-For": "100.101.102.103", "X-Forwarded-Proto": "https", "X-Forwarded-Host": TS_HOST,
            "Tailscale-User-Login": "persona@example.com", "Tailscale-User-Name": "Persona"}
RUTAS_ADMIN = [("get", "/admin/"), ("post", "/admin/entrar"), ("post", "/admin/salir"), ("get", "/admin/registrar"),
               ("post", "/admin/api/registrar"), ("post", "/admin/api/eliminar"), ("post", "/admin/api/desbloquear"),
               ("post", "/admin/api/clave")]


@pytest.fixture
def admin(tmp_path, monkeypatch):
    monkeypatch.setenv("FACEID_ADMIN_PASSWORD", CLAVE_ADMIN)
    monkeypatch.setenv("FACEID_ADMIN_HOSTS", TS_HOST)
    alm = Almacen(tmp_path / "privado")
    app = create_app(ServicioDoble(alm), alm, ControlIntentos(alm.dir, reloj=Reloj()))
    app.config["TESTING"] = True
    return app.test_client()


# ------------------------------------------------------------------ instancia pública
@pytest.mark.parametrize("metodo,ruta", RUTAS_ADMIN)
def test_publica_da_404_en_admin_aun_con_la_contrasena(tmp_path, metodo, ruta):
    alm = Almacen(tmp_path / "p")
    app = create_app(ServicioDoble(alm), alm, ControlIntentos(alm.dir, reloj=Reloj()), modo_publico=True, clave_publica="pub-123")
    h = {"Authorization": "Basic " + base64.b64encode(b"x:pub-123").decode(), "CF-Ray": "8a1b-LIM", "CF-Connecting-IP": "203.0.113.9"}
    assert getattr(app.test_client(), metodo)(ruta, headers=h).status_code == 404


# ------------------------------------------------------------------ instancia de administración
def test_admin_por_tailscale_serve_funciona(admin):
    """Con el nombre *.ts.net y las cabeceras del proxy, el panel pide la contraseña y la acepta."""
    kw = {"headers": PROXY_TS, "base_url": f"https://{TS_HOST}"}
    assert "Contraseña" in admin.get("/admin/", **kw).get_data(as_text=True)
    r = admin.post("/admin/entrar", data={"clave": CLAVE_ADMIN}, **kw)
    assert r.status_code == 302 and r.headers["Location"] == "/admin/"      # redirección relativa: sirve tras el proxy
    assert "Panel de administración" in admin.get("/admin/", **kw).get_data(as_text=True)


def test_admin_sigue_exigiendo_contrasena(admin):
    kw = {"headers": PROXY_TS, "base_url": f"https://{TS_HOST}"}
    assert admin.post("/admin/entrar", data={"clave": "otra"}, **kw).status_code == 401
    assert admin.post("/admin/api/eliminar", json={"id": "V01"}, **kw).status_code == 401
    assert admin.get("/admin/registrar", **kw).status_code == 302


def test_admin_sin_contrasena_configurada_queda_deshabilitada(tmp_path, monkeypatch):
    monkeypatch.delenv("FACEID_ADMIN_PASSWORD", raising=False)
    alm = Almacen(tmp_path / "p")
    c = create_app(ServicioDoble(alm), alm, ControlIntentos(alm.dir, reloj=Reloj())).test_client()
    assert c.post("/admin/entrar", data={"clave": ""}).status_code == 401


@pytest.mark.parametrize("cabecera", [{"CF-Ray": "8a1b-LIM", "CF-Connecting-IP": "203.0.113.9"}, {"CF-Ray": "8a1b-LIM"},
                                      {"CF-Connecting-IP": "203.0.113.9"}, {"Tailscale-Funnel-Request": "?1"}])
@pytest.mark.parametrize("metodo,ruta", RUTAS_ADMIN + [("get", "/"), ("post", "/api/verificar")])
def test_admin_rechaza_lo_que_entra_por_internet(admin, cabecera, metodo, ruta):
    """Si alguien apuntara el túnel de Cloudflare (o Tailscale Funnel) al puerto 5001, todo daría 404."""
    assert getattr(admin, metodo)(ruta, headers=cabecera).status_code == 404


def test_admin_rechaza_hosts_desconocidos(admin):
    """Un nombre que no es 127.0.0.1, localhost ni FACEID_ADMIN_HOSTS no recibe respuesta (protección contra DNS rebinding)."""
    assert admin.get("/admin/", base_url="http://atacante.example").status_code == 400
    assert admin.get("/admin/", base_url="http://192.168.1.50:5001").status_code == 400
    assert admin.get("/admin/", base_url="http://127.0.0.1:5001").status_code == 200


def test_limite_de_contrasenas_de_admin_fallidas(admin, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    for _ in range(CFG.ADMIN_FALLOS_MAX):
        assert admin.post("/admin/entrar", data={"clave": "mala"}).status_code == 401
    r = admin.post("/admin/entrar", data={"clave": CLAVE_ADMIN})
    assert r.status_code == 429 and "Demasiadas contraseñas" in r.get_data(as_text=True)


def test_admin_nunca_en_el_puerto_publico():
    with pytest.raises(RuntimeError):
        comprobar_puerto(False, CFG.PUERTO_PUBLICO)
    comprobar_puerto(False, CFG.PUERTO_ADMIN)
    comprobar_puerto(True, CFG.PUERTO_PUBLICO)
    assert CFG.HOST == "127.0.0.1" and CFG.PUERTO_PUBLICO != CFG.PUERTO_ADMIN


def test_arranque_comprueba_el_puerto_y_escucha_solo_en_loopback(root):
    s = (root / "app" / "__main__.py").read_text(encoding="utf-8")
    assert "comprobar_puerto(CFG.MODO_PUBLICO, CFG.PUERTO)" in s and "host=CFG.HOST" in s
    assert "0.0.0.0" not in s


# ------------------------------------------------------------------ script del túnel
def test_script_del_tunel_no_expone_el_puerto_5001(root):
    s = (root / "scripts" / "iniciar_demo_tunel.ps1").read_text(encoding="utf-8-sig")
    lineas_tunel = [l for l in s.splitlines() if "$Cloudflared" in l and "Start-Process" in l]
    assert len(lineas_tunel) == 1, lineas_tunel
    destinos = re.findall(r'"--url",\s*"([^"]+)"', lineas_tunel[0])
    assert destinos == ["http://127.0.0.1:5000"]
    # Ningún otro destino de túnel ni Tailscale Funnel en el script
    assert len(re.findall(r"--url", s)) == 1
    assert "funnel" not in s.lower() and "tailscale" not in s.lower()
    # 5001 solo aparece como instancia local de administración, nunca junto a cloudflared
    for l in s.splitlines():
        if "5001" in l:
            assert "cloudflared" not in l.lower() and "--url" not in l


def test_script_completo_tailscale_solo_al_5001_y_nunca_funnel(root):
    s = (root / "scripts" / "iniciar_demo_completa.ps1").read_text(encoding="utf-8-sig")
    codigo = [l for l in s.splitlines() if l.strip() and not l.strip().startswith("#")]
    serve = [l for l in codigo if re.search(r"\bserve\s+--bg\b", l)]
    assert len(serve) == 1 and serve[0].rstrip().endswith("serve --bg http://127.0.0.1:5001 | Out-Null")
    assert not [l for l in codigo if re.search(r"&\s*\$Tailscale\s+funnel", l)]      # nunca ejecuta Funnel
    assert "AllowFunnel" in s and "serve reset" in s                                 # se detiene si hay Funnel y limpia al salir
    assert "cloudflared" not in s.lower() and "5000\"" not in s                       # el túnel lo maneja solo iniciar_demo_tunel.ps1
    assert 'Join-Path $PSScriptRoot "iniciar_demo_tunel.ps1"' in s
    # Comprueba los puertos ANTES de tocar Tailscale
    assert s.index("Get-NetTCPConnection") < s.index("serve --bg")
