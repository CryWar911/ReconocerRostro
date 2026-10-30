<#
.SYNOPSIS
  Arranca TODO de una vez: la demostración por túnel (instancia pública 5000 + Cloudflare Tunnel, y administración 5001)
  y el acceso a la administración desde sus dispositivos por Tailscale (`tailscale serve` -> 127.0.0.1:5001).
  Al pulsar Enter cierra todo y quita `tailscale serve`.

.DESCRIPTION
  - Cloudflare Tunnel apunta SOLO a la instancia pública (5000); lo hace scripts\iniciar_demo_tunel.ps1, que este script llama.
  - Tailscale publica la administración (5001) SOLO dentro de su tailnet, con HTTPS. Nunca usa Funnel: si detecta Funnel
    activo, se detiene.
  - Detecta el nombre *.ts.net de este equipo y lo pasa a la app en FACEID_ADMIN_HOSTS.
  - Al cerrar ejecuta `tailscale serve reset` (quita cualquier configuración de serve de este equipo).

.PARAMETER SinTailscale
  Solo la demostración por túnel, sin publicar la administración en la tailnet.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\iniciar_demo_completa.ps1
#>
param(
  [switch]$SinTunel,
  [switch]$ModoPruebas,
  [switch]$SinTailscale,
  [string]$Dispositivo = ""
)
$ErrorActionPreference = "Stop"
function Fallar($msg) { Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

foreach ($p in 5000, 5001) {
  if (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) { Fallar "El puerto $p ya está en uso. Cierre la otra instancia de la app (Ctrl+C) y vuelva a intentarlo." }
}

$Tailscale = $null
if (-not $SinTailscale) {
  $c = Get-Command tailscale -ErrorAction SilentlyContinue
  if ($c) { $Tailscale = $c.Source }
  elseif (Test-Path "$env:ProgramFiles\Tailscale\tailscale.exe") { $Tailscale = "$env:ProgramFiles\Tailscale\tailscale.exe" }
  else { Fallar "Tailscale no está instalado. Instálelo con:  winget install --id Tailscale.Tailscale   (o use -SinTailscale)." }

  $estado = & $Tailscale status --json 2>$null | ConvertFrom-Json
  if (-not $estado -or $estado.BackendState -ne "Running") { Fallar "Tailscale no está conectado. Abra Tailscale e inicie sesión." }
  $NombreTs = ($estado.Self.DNSName).TrimEnd(".")
  if (-not $NombreTs) { Fallar "No se obtuvo el nombre *.ts.net de este equipo. Active MagicDNS en la consola de Tailscale." }

  # Solo dentro de la tailnet (nunca Funnel), hacia la administración local.
  & $Tailscale serve --bg http://127.0.0.1:5001 | Out-Null
  if ($LASTEXITCODE -ne 0) { Fallar "No se pudo activar 'tailscale serve'. Ejecútelo a mano una vez para ver el enlace de activación." }
  $serve = & $Tailscale serve status --json | ConvertFrom-Json
  if ($serve.AllowFunnel -and @($serve.AllowFunnel.PSObject.Properties | Where-Object { $_.Value }).Count -gt 0) {
    & $Tailscale serve reset | Out-Null
    Fallar "Tailscale Funnel estaba activo (publicaría el panel en internet). Se quitó todo. Revise 'tailscale serve status'."
  }
  $env:FACEID_ADMIN_HOSTS = $NombreTs
  Write-Host "Tailscale: administración en https://$NombreTs/admin/ (solo sus dispositivos)" -ForegroundColor Yellow
}

$argumentos = @{}
if ($SinTunel) { $argumentos.SinTunel = $true }
if ($ModoPruebas) { $argumentos.ModoPruebas = $true }
if ($Dispositivo) { $argumentos.Dispositivo = $Dispositivo }
try {
  & (Join-Path $PSScriptRoot "iniciar_demo_tunel.ps1") @argumentos
}
finally {
  if ($Tailscale) {
    & $Tailscale serve reset | Out-Null
    Write-Host "Tailscale serve desactivado: la administración vuelve a ser solo local." -ForegroundColor Gray
  }
  $env:FACEID_ADMIN_HOSTS = ""
}
