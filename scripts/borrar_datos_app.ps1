<#
.SYNOPSIS
  Borra TODOS los datos de la aplicación (plantillas de usuarios, metadatos, fotos conservadas, registros de intentos,
  registro del modo pruebas y del administrador) y verifica que se borraron. No toca el modelo ni las 24 plantillas
  del dataset (models/).

.PARAMETER Carpeta
  Carpeta de datos. Por defecto, FACEID_APP_DATA o %USERPROFILE%\FaceID_privado.

.PARAMETER Confirmar
  Omite la pregunta de confirmación (uso en scripts). Sin él, hay que escribir BORRAR.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\borrar_datos_app.ps1
#>
param([string]$Carpeta = "", [switch]$Confirmar)
$ErrorActionPreference = "Stop"
$Raiz = (Resolve-Path (Split-Path -Parent $PSScriptRoot)).Path
if (-not $Carpeta) { $Carpeta = $env:FACEID_APP_DATA }
if (-not $Carpeta) { $Carpeta = Join-Path $env:USERPROFILE "FaceID_privado" }

if (-not (Test-Path $Carpeta)) { Write-Host "No existe ${Carpeta}: no hay datos que borrar." -ForegroundColor Green; exit 0 }
$Ruta = (Resolve-Path $Carpeta).Path.TrimEnd("\")

# Protecciones: no borrar la raíz de una unidad, el perfil del usuario ni carpetas del repositorio fuera de data\
if ($Ruta -match '^[A-Za-z]:$' -or $Ruta -eq $env:USERPROFILE.TrimEnd("\")) { Write-Host "Ruta peligrosa: $Ruta" -ForegroundColor Red; exit 1 }
if ($Ruta.StartsWith($Raiz, [StringComparison]::OrdinalIgnoreCase) -and -not $Ruta.StartsWith((Join-Path $Raiz "data"), [StringComparison]::OrdinalIgnoreCase)) {
  Write-Host "La carpeta $Ruta está dentro del repositorio fuera de data\. No se borra." -ForegroundColor Red; exit 1
}
if (-not (Test-Path (Join-Path $Ruta "usuarios")) -and -not (Get-ChildItem $Ruta -Filter "*intentos*" -ErrorAction SilentlyContinue)) {
  Write-Host "$Ruta no parece una carpeta de datos de la app (no tiene usuarios\ ni registros). No se borra." -ForegroundColor Red; exit 1
}
foreach ($p in 5000, 5001) {
  if (Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "Hay una instancia de la app escuchando en el puerto $p. Ciérrela antes de borrar." -ForegroundColor Red; exit 1
  }
}

$usuarios = @(Get-ChildItem (Join-Path $Ruta "usuarios") -Directory -ErrorAction SilentlyContinue)
$archivos = @(Get-ChildItem $Ruta -Recurse -File -ErrorAction SilentlyContinue)
Write-Host "Carpeta: $Ruta"
Write-Host "Usuarios registrados: $($usuarios.Count)  |  archivos: $($archivos.Count)"
if (-not $Confirmar) {
  $r = Read-Host "Esto borra de forma permanente las plantillas y registros. Escriba BORRAR para continuar"
  if ($r -ne "BORRAR") { Write-Host "Cancelado." ; exit 1 }
}

Remove-Item -LiteralPath $Ruta -Recurse -Force

# Verificación
if (Test-Path -LiteralPath $Ruta) {
  $quedan = @(Get-ChildItem -LiteralPath $Ruta -Recurse -Force -ErrorAction SilentlyContinue)
  Write-Host "FALLO: la carpeta sigue existiendo con $($quedan.Count) elementos." -ForegroundColor Red; exit 2
}
Write-Host "OK: $Ruta ya no existe. Se borraron $($usuarios.Count) usuarios y $($archivos.Count) archivos." -ForegroundColor Green
exit 0
