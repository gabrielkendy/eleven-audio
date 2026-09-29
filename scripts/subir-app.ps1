$ErrorActionPreference = 'Stop'

$RaizProjeto = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$Porta = if ($env:ESTUDIO_PORT) { [int]$env:ESTUDIO_PORT } else { 7800 }

# Ajustes locais da maquina, os mesmos que o ligar-tudo.ps1 usa. Sem isto este
# script ignorava o local.ps1 e caia num "python" qualquer do PATH.
$AjustesLocais = Join-Path $PSScriptRoot 'local.ps1'
if (Test-Path -LiteralPath $AjustesLocais) { . $AjustesLocais }

# O app tem venv proprio, e "python" do PATH pode ser outro, sem as dependencias
# do projeto. Ordem: ESTUDIO_PYTHON > ajuste local > .venv do repositorio > PATH.
$Python = if ($env:ESTUDIO_PYTHON) { $env:ESTUDIO_PYTHON }
          elseif (-not [string]::IsNullOrWhiteSpace($PythonProjetoPadrao)) { $PythonProjetoPadrao }
          else { Join-Path $RaizProjeto '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $Python)) { $Python = 'python' }

if (Get-NetTCPConnection -LocalPort $Porta -State Listen -ErrorAction SilentlyContinue) {
    throw "Ja existe uma instancia ouvindo na porta $Porta."
}

# PYTHONPATH herdado de fora sombreia o site-packages do projeto e o import
# quebra na largada. Medido em 29/09/2026 com o estudio aberto por dentro de
# outro processo: "No module named 'pydantic_core._pydantic_core'".
$env:PYTHONPATH = $null

Push-Location -LiteralPath $RaizProjeto
try {
    & $Python -m uvicorn app.servidor:app --host 127.0.0.1 --port $Porta
    if ($LASTEXITCODE -ne 0) {
        throw "O app encerrou com codigo $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
