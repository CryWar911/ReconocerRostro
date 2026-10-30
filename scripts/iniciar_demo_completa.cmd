@echo off
rem Doble clic: arranca la demostracion completa (Cloudflare Tunnel + administracion por Tailscale).
rem Para cerrar todo, pulse Enter en esta ventana (no la cierre con la X).
cd /d "%~dp0.."
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar_demo_completa.ps1" %*
pause
