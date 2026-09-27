$ErrorActionPreference = 'Stop'

$RaizProjeto = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$Porta = if ($env:ESTUDIO_PORT) { [int]$env:ESTUDIO_PORT } else { 7800 }

if (Get-NetTCPConnection -LocalPort $Porta -State Listen -ErrorAction SilentlyContinue) {
    throw "Ja existe uma instancia ouvindo na porta $Porta."
}

Push-Location -LiteralPath $RaizProjeto
try {
    & python -m uvicorn app.servidor:app --host 127.0.0.1 --port $Porta
    if ($LASTEXITCODE -ne 0) {
        throw "O app encerrou com codigo $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
