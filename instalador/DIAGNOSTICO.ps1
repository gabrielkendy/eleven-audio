# Diagnostico do ELEVEN AUDIO.
#
# Existe por um motivo pratico: o instalador roda na maquina de OUTRA pessoa, e
# ninguem do lado de ca enxerga a tela dela. Entao este script olha tudo o que
# costuma dar errado e grava num arquivo unico, que a pessoa manda de volta.
#
# Nao instala, nao corrige e nao apaga NADA. So le e escreve o relatorio.
#
# Roda pelo DIAGNOSTICO.bat, ou na mao:
#   powershell -NoProfile -ExecutionPolicy Bypass -File instalar\DIAGNOSTICO.ps1

[CmdletBinding()]
param(
    [string]$Saida,
    # Nao abre o Bloco de Notas no fim. Serve para rodar sem interface (script,
    # verificacao automatizada) e para quem so quer o arquivo.
    [switch]$SemAbrir
)

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

$Raiz = $PSScriptRoot
if (-not $Raiz) { $Raiz = Split-Path -Parent $MyInvocation.MyCommand.Path }
$PastaApp = Split-Path -Parent $Raiz

if (-not $Saida) {
    $Saida = Join-Path ([Environment]::GetFolderPath('Desktop')) 'ELEVEN-AUDIO-diagnostico.txt'
}

$linhas = New-Object System.Collections.ArrayList
function Escrever([string]$t) {
    [void]$linhas.Add($t)
    Write-Host $t
}
function Secao([string]$t) {
    Escrever ''
    Escrever ('=' * 66)
    Escrever "  $t"
    Escrever ('=' * 66)
}
function Item([string]$rotulo, [string]$valor) {
    Escrever ("  {0,-26} {1}" -f $rotulo, $valor)
}

Write-Host ''
Write-Host '   ELEVEN AUDIO  -  diagnostico' -ForegroundColor Cyan
Write-Host '   Vou apenas olhar. Nada sera alterado.' -ForegroundColor Gray

# ---------------------------------------------------------------- cabecalho

Secao 'QUANDO E ONDE'
Item 'data' (Get-Date -Format 'dd/MM/yyyy HH:mm:ss')
Item 'maquina' $env:COMPUTERNAME
Item 'usuario' $env:USERNAME
Item 'pasta do app' $PastaApp
Item 'pasta do instalador' $Raiz
Item 'relatorio' $Saida

# ---------------------------------------------------------------- sistema

Secao 'SISTEMA'
try {
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
    Item 'windows' $os.Caption
    Item 'versao' $os.Version
    Item 'arquitetura' $env:PROCESSOR_ARCHITECTURE
    Item 'ram total' ("{0:N1} GB" -f ($os.TotalVisibleMemorySize / 1MB))
} catch {
    Item 'windows' "erro ao ler: $($_.Exception.Message)"
}

$unidade = (Split-Path $PastaApp -Qualifier)
try {
    $d = Get-PSDrive $unidade.TrimEnd(':')
    Item "disco $unidade livre" ("{0:N1} GB" -f ($d.Free / 1GB))
} catch {
    Item 'disco' 'erro ao ler'
}

# ---------------------------------------------------------------- ferramentas

Secao 'FERRAMENTAS QUE O INSTALADOR USA'

foreach ($par in @(@('git', '--version'), @('ffmpeg', '-version'), @('uv', '--version'))) {
    $nome = $par[0]
    $cmd = Get-Command $nome -ErrorAction SilentlyContinue
    if ($cmd) {
        try {
            # NAO usar $saida aqui: colide com o parametro $Saida (o PowerShell
            # ignora maiuscula/minuscula). Foi o que gravou o relatorio num arquivo
            # chamado "uv 0.12.0 ...".
            $textoVersao = & $nome $par[1] 2>&1 | Select-Object -First 1
            Item $nome ("$textoVersao")
            Item "  caminho de $nome" $cmd.Source
        } catch {
            Item $nome 'existe mas nao respondeu'
        }
    } else {
        Item $nome 'NAO ENCONTRADO'
    }
}

# ---------------------------------------------------------------- pythons

