# ---------------------------------------------------------------------------
# install.ps1 — Windows installer for davinci-frameio-bridge
# ---------------------------------------------------------------------------
$ErrorActionPreference = "Stop"

$SelfDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Src      = Join-Path $SelfDir "src"

$CoreDir  = Join-Path $env:USERPROFILE ".resolve_frameio"
$Resolve  = Join-Path $env:APPDATA "Blackmagic Design\DaVinci Resolve\Support\Fusion\Scripts"
$Deliver  = Join-Path $Resolve "Deliver"

Write-Host ">> davinci-frameio-bridge installer"
Write-Host ">> source : $Src"
Write-Host ">> target : $CoreDir"
Write-Host ">> resolve: $Resolve"
Write-Host ""

if (!(Test-Path $Src)) {
    Write-Error "src/ not found next to install.ps1"
}
if (!(Test-Path $Resolve)) {
    Write-Error "DaVinci Resolve scripts folder not found at: $Resolve`nInstall and open DaVinci Resolve first."
}

# 1. Private config dir
New-Item -ItemType Directory -Force -Path $CoreDir | Out-Null

# 2. Core libs
Copy-Item (Join-Path $Src "frameio_core.py") $CoreDir -Force
Copy-Item (Join-Path $Src "uploader_gui.py") $CoreDir -Force
Write-Host "Copied frameio_core.py and uploader_gui.py to $CoreDir"

# 3. Entry-point scripts
New-Item -ItemType Directory -Force -Path $Deliver | Out-Null
Copy-Item (Join-Path $Src "Enviar_para_Frame.io.py")      $Deliver -Force
Copy-Item (Join-Path $Src "Importar_comentarios.py")      $Resolve -Force
Copy-Item (Join-Path $Src "Enviar_ao_terminar_render.py") $Resolve -Force
Write-Host "Copied menu scripts into the Resolve Scripts folder"

# 4. Preserve any existing config
$cfg = Join-Path $CoreDir "config.json"
if (!(Test-Path $cfg)) {
    "{}" | Out-File -FilePath $cfg -Encoding UTF8
    Write-Host "Created empty config.json"
} else {
    Write-Host "Existing config.json preserved"
}

Write-Host ""
Write-Host "Done! Open DaVinci Resolve -> Workspace -> Scripts -> Deliver -> Enviar para Frame.io"
Write-Host "Then click 'Configurar / Login' to enter your Adobe OAuth credentials."
