param(
    [string]$BaseDir = $env:VOICESTUDIO_DIR
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($BaseDir)) {
    throw 'Defina VOICESTUDIO_DIR com a pasta externa da base VoiceStudio.'
}

$BaseDir = (Resolve-Path -LiteralPath $BaseDir).Path
$PythonBase = Join-Path $BaseDir '.venv\Scripts\python.exe'
$EntradaBase = Join-Path $BaseDir 'backend\main.py'
$Porta = if ($env:OMNIVOICE_PORT) { [int]$env:OMNIVOICE_PORT } else { 3900 }

if (-not (Test-Path -LiteralPath $EntradaBase)) {
    throw "backend\main.py nao encontrado em $BaseDir"
}
if (-not (Test-Path -LiteralPath $PythonBase)) {
    throw 'Ambiente da base ausente. Prepare a base fora deste script antes de subir.'
}
if (Get-NetTCPConnection -LocalPort $Porta -State Listen -ErrorAction SilentlyContinue) {
    throw "Ja existe uma instancia ouvindo na porta $Porta."
}

Push-Location -LiteralPath $BaseDir
try {
    & $PythonBase -m uvicorn backend.main:app --host 127.0.0.1 --port $Porta
    if ($LASTEXITCODE -ne 0) {
        throw "A base encerrou com codigo $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