Secao 'PYTHONS NA MAQUINA'
$todos = @()
foreach ($n in @('python', 'python3', 'py')) {
    $cmd = Get-Command $n -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    try {
        $v = & $n -c "import sys; print('%d.%d.%d' % sys.version_info[:3])" 2>$null
        $exe = $cmd.Source
        # venv alheio: o instalador descarta de proposito
        $venvRaiz = Split-Path -Parent (Split-Path -Parent $exe)
        $deVenv = Test-Path -LiteralPath (Join-Path $venvRaiz 'pyvenv.cfg')
        $todos += [PSCustomObject]@{ Nome = $n; Versao = $v; Caminho = $exe; Venv = $deVenv }
    } catch { }
}
if ($todos.Count -eq 0) {
    Item 'nenhum python' 'o instalador vai instalar o 3.13'
} else {
    foreach ($p in $todos) {
        $marca = if ($p.Venv) { '  (de um venv alheio, descartado)' } else { '' }
        Escrever ("  {0,-8} {1,-12} {2}{3}" -f $p.Nome, $p.Versao, $p.Caminho, $marca)
    }
    $bons = $todos | Where-Object { -not $_.Venv -and $_.Versao -match '^3\.(1[123])\.' }
    if ($bons) {
        Item '-> o instalador usaria' ("$($bons[0].Versao)  $($bons[0].Caminho)")
    } else {
        Item '-> problema' 'nenhum Python 3.11-3.13 fora de venv (o torch nao tem build para 3.14+)'
    }
}

# ---------------------------------------------------------------- gpu

Secao 'PLACA DE VIDEO'
try {
    $gpus = Get-CimInstance Win32_VideoController -ErrorAction Stop
    foreach ($g in $gpus) {
        $mem = if ($g.AdapterRAM) { "{0:N1} GB" -f ($g.AdapterRAM / 1GB) } else { '?' }
        Escrever ("  {0}   ({1})" -f $g.Name, $mem)
    }
    $nvidia = $gpus | Where-Object { $_.Name -match 'NVIDIA' }
    if ($nvidia) {
        Item '-> NVIDIA presente' 'o motor usa CUDA'
        $nvsmi = Get-Command 'nvidia-smi' -ErrorAction SilentlyContinue
        if ($nvsmi) {
            try {
                $mem = & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>&1 | Select-Object -First 2
                foreach ($l in $mem) { Escrever "     nvidia-smi: $l" }
            } catch { Escrever '     nvidia-smi existe mas nao respondeu' }
        } else {
            Escrever '     nvidia-smi NAO encontrado (driver pode estar faltando)'
        }
    } else {
        Item '-> sem NVIDIA' 'vai rodar na CPU, bem mais devagar'
    }
} catch {
    Item 'gpu' "erro ao ler: $($_.Exception.Message)"
}

# ---------------------------------------------------------------- instalacao

Secao 'O QUE FOI INSTALADO'

$local = Join-Path $Raiz 'local.ps1'
if (Test-Path -LiteralPath $local) {
    Item 'local.ps1' 'existe'
    Escrever ''
    Escrever '  --- conteudo do local.ps1 ---'
    Get-Content -LiteralPath $local | ForEach-Object { Escrever "  $_" }
    Escrever ''
} else {
    Item 'local.ps1' 'NAO EXISTE (o INSTALAR nao terminou)'
}

# o instalador clona a base ao lado da pasta do app
$pastaBase = Join-Path (Split-Path -Parent $PastaApp) 'base-voicestudio'
if (-not (Test-Path -LiteralPath $pastaBase)) {
    $pastaBase = Join-Path $PastaApp 'base-voicestudio'
}
Item 'esperado da base' $pastaBase
if (Test-Path -LiteralPath $pastaBase) {
    Item 'base baixada' 'sim'
    Item '  tem backend/' (Test-Path (Join-Path $pastaBase 'backend'))
    Item '  tem uv.lock' (Test-Path (Join-Path $pastaBase 'uv.lock'))
    $pyBase = Join-Path $pastaBase '.venv\Scripts\python.exe'
    Item '  tem .venv' (Test-Path -LiteralPath $pyBase)
    if (Test-Path -LiteralPath $pyBase) {
        try {
            $v = & $pyBase -c "import sys; print(sys.version.split()[0])" 2>&1
            Item '  python da base' $v
            # as duas importacoes que decidem se a base sobe
            foreach ($mod in @('torch', 'torchaudio', 'fastapi')) {
                $r = & $pyBase -c "import $mod; print(getattr($mod,'__version__','ok'))" 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Item "  importa $mod" $r
                } else {
                    Item "  importa $mod" "FALHOU: $r"
                }
            }
            $cuda = & $pyBase -c "import torch; print(torch.cuda.is_available())" 2>&1
            Item '  CUDA ativo' $cuda
        } catch {
            Item '  python da base' "erro: $($_.Exception.Message)"
        }
    }
} else {
    Item 'base baixada' 'NAO (o clone falhou ou foi pulado)'
}

