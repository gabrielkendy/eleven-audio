# Sobe a base e o app, espera os dois responderem e abre o navegador.
#
# Le os caminhos de local.ps1, que o instalador gravou. Se este arquivo for rodado
# de dentro de outra pasta, ele procura o local.ps1 ao lado dele mesmo.

[CmdletBinding()]
param(
    [switch]$SemNavegador,
    [switch]$Reiniciar
)

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

$Raiz = $PSScriptRoot
if (-not $Raiz) { $Raiz = Split-Path -Parent $MyInvocation.MyCommand.Path }

# --- ajustes da maquina: TODOS os scripts leem este mesmo arquivo ---
$Ajustes = Join-Path $Raiz 'local.ps1'
if (-not (Test-Path -LiteralPath $Ajustes)) {
    Write-Host ''
    Write-Host '   Nao achei o local.ps1.' -ForegroundColor Red
    Write-Host '   Rode o INSTALAR.bat primeiro.' -ForegroundColor Gray
    Write-Host ''
    Read-Host '   Enter para fechar'
    exit 1
}
. $Ajustes

$PortaBase = if ($PortaBase) { $PortaBase } else { 3900 }
$PortaApp = if ($PortaApp) { $PortaApp } else { 7800 }

function Linha([string]$t) { Write-Host "   $t" }
function Ok([string]$t)    { Write-Host "   [ok]   $t" -ForegroundColor Green }
function Mal([string]$t)   { Write-Host "   [erro] $t" -ForegroundColor Red }
function Info([string]$t)  { Write-Host "          $t" -ForegroundColor DarkGray }

# Sonda o servico pelo endpoint de saude dele, nao pela raiz.
#
# Dois defeitos medidos aqui em 29/09/2026, e os dois davam FALSO NEGATIVO:
#   1. A raiz da base responde 307 (redireciona). O Invoke-WebRequest SEGUE o
#      redirect por padrao, estoura, e o script concluia que a base nao subiu.
#   2. Qualquer resposta HTTP ja prova que o servidor esta de pe. Um 404 e prova
#      de servidor vivo, nao de servidor morto.
# Por isso: endpoint de saude + MaximumRedirection 0 + aceitar erro com Resposta.
function PortaViva([int]$p, [string]$caminho) {
    if (-not $caminho) { $caminho = '/' }
    $url = "http://127.0.0.1:$p$caminho"
    try {
        $r = Invoke-WebRequest -Uri $url -Method Get -UseBasicParsing `
             -TimeoutSec 4 -MaximumRedirection 0 -ErrorAction Stop
        return ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500)
    } catch {
        if ($_.Exception.Response) { return $true }   # 307, 404: servidor no ar
        return $false                                  # nem conexao houve
    }
}

function BaseViva { return (PortaViva $PortaBase '/health') }
function AppVivo  { return (PortaViva $PortaApp  '/api/saude') }

function Esperar([int]$p, [string]$nome, [int]$segundos, [string]$caminho) {
    for ($i = 1; $i -le $segundos; $i++) {
        if (PortaViva $p $caminho) { return $true }
        Start-Sleep -Seconds 1
        if ($i % 10 -eq 0) { Info "$nome ainda subindo... ($i s)" }
    }
    return $false
}

function MatarPorta([int]$p) {
    try {
        $linhas = netstat -ano | Select-String ":$p\s" | Select-String 'LISTENING'
        foreach ($l in $linhas) {
            # NAO usar $pid: no PowerShell essa variavel e reservada (somente leitura,
            # e o id do processo atual). Atribuir nela estoura em tempo de execucao.
            $idProc = ($l -split '\s+')[-1]
            if ($idProc -match '^\d+$' -and $idProc -ne '0') {
                Stop-Process -Id ([int]$idProc) -Force -ErrorAction SilentlyContinue
            }
        }
    } catch { }
}

Write-Host ''
Write-Host '   ELEVEN AUDIO' -ForegroundColor Cyan
Write-Host ''

if ($Reiniciar) {
    Linha 'encerrando o que estiver no ar...'
    MatarPorta $PortaBase
    MatarPorta $PortaApp
    Start-Sleep -Seconds 2
}

# --- ja esta no ar? abre e sai, sem subir de novo ---
$baseViva = BaseViva
$appVivo  = AppVivo

if ($baseViva -and $appVivo) {
    Ok 'os dois servicos ja estao no ar'
    Info "estudio:  http://127.0.0.1:$PortaApp"
    if (-not $SemNavegador) { Start-Process "http://127.0.0.1:$PortaApp" }
    Start-Sleep -Seconds 2
    exit 0
}

# So cobra o Python se for REALMENTE preciso subir algo. Servico ja no ar nao
# depende de achar o interpretador: evita erro em quem so quer reabrir a tela.
if (-not $PythonBase -or -not (Test-Path -LiteralPath $PythonBase)) {
    Mal 'nao achei o Python da base'
    Info "esperado em: $PythonBase"
    Info 'rode o INSTALAR.bat de novo'
    Read-Host '   Enter para fechar'
    exit 1
}
if (-not $PythonApp -or -not (Test-Path -LiteralPath $PythonApp)) {
    Mal 'nao achei o Python do app'
    Info "esperado em: $PythonApp"
    Read-Host '   Enter para fechar'
    exit 1
}

# --- base ---
if (-not $baseViva) {
    Linha 'subindo a base (o motor do estudio)...'
    Info 'a primeira subida demora mais, ela carrega os modelos'
    $env:HF_HUB_OFFLINE = '1'
    $env:TRANSFORMERS_OFFLINE = '1'
    $env:HF_HUB_DISABLE_TELEMETRY = '1'
    $env:PYTHONPATH = $null
    Start-Process -FilePath $PythonBase `
        -ArgumentList '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', "$PortaBase" `
        -WorkingDirectory $PastaBase -WindowStyle Minimized
} else {
    Ok 'base ja estava no ar'
}

if (-not (Esperar $PortaBase 'base' 180 '/health')) {
    Mal "a base nao respondeu em 3 minutos"
    Info 'tente abrir a pasta da base e rodar de novo pelo ABRIR'
    Info "log: $PastaBase\logs"
    Read-Host '   Enter para fechar'
    exit 1
}
Ok "base no ar na porta $PortaBase"

# --- app ---
if (-not $appVivo) {
    Linha 'subindo o estudio...'
    $env:PYTHONPATH = $null
    Start-Process -FilePath $PythonApp `
        -ArgumentList '-m', 'uvicorn', 'app.servidor:app', '--host', '127.0.0.1', '--port', "$PortaApp" `
        -WorkingDirectory $PastaApp -WindowStyle Minimized
} else {
    Ok 'estudio ja estava no ar'
}

if (-not (Esperar $PortaApp 'estudio' 120 '/api/saude')) {
    Mal 'o estudio nao respondeu em 2 minutos'
    Read-Host '   Enter para fechar'
    exit 1
}

Write-Host ''
Ok 'TUDO PRONTO'
Write-Host "          http://127.0.0.1:$PortaApp" -ForegroundColor White
Write-Host ''
Info 'para encerrar, use o FECHAR.bat'

if (-not $SemNavegador) { Start-Process "http://127.0.0.1:$PortaApp" }
Start-Sleep -Seconds 3
