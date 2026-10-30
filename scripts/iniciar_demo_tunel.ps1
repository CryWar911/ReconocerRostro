<#
.SYNOPSIS
  Arranca la demostración expuesta por túnel: instancia de administración (127.0.0.1:5001), instancia pública
  (127.0.0.1:5000, solo verificación) y Cloudflare Tunnel hacia el puerto 5000. Muestra la dirección pública y,
  al pulsar Enter, cierra todo.

.DESCRIPTION
  - El túnel SIEMPRE apunta a http://127.0.0.1:5000 (instancia pública). La administración (5001) nunca se expone.
  - Contraseñas: FACEID_ACCESO_PUBLICO (autenticación básica de la instancia pública) y FACEID_ADMIN_PASSWORD
    (administración). Si no están definidas, se piden sin mostrarlas. No se guardan en disco.
  - Ambas instancias usan la misma carpeta de datos (FACEID_APP_DATA, por defecto %USERPROFILE%\FaceID_privado).
  - Mientras el script está abierto, Windows no suspende el equipo ni apaga la pantalla (no cambia la configuración
    de energía; al cerrar se restablece). Use igualmente el cargador.
  - La dirección *.trycloudflare.com CAMBIA cada vez que se reinicia el túnel.

.PARAMETER SinTunel
  Arranca solo las dos instancias (para probar en local sin cloudflared).

.PARAMETER ModoPruebas
  Activa FACEID_MODO_PRUEBAS=1 en la instancia pública: se registran todos los intentos con su caso de prueba y sus
  tiempos (sin imágenes), para medir el tiempo de punta a punta desde un teléfono. Resumen: python -m app.resumen_pruebas

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\iniciar_demo_tunel.ps1
#>
param(
  [switch]$SinTunel,
  [switch]$ModoPruebas,
  [string]$Dispositivo = ""
)
$ErrorActionPreference = "Stop"
$Raiz = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Raiz ".venv\Scripts\python.exe"
$Logs = Join-Path $env:TEMP "faceid_demo_logs"
New-Item -ItemType Directory -Force $Logs | Out-Null

function Fallar($msg) { Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }
function ClavePlana($nombre, $texto) {
  $v = [Environment]::GetEnvironmentVariable($nombre, "Process")
  if ($v) { return $v }
  $s = Read-Host -AsSecureString $texto
  $b = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($s)
  try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($b) } finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($b) }
}
function Esperar-Puerto($puerto, $segundos) {
  $limite = (Get-Date).AddSeconds($segundos)
  while ((Get-Date) -lt $limite) {
    $c = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort $puerto -State Listen -ErrorAction SilentlyContinue
    if ($c) { return $true }
    Start-Sleep -Milliseconds 500
  }
  return $false
}

# ---------------------------------------------------------------- comprobaciones
if (-not (Test-Path $Python)) { Fallar "No existe $Python. Cree el entorno con las instrucciones del README." }
if (-not (Test-Path (Join-Path $Raiz "models\verificador_facenet_vggface2\red.ts"))) { Fallar "Falta el paquete del modelo en models\verificador_facenet_vggface2." }
foreach ($p in 5000, 5001) {
  if (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) { Fallar "El puerto $p ya está en uso. Cierre la otra instancia." }
}
$Cloudflared = $null
if (-not $SinTunel) {
  $c = Get-Command cloudflared -ErrorAction SilentlyContinue
  if (-not $c) { Fallar "cloudflared no está instalado. Instálelo con:  winget install --id Cloudflare.cloudflared   (o use -SinTunel)." }
  $Cloudflared = $c.Source
}

$ClavePublica = ClavePlana "FACEID_ACCESO_PUBLICO" "Contraseña de acceso para la instancia PÚBLICA (la usarán los teléfonos)"
$ClaveAdmin = ClavePlana "FACEID_ADMIN_PASSWORD" "Contraseña del ADMINISTRADOR (solo en esta laptop, puerto 5001)"
if (-not $ClavePublica -or -not $ClaveAdmin) { Fallar "Las dos contraseñas son obligatorias." }
if ($ClavePublica -eq $ClaveAdmin) { Fallar "Use contraseñas distintas para la instancia pública y para la administración." }

# ---------------------------------------------------------------- mantener el equipo despierto (temporal)
Add-Type -Namespace Win32 -Name Energia -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);'
$ES_CONTINUOUS = [uint32]"0x80000000"; $ES_SYSTEM = [uint32]"0x00000001"; $ES_DISPLAY = [uint32]"0x00000002"
[void][Win32.Energia]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM -bor $ES_DISPLAY)

