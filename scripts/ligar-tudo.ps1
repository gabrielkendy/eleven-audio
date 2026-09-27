param()

$ErrorActionPreference = 'Stop'
$VoiceStudioPadrao = 'C:\Users\Gabriel\Downloads\YOUTUBE KENDY\02-EM-PRODUCAO\SÉRIE · ENGENHARIA REVERSA DE PRODUTO\2-MATERIAIS-DA-SOLUCAO\4-BASE-VOICESTUDIO'
$PythonProjetoPadrao = 'C:\Users\Gabriel\.venvs\eleven-audio\Scripts\python.exe'
$TempoLimiteSegundos = 180

$RaizProjeto = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$PastaLogs = Join-Path $RaizProjeto 'dados\logs'
$ArquivoLog = Join-Path $PastaLogs 'ligar-tudo.log'
$JobsIniciados = @()

New-Item -ItemType Directory -Path $PastaLogs -Force | Out-Null

function Registrar([string]$Mensagem) {
    $Linha = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $Mensagem"
    Write-Host $Mensagem
    Add-Content -LiteralPath $ArquivoLog -Value $Linha -Encoding UTF8
}

function Testar-Url([string]$Url) {
    try {
        $Resposta = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return $Resposta.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Aguardar-Url([string]$Nome, [string]$Url, [System.Management.Automation.Job]$Job) {
    $Limite = (Get-Date).AddSeconds($TempoLimiteSegundos)
    while ((Get-Date) -lt $Limite) {
        if (Testar-Url $Url) {
            Registrar "$Nome respondeu em $Url."
            return
        }
        if ($null -ne $Job -and $Job.State -in @('Completed', 'Failed', 'Stopped')) {
            $Saida = (Receive-Job -Job $Job -ErrorAction SilentlyContinue | Out-String).Trim()
            throw "$Nome encerrou antes de responder. $Saida"
        }
        Start-Sleep -Seconds 1
    }
    throw "Tempo esgotado esperando $Nome em $Url. Limite: $TempoLimiteSegundos segundos."
}

try {
    $UrlBase = 'http://127.0.0.1:3900/health'
    $UrlApp = 'http://127.0.0.1:7800/api/saude'

    if (Testar-Url $UrlBase) {
        Registrar 'Base ja esta no ar. Nao foi iniciada outra instancia.'
        $JobBase = $null
    }
    else {
        $BaseDir = if ($env:VOICESTUDIO_DIR) { $env:VOICESTUDIO_DIR } else { $VoiceStudioPadrao }
        $BaseDir = (Resolve-Path -LiteralPath $BaseDir).Path
        $PythonBase = Join-Path $BaseDir '.venv\Scripts\python.exe'
        if (-not (Test-Path -LiteralPath $PythonBase)) {
            throw "Python da base nao encontrado em $PythonBase. Confira VOICESTUDIO_DIR."
        }
        if (-not (Test-Path -LiteralPath (Join-Path $BaseDir 'backend\main.py'))) {
            throw "backend\main.py nao encontrado em $BaseDir."
        }
        Registrar "Iniciando a base em $BaseDir."
        $JobBase = Start-Job -ScriptBlock {
            param($Diretorio, $Python)
            Set-Location -LiteralPath $Diretorio
            & $Python -m uvicorn backend.main:app --host 127.0.0.1 --port 3900
        } -ArgumentList $BaseDir, $PythonBase
        $JobsIniciados += $JobBase
        Aguardar-Url 'Base' $UrlBase $JobBase
    }

    if (Testar-Url $UrlApp) {
        Registrar 'Nosso app ja esta no ar. Nao foi iniciada outra instancia.'
        $JobApp = $null
    }
    else {
        $PythonProjeto = if ($env:ESTUDIO_PYTHON) { $env:ESTUDIO_PYTHON } else { $PythonProjetoPadrao }
        if (-not (Test-Path -LiteralPath $PythonProjeto)) {
            throw "Python do projeto nao encontrado em $PythonProjeto."
        }
        Registrar 'Iniciando o Estudio de Voz Local.'
        $JobApp = Start-Job -ScriptBlock {
            param($Diretorio, $Python)
            Set-Location -LiteralPath $Diretorio
            & $Python -m uvicorn app.servidor:app --host 127.0.0.1 --port 7800
        } -ArgumentList $RaizProjeto, $PythonProjeto
        $JobsIniciados += $JobApp
        Aguardar-Url 'Nosso app' $UrlApp $JobApp
    }

    Registrar 'Estudio pronto. Abrindo http://127.0.0.1:7800 no navegador.'
    Start-Process 'http://127.0.0.1:7800'

    if ($JobsIniciados.Count -gt 0) {
        Registrar 'Mantenha esta janela aberta enquanto usa. Fechar a janela desliga o estudio.'
        Wait-Job -Job $JobsIniciados -Any | Out-Null
        throw 'Um dos servicos encerrou. Consulte o log e tente ligar novamente.'
    }
    Registrar 'Os dois servicos ja estavam ativos. Nenhum processo duplicado foi criado.'
}
catch {
    Registrar "ERRO: $($_.Exception.Message)"
    exit 1
}
finally {
    foreach ($Job in $JobsIniciados) {
        Stop-Job -Job $Job -ErrorAction SilentlyContinue
        Remove-Job -Job $Job -Force -ErrorAction SilentlyContinue
    }
}