$venvApp = Join-Path $PastaApp '.venv'
Item 'venv do app' (Test-Path (Join-Path $venvApp 'Scripts\python.exe'))
if (Test-Path (Join-Path $venvApp 'Scripts\python.exe')) {
    $pyApp = Join-Path $venvApp 'Scripts\python.exe'
    foreach ($mod in @('fastapi', 'uvicorn', 'httpx')) {
        $r = & $pyApp -c "import $mod; print('ok')" 2>&1
        if ($LASTEXITCODE -eq 0) { Item "  importa $mod" 'ok' }
        else { Item "  importa $mod" "FALHOU: $r" }
    }
}

# as pastas onde o app guarda as coisas
foreach ($p in @('app', 'web', 'requirements.txt')) {
    Item "  tem $p" (Test-Path (Join-Path $PastaApp $p))
}

# ---------------------------------------------------------------- servicos

Secao 'SERVICOS NO AR AGORA'

function Sondar([string]$url) {
    try {
        $r = Invoke-WebRequest -Uri $url -Method Get -UseBasicParsing `
             -TimeoutSec 6 -MaximumRedirection 0 -ErrorAction Stop
        return "HTTP $($r.StatusCode)"
    } catch {
        # qualquer resposta HTTP ja prova servidor de pe
        if ($_.Exception.Response) { return "HTTP $([int]$_.Exception.Response.StatusCode)" }
        return 'sem resposta'
    }
}

$portaBase = 3900
$portaApp = 7800
if (Test-Path -LiteralPath $local) {
    $conteudo = Get-Content -LiteralPath $local -Raw
    if ($conteudo -match '\$PortaBase\s*=\s*(\d+)') { $portaBase = [int]$Matches[1] }
    if ($conteudo -match '\$PortaApp\s*=\s*(\d+)')  { $portaApp  = [int]$Matches[1] }
}

Item "base  ($portaBase)" (Sondar "http://127.0.0.1:$portaBase/health")
Item "app   ($portaApp)" (Sondar "http://127.0.0.1:$portaApp/api/saude")
Escrever ''
Escrever '  se o app responde, o corpo dele diz o resto:'
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$portaApp/api/saude" -UseBasicParsing -TimeoutSec 8
    Escrever "    $($r.Content)"
} catch {
    Escrever "    (nao consegui ler: $($_.Exception.Message))"
}

# ---------------------------------------------------------------- modelos

Secao 'MODELOS JA BAIXADOS'
$hf = Join-Path $env:USERPROFILE '.cache\huggingface\hub'
if (Test-Path -LiteralPath $hf) {
    $itens = Get-ChildItem -LiteralPath $hf -Directory -ErrorAction SilentlyContinue
    if ($itens) {
        foreach ($d in $itens) {
            $tam = (Get-ChildItem -LiteralPath $d.FullName -Recurse -File -ErrorAction SilentlyContinue |
                    Measure-Object -Property Length -Sum).Sum
            Escrever ("  {0,8:N0} MB  {1}" -f ($tam / 1MB), $d.Name)
        }
    } else {
        Escrever '  pasta existe mas esta vazia (baixa na primeira geracao)'
    }
} else {
    Escrever '  nada ainda. Os modelos baixam na primeira vez que gerar audio.'
}

# ---------------------------------------------------------------- logs

Secao 'ULTIMAS LINHAS DE LOG (se houver)'
$achouLog = $false
$candidatos = @(
    (Join-Path $pastaBase 'logs'),
    (Join-Path $PastaApp 'logs'),
    (Join-Path $env:APPDATA 'OmniVoice')
)
foreach ($c in $candidatos) {
    if (-not (Test-Path -LiteralPath $c)) { continue }
    $arqs = Get-ChildItem -LiteralPath $c -Filter '*.log*' -File -Recurse -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending | Select-Object -First 3
    foreach ($a in $arqs) {
        $achouLog = $true
        Escrever ''
        Escrever "  --- $($a.FullName)  ($($a.LastWriteTime)) ---"
        Get-Content -LiteralPath $a.FullName -Tail 25 -ErrorAction SilentlyContinue |
            ForEach-Object { Escrever "    $_" }
    }
}
if (-not $achouLog) { Escrever '  nenhum log encontrado' }

# ---------------------------------------------------------------- fim

Secao 'FIM'
Escrever '  Manda este arquivo inteiro de volta. Ele nao tem senha nem nada seu'
Escrever '  alem dos caminhos da sua propria maquina.'
Escrever ''

# utf-8 com BOM: abre certo no Bloco de Notas do Windows
[System.IO.File]::WriteAllText($Saida, ($linhas -join "`r`n"),
    (New-Object System.Text.UTF8Encoding $true))

Write-Host ''
Write-Host '   Relatorio gravado em:' -ForegroundColor Green
Write-Host "   $Saida" -ForegroundColor White
Write-Host ''
if (-not $SemAbrir) {
    Write-Host '   Abrindo...' -ForegroundColor Gray
    Start-Process notepad.exe $Saida
}