$procesos = @()
try {
  # ------------------------------------------------------------ instancia de administración (5001)
  $env:FACEID_MODO_PUBLICO = ""; $env:FACEID_ACCESO_PUBLICO = ""
  $env:FACEID_ADMIN_PASSWORD = $ClaveAdmin; $env:FACEID_PUERTO = "5001"
  if ($Dispositivo) { $env:FACEID_DEVICE = $Dispositivo }
  $procesos += Start-Process -FilePath $Python -ArgumentList "-m", "app" -WorkingDirectory $Raiz -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $Logs "admin.out.log") -RedirectStandardError (Join-Path $Logs "admin.err.log")

  # ------------------------------------------------------------ instancia pública (5000)
  $env:FACEID_ADMIN_PASSWORD = ""   # la pública no tiene administración
  $env:FACEID_MODO_PUBLICO = "1"; $env:FACEID_ACCESO_PUBLICO = $ClavePublica; $env:FACEID_PUERTO = "5000"
  if ($ModoPruebas) { $env:FACEID_MODO_PRUEBAS = "1" }
  $procesos += Start-Process -FilePath $Python -ArgumentList "-m", "app" -WorkingDirectory $Raiz -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $Logs "publica.out.log") -RedirectStandardError (Join-Path $Logs "publica.err.log")

  # Las contraseñas solo quedan en el entorno de los procesos hijos.
  $env:FACEID_ACCESO_PUBLICO = ""; $env:FACEID_ADMIN_PASSWORD = ""; $env:FACEID_MODO_PUBLICO = ""; $env:FACEID_PUERTO = ""; $env:FACEID_MODO_PRUEBAS = ""

  Write-Host "Cargando el modelo en las dos instancias..."
  if (-not (Esperar-Puerto 5001 120)) { Fallar "La instancia de administración no arrancó. Vea $Logs\admin.err.log" }
  if (-not (Esperar-Puerto 5000 120)) { Fallar "La instancia pública no arrancó. Vea $Logs\publica.err.log" }

  $Publica = "(sin túnel)"
  if (-not $SinTunel) {
    $logTunel = Join-Path $Logs "cloudflared.log"
    if (Test-Path $logTunel) { Remove-Item $logTunel }
    # El túnel apunta SOLO a la instancia pública.
    $procesos += Start-Process -FilePath $Cloudflared -ArgumentList "tunnel", "--no-autoupdate", "--url", "http://127.0.0.1:5000" `
      -PassThru -WindowStyle Hidden -RedirectStandardError $logTunel -RedirectStandardOutput (Join-Path $Logs "cloudflared.out.log")
    $limite = (Get-Date).AddSeconds(60)
    while ((Get-Date) -lt $limite -and $Publica -eq "(sin túnel)") {
      Start-Sleep -Seconds 1
      if (Test-Path $logTunel) {
        $m = Select-String -Path $logTunel -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -AllMatches | Select-Object -First 1
        if ($m) { $Publica = $m.Matches[0].Value }
      }
    }
    if ($Publica -eq "(sin túnel)") { Fallar "No se obtuvo la dirección del túnel. Vea $logTunel" }
  }

  Write-Host ""
  Write-Host "==============================================================" -ForegroundColor Green
  Write-Host " Dirección PÚBLICA (teléfonos):  $Publica" -ForegroundColor Green
  Write-Host "   usuario: cualquiera  |  contraseña: la de acceso público" -ForegroundColor Green
  Write-Host " Administración (SOLO esta laptop): http://127.0.0.1:5001/admin/" -ForegroundColor Yellow
  if ($env:FACEID_ADMIN_HOSTS) {
    Write-Host " Administración en sus dispositivos: https://$($env:FACEID_ADMIN_HOSTS)/admin/" -ForegroundColor Yellow
  }
  Write-Host " Pública en esta laptop:            http://127.0.0.1:5000" -ForegroundColor Gray
  Write-Host " La dirección pública cambia si se reinicia el túnel." -ForegroundColor Gray
  Write-Host " Registros técnicos: $Logs" -ForegroundColor Gray
  Write-Host "==============================================================" -ForegroundColor Green
  Read-Host "Pulse Enter para cerrar el túnel y las dos instancias"
}
finally {
  foreach ($p in $procesos) { if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue } }
  [void][Win32.Energia]::SetThreadExecutionState($ES_CONTINUOUS)
  $env:FACEID_ACCESO_PUBLICO = ""; $env:FACEID_ADMIN_PASSWORD = ""; $env:FACEID_MODO_PUBLICO = ""; $env:FACEID_PUERTO = ""
  Write-Host "Todo cerrado (túnel e instancias). Suspensión del equipo restablecida."
}
