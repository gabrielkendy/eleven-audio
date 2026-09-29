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
# Modo offline: a base, por padrao, consulta o HuggingFace a cada geracao para
# checar metadados de modelo. Medido em 28/09/2026: sem estes tres, a geracao
# abria uma conexao HTTPS externa (CloudFront); com eles, zero conexao externa e
# a geracao continua identica. Os modelos aqui ja estao em disco, entao nao ha o
# que baixar. Fica documentado que a solucao roda sem internet.
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
# A base tem o venv dela. PYTHONPATH herdado de fora pode fazer outro
# site-packages sombrear o do projeto e derrubar o import na largada. Medido em
# 29/09/2026: "No module named 'pydantic_core._pydantic_core'".
$env:PYTHONPATH = $null
try {
    & $PythonBase -m uvicorn backend.main:app --host 127.0.0.1 --port $Porta
    if ($LASTEXITCODE -ne 0) {
        throw "A base encerrou com codigo $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
