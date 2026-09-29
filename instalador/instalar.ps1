# Instalador do ELEVEN AUDIO para Windows
#
# O que este script faz, na ordem:
#   1. confere o que ja existe na maquina (Python, Git, ffmpeg, GPU)
#   2. instala o que falta, pedindo confirmacao antes de baixar qualquer coisa
#   3. clona a base VoiceStudio (AGPL-3.0) do repositorio oficial
#   4. cria os dois ambientes Python e instala as dependencias
#   5. deixa os atalhos de abrir e fechar prontos
#
# O que ele NAO faz: nao baixa modelo nenhum. Os modelos vem do HuggingFace na
# primeira vez que a pessoa gera audio, porque assim o download retoma de onde
# parou e a pessoa so baixa o motor que ela escolher.
#
# Nada aqui sai da maquina da pessoa, exceto os downloads de instalacao.

[CmdletBinding()]
param(
    [string]$PastaInstalacao = (Join-Path $env:USERPROFILE 'ELEVEN-AUDIO'),
    [string]$BaseUrl = 'https://github.com/debpalash/VoiceStudio.git',
    [string]$BaseTag = 'main',
    [switch]$SemPerguntar,
    [switch]$SoVerificar
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# ---------------------------------------------------------------- apresentacao

$L = 68
function Titulo([string]$t) {
    Write-Host ''
    Write-Host ('  ' + ('-' * $L)) -ForegroundColor DarkGray
    Write-Host "  $t" -ForegroundColor White
    Write-Host ('  ' + ('-' * $L)) -ForegroundColor DarkGray
}
function Ok([string]$t)    { Write-Host "   [ok]   $t" -ForegroundColor Green }
function Falta([string]$t) { Write-Host "   [--]   $t" -ForegroundColor Yellow }
function Mal([string]$t)   { Write-Host "   [erro] $t" -ForegroundColor Red }
function Nota([string]$t)  { Write-Host "          $t" -ForegroundColor DarkGray }

function Perguntar([string]$t) {
    if ($SemPerguntar) { return $true }
    $r = Read-Host "   $t [S/n]"
    return ($r -eq '' -or $r -match '^[sSyY]')
}

# ---------------------------------------------------------------- utilidades

function TemComando([string]$nome) {
    return [bool](Get-Command $nome -ErrorAction SilentlyContinue)
}

function ViaWinget([string]$id, [string]$descricao) {
    if (-not (TemComando 'winget')) {
        Mal "winget nao esta disponivel nesta maquina; instale $descricao na mao."
        return $false
    }
    if (-not (Perguntar "Posso instalar $descricao agora via winget?")) {
        Falta "$descricao nao instalado (voce escolheu nao)"
        return $false
    }
    Write-Host "          instalando $descricao..." -ForegroundColor DarkGray
    winget install --id $id -e --accept-source-agreements --accept-package-agreements --silent
    # o PATH so atualiza em sessao nova; recarrega a partir do registro
    $env:PATH = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                [Environment]::GetEnvironmentVariable('Path', 'User')
    return $true
}

# A base pede >=3.11, mas "mais novo" nao e melhor: o torch (que a base precisa)
# publica pacote pronto para 3.11, 3.12 e 3.13. O 3.14 costuma ficar meses sem
# build, e o erro so aparece no meio da instalacao, quando ja baixou GB.
# Por isso a faixa preferida e 3.11 a 3.13, e o 3.14+ so entra como ultimo recurso.
$SCRIPT:PyMin = 11
$SCRIPT:PyMax = 13
# versao que o uv vai baixar e gerenciar para a base (independente do sistema)
$SCRIPT:PyAlvoBase = '3.13'

# Descarta Python que pertence ao ambiente privado de OUTRO programa (um venv).
# Sem isto o instalador pega o primeiro python do PATH, que pode ser o de um app
# qualquer, e instala as dependencias da base DENTRO do ambiente alheio —
# corrompendo o outro programa. Um venv se reconhece pelo pyvenv.cfg ao lado.
function EhPythonDeVenv([string]$exe) {
    try {
        $scripts = Split-Path -Parent $exe          # ...\<venv>\Scripts
        $raiz    = Split-Path -Parent $scripts      # ...\<venv>
        if (Test-Path -LiteralPath (Join-Path $raiz 'pyvenv.cfg')) { return $true }
        if ($exe -match '\\venv\\|\\\.venv\\|site-packages') { return $true }
    } catch { }
    return $false
}

function AcharPython {
    # ATENCAO: nao usar array de pares com Sort-Object. O pipeline do PowerShell
    # DESENROLA o array, e o par (exe, versao) vira dois itens soltos. Foi o que
    # fez isto devolver a string do caminho em vez do par. Objeto nomeado resolve.
    $bons = New-Object System.Collections.ArrayList
    $novos = New-Object System.Collections.ArrayList

    foreach ($n in @('python', 'python3', 'py')) {
        if (-not (TemComando $n)) { continue }
        try {
            $v = & $n -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
            if (-not $v -or $v -notmatch '^(\d+)\.(\d+)$') { continue }
            $exe = (Get-Command $n).Source
            $maior = [int]$Matches[1]
            $menor = [int]$Matches[2]
            if ($maior -ne 3) { continue }
            if (EhPythonDeVenv $exe) { continue }
            $item = [PSCustomObject]@{
                Exe     = $exe
                Versao  = $v
                Numero  = [version]$v
                Caminho = $exe
            }
            if ($menor -ge $SCRIPT:PyMin -and $menor -le $SCRIPT:PyMax) {
                [void]$bons.Add($item)
            } elseif ($menor -gt $SCRIPT:PyMax) {
                [void]$novos.Add($item)
            }
        } catch { }
    }

    if ($bons.Count -gt 0) {
        $script:PyAviso = $null
        return ($bons | Sort-Object -Property Numero -Descending | Select-Object -First 1)
    }
    if ($novos.Count -gt 0) {
        $escolhido = ($novos | Sort-Object -Property Numero -Descending | Select-Object -First 1)
        $script:PyAviso = "so encontrei Python $($escolhido.Versao); a base espera 3.$SCRIPT:PyMax ou menor"
        return $escolhido
    }
    return $null
}

# ---------------------------------------------------------------- passos

function Passo1_Conferir {
    Titulo 'PASSO 1 de 5  -  O que esta maquina ja tem'

    $script:Falhas = @()

    # Windows
    $wv = [Environment]::OSVersion.Version
    if ($wv.Major -lt 10) { $script:Falhas += 'Windows 10 ou mais novo' }
    Ok "Windows $($wv.Major).$($wv.Minor)"

    # arquitetura
    if ($env:PROCESSOR_ARCHITECTURE -notmatch '64') {
        Mal "arquitetura $env:PROCESSOR_ARCHITECTURE: a base precisa de 64 bits"
        $script:Falhas += 'Windows 64 bits'
    } else {
        Ok "arquitetura $env:PROCESSOR_ARCHITECTURE"
    }

    # Python
    $script:Py = AcharPython
    if ($script:Py) {
        if ($script:PyAviso) {
            Falta $script:PyAviso
            Nota 'o torch ainda nao publica pacote para esta versao'
            $script:Falhas += 'python 3.11-3.13'
        } else {
            Ok "Python $($script:Py.Versao)"
            Nota $script:Py.Exe
        }
    } else {
        Falta 'Python 3.11, 3.12 ou 3.13'
        $script:Falhas += 'python'
    }

    # Git
    if (TemComando 'git') {
        Ok "Git $((git --version) -replace 'git version ','')"
    } else {
        Falta 'Git (necessario para baixar a base)'
        $script:Falhas += 'git'
    }

    # ffmpeg
    if (TemComando 'ffmpeg') {
        Ok "ffmpeg"
    } else {
        Falta 'ffmpeg (converte e corta o audio)'
        $script:Falhas += 'ffmpeg'
    }

    # GPU
    $gpu = $null
    try {
        $gpu = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue |
               Where-Object { $_.Name -match 'NVIDIA|Radeon|AMD' } | Select-Object -First 1
    } catch { }
    if ($gpu) {
        $mem = if ($gpu.AdapterRAM) { [math]::Round($gpu.AdapterRAM / 1GB, 1) } else { '?' }
        Ok "GPU: $($gpu.Name)"
        if ($gpu.Name -match 'NVIDIA') {
            Nota 'NVIDIA: a base usa CUDA. Precisa de ~6 GB de VRAM livres para gerar voz.'
        } else {
            Nota 'AMD/Intel: no Windows a base roda so na CPU, bem mais devagar.'
        }
    } else {
        Falta 'GPU dedicada'
        Nota 'roda sem GPU, mas a geracao fica lenta (minutos por trecho)'
    }

    # disco
    $unidade = (Split-Path $PastaInstalacao -Qualifier)
    $livre = (Get-PSDrive $unidade.TrimEnd(':')).Free
    $precisa = 25GB
    if ($livre -lt $precisa) {
        Falta "espaco em disco: $([math]::Round($livre/1GB,1)) GB livre, precisa de 25 GB"
        $script:Falhas += 'espaco em disco'
    } else {
        Ok "espaco em disco: $([math]::Round($livre/1GB,1)) GB livre"
    }

    return ($script:Falhas.Count -eq 0)
}

function Passo2_InstalarFaltando {
    Titulo 'PASSO 2 de 5  -  O que falta'

    if ($script:Falhas.Count -eq 0) {
        Ok 'nada a instalar, a maquina ja tem tudo'
        return $true
    }

    Write-Host "   Vou precisar instalar: $($script:Falhas -join ', ')" -ForegroundColor Yellow
    Nota 'O download e do site oficial da Microsoft e do ffmpeg.org.'

    if (-not (Perguntar 'Posso seguir?')) {
        Mal 'instalacao cancelada por voce'
        return $false
    }

    if ($script:Falhas -contains 'git') {
        if (-not (ViaWinget 'Git.Git' 'Git')) { return $false }
    }
    if ($script:Falhas -contains 'ffmpeg') {
        if (-not (ViaWinget 'Gyan.FFmpeg' 'ffmpeg')) { return $false }
    }
    if ($script:Falhas -contains 'python') {
        if (-not (ViaWinget 'Python.Python.3.13' 'Python 3.13')) { return $false }
        $script:Py = AcharPython
        if (-not $script:Py -or $script:PyAviso) {
            Mal 'Python foi instalado mas nao aparece nesta janela. Feche e rode o INSTALAR de novo.'
            return $false
        }
    }
    elseif ($script:Falhas -contains 'python 3.11-3.13') {
        Write-Host ''
        Nota 'esta maquina tem um Python mais novo que o torch ainda nao acompanha.'
        Nota 'o 3.13 convive com ele, sem mexer no que voce ja usa.'
        if (ViaWinget 'Python.Python.3.13' 'Python 3.13') {
            $script:Py = AcharPython
            if ($script:Py -and -not $script:PyAviso) {
                Ok "agora vou usar o Python $($script:Py.Versao)"
                $script:Falhas = $script:Falhas | Where-Object { $_ -ne 'python 3.11-3.13' }
            } else {
                Mal 'instalei o 3.13 mas ainda nao aparece. Feche e rode o INSTALAR de novo.'
                return $false
            }
        } else {
            return $false
        }
    }

    Ok 'tudo instalado'
    Nota 'se algum programa novo nao for encontrado agora, feche esta janela e rode de novo'
    return $true
}

function Passo3_BaixarBase {
    Titulo 'PASSO 3 de 5  -  A base do estudio (VoiceStudio)'

    $script:PastaBase = Join-Path $PastaInstalacao 'base-voicestudio'

    if (Test-Path (Join-Path $script:PastaBase '.git')) {
        Ok 'a base ja esta baixada'
        return $true
    }

    Write-Host '   A base e o projeto VoiceStudio (AGPL-3.0), de terceiro.' -ForegroundColor Gray
    Nota 'Ela faz o trabalho pesado: clonar voz, gerar fala, separar trilha e dublar.'
    Nota 'O nosso app conversa com ela por rede local, sem modificar o codigo dela.'
    Write-Host ''
    Nota "repositorio: $BaseUrl"
    Nota 'licenca AGPL-3.0: o codigo dela continua aberto. O nosso app (MIT) fica separado.'

    if (-not (Perguntar 'Posso baixar a base?')) {
        Falta 'base nao baixada'
        return $false
    }

    New-Item -ItemType Directory -Force -Path $PastaInstalacao | Out-Null
    Write-Host '          baixando (sem historico, e mais rapido)...' -ForegroundColor DarkGray

    & git clone --depth 1 --branch $BaseTag $BaseUrl $script:PastaBase
    if ($LASTEXITCODE -ne 0) {
        Mal 'o download da base falhou'
        Nota 'confira a internet e rode de novo; o git reaproveita o que ja baixou'
        return $false
    }

    if (-not (Test-Path (Join-Path $script:PastaBase 'backend'))) {
        Mal 'a base baixou mas nao tem a pasta backend'
        return $false
    }

    Ok 'base baixada'
    return $true
}

function Passo4_Ambientes {
    Titulo 'PASSO 4 de 5  -  Os ambientes Python'

    $py = $script:Py.Exe

    # ---- base ----
    # O uv cuida do ambiente E do interpretador. Ele baixa um Python proprio
    # (gerenciado, fora do sistema) na versao exata que funciona, sem mexer no
    # Python que a pessoa ja usa. Por isso nao criamos o venv na mao aqui.
    $venvBase = Join-Path $script:PastaBase '.venv'
    if (Test-Path (Join-Path $venvBase 'Scripts\python.exe')) {
        Ok 'ambiente da base ja existe'
        Nota 'se der erro de modulo faltando mais tarde, apague a pasta .venv da base e rode de novo'
    } else {
        # NAO criar o venv com o python do sistema aqui. O uv escolhe e baixa o
        # interpretador dele (gerenciado), na versao que funciona com o torch.
        # Criar antes com o python do PATH foi o que deixaria o ambiente com a
        # versao errada — e o erro so apareceria no meio do uv sync.

        # A base instala com UV, nao com pip — e a diferenca e funcional.
        # O pyproject dela aponta torch/torchaudio/torchvision para um INDICE
        # PROPRIO de CUDA ([tool.uv.sources]) e trava as versoes testadas em
        # [tool.uv] (torch==2.8.0). O pip IGNORA as duas coisas: pegaria um torch
        # qualquer do PyPI, possivelmente sem CUDA, e a base quebraria depois.
        # `uv sync` le o uv.lock e instala exatamente o conjunto testado.
        if (-not (TemComando 'uv')) {
            Falta 'uv (instalador de pacotes que a base usa)'
            if (Perguntar 'Posso instalar o uv agora?') {
                try {
                    & powershell -NoLogo -NoProfile -ExecutionPolicy Bypass `
                        -Command "irm https://astral.sh/uv/install.ps1 | iex" | Out-Null
                    $env:PATH = "$env:USERPROFILE\.local\bin;" +
                                [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' +
                                [Environment]::GetEnvironmentVariable('Path', 'User')
                } catch { }
            }
            if (-not (TemComando 'uv')) {
                Mal 'o uv nao esta disponivel'
                Nota 'instale por: winget install --id astral-sh.uv -e'
                return $false
            }
        }
        Ok "uv $((& uv --version) -replace 'uv ','')"

        Write-Host '          instalando as dependencias da base (alguns GB, demora)...' -ForegroundColor DarkGray
        Nota 'o torch com CUDA e o maior pacote, uns 3 GB'
        Nota 'o uv cria o .venv sozinho, com a versao exata que o projeto testou'

        Push-Location $script:PastaBase
        try {
            & uv sync --frozen --python $($SCRIPT:PyAlvoBase)
            if ($LASTEXITCODE -ne 0) {
                Nota 'a primeira tentativa falhou; tentando sem --frozen (pode ajustar versoes)'
                & uv sync --python $($SCRIPT:PyAlvoBase)
            }
        } finally {
            Pop-Location
        }
        if ($LASTEXITCODE -ne 0) {
            Mal 'falhou ao instalar as dependencias da base'
            Nota 'rode de novo; o uv continua de onde parou'
            return $false
        }
        Ok 'ambiente da base pronto'
    }

    # ---- app ----
    # O app NAO e uma subpasta de $PastaInstalacao: ele E a pasta que contem este
    # instalador. Quem baixa o zip do repositorio ja tem o app onde ele deve estar,
    # entao a raiz do app e o PAI de instalador/. Depender de um nome fixo aqui foi
    # o defeito que deixaria o app "nao encontrado" em toda instalacao limpa.
    $script:PastaApp = Split-Path -Parent $PSScriptRoot
    if (-not (Test-Path (Join-Path $script:PastaApp 'app\servidor.py'))) {
        # fallback: instalador solto numa pasta junto do app
        $alternativa = Join-Path $PastaInstalacao 'eleven-audio'
        if (Test-Path (Join-Path $alternativa 'app\servidor.py')) {
            $script:PastaApp = $alternativa
        } else {
            Mal 'nao achei o app (procurei app\servidor.py)'
            Nota "procurei em: $(Split-Path -Parent $PSScriptRoot)"
            Nota 'o instalador precisa estar DENTRO da pasta do app'
            return $false
        }
    }
    # o venv do app vive dentro da propria pasta do app, nao solto por ai
    $venvApp = Join-Path $script:PastaApp '.venv'

    if (Test-Path (Join-Path $venvApp 'Scripts\python.exe')) {
        Ok 'ambiente do app ja existe'
    } else {
        Write-Host '          criando o ambiente do app...' -ForegroundColor DarkGray
        $req = Join-Path $script:PastaApp 'requirements.txt'
        if (-not (Test-Path $req)) {
            Mal 'nao achei o requirements.txt do app'
            Nota "procurei em: $req"
            return $false
        }
        # mesmo caminho da base: uv cria o ambiente e escolhe o interpretador.
        # O app e leve (fastapi, httpx, uvicorn), entao isto leva segundos.
        & uv venv $venvApp --python $($SCRIPT:PyAlvoBase)
        if ($LASTEXITCODE -ne 0) { Mal 'nao consegui criar o ambiente do app'; return $false }

        Push-Location $script:PastaApp
        try {
            & uv pip install --python $venvApp -r $req
        } finally {
            Pop-Location
        }
        if ($LASTEXITCODE -ne 0) { Mal 'falhou ao instalar as dependencias do app'; return $false }
        Ok 'ambiente do app pronto'
    }

    $script:PythonBase = Join-Path $venvBase 'Scripts\python.exe'
    $script:PythonApp = Join-Path $venvApp 'Scripts\python.exe'
    return $true
}

function Passo5_Atalhos {
    Titulo 'PASSO 5 de 5  -  Os atalhos'

    $conteudoLocal = @"
# Ajustes desta maquina. Gerado pelo instalador, pode editar a mao.
`$PastaBase         = '$($script:PastaBase)'
`$PythonBase        = '$($script:PythonBase)'
`$PythonApp         = '$($script:PythonApp)'
`$PastaApp          = '$($script:PastaApp)'
`$PortaBase         = 3900
`$PortaApp          = 7800
"@
    # O local.ps1 TEM que ficar na pasta do instalador, porque e ali que o
    # ABRIR.ps1 e o FECHAR.ps1 procuram (ao lado deles mesmos, via $PSScriptRoot).
    # Gravar em $PastaInstalacao foi o defeito que faria o launcher responder
    # "rode o INSTALAR.bat primeiro" para sempre, mesmo com tudo instalado.
    $arqLocal = Join-Path $PSScriptRoot 'local.ps1'
    if (-not $PSScriptRoot) { $arqLocal = Join-Path $PastaInstalacao 'instalador\local.ps1' }
    # utf-8 com BOM: o PowerShell 5.1 le sem BOM como ANSI e corrompe acento
    [System.IO.File]::WriteAllText($arqLocal, $conteudoLocal,
        (New-Object System.Text.UTF8Encoding $true))
    Ok 'ajustes da maquina gravados'
    Nota $arqLocal

    $atalho = Join-Path ([Environment]::GetFolderPath('Desktop')) 'ELEVEN AUDIO.lnk'
    try {
        $sh = New-Object -ComObject WScript.Shell
        $lnk = $sh.CreateShortcut($atalho)
        # O ABRIR.bat mora na pasta DESTE script, nao em $PastaInstalacao (que e a
        # pasta de trabalho, onde entra a base). Apontar para $PastaInstalacao criava
        # um atalho para arquivo inexistente: o usuario clicava e nada acontecia.
        $lnk.TargetPath = Join-Path $PSScriptRoot 'ABRIR.bat'
        $lnk.WorkingDirectory = $PSScriptRoot
        $lnk.Description = 'Estudio de voz local'
        $lnk.Save()
        Ok 'atalho criado na Area de Trabalho'
    } catch {
        Falta 'nao consegui criar o atalho automaticamente'
        Nota "crie um atalho a mao para: $(Join-Path $PSScriptRoot 'ABRIR.bat')"
    }

    return $true
}

# ---------------------------------------------------------------- principal

Write-Host ''
Write-Host '   ELEVEN AUDIO  -  estudio de voz local' -ForegroundColor Cyan
Write-Host '   clonagem, geracao, transcricao e dublagem rodando na sua maquina' -ForegroundColor DarkGray

try {
    $pronto = Passo1_Conferir

    if ($SoVerificar) {
        Titulo 'SO CONFERIR'
        if ($pronto) { Ok 'esta maquina tem tudo para rodar' }
        else { Falta "falta: $($script:Falhas -join ', ')" }
        exit 0
    }

    if (-not (Passo2_InstalarFaltando)) { exit 1 }
    if (-not (Passo3_BaixarBase))       { exit 1 }
    if (-not (Passo4_Ambientes))        { exit 1 }
    if (-not (Passo5_Atalhos))          { exit 1 }

    Titulo 'PRONTO'
    Write-Host ''
    Write-Host '   Abra pelo atalho na Area de Trabalho, ou por:' -ForegroundColor White
    Write-Host "   $(Join-Path $PSScriptRoot 'ABRIR.bat')" -ForegroundColor Gray
    Write-Host ''
    Write-Host '   Na primeira vez que gerar audio, ele baixa o motor do HuggingFace.' -ForegroundColor Gray
    Write-Host '   O download retoma de onde parou. Nao precisa de conta.' -ForegroundColor Gray
    Write-Host ''
}
catch {
    Titulo 'DEU ERRO'
    Mal $_.Exception.Message
    Write-Host ''
    Nota 'nada foi perdido. Rode o INSTALAR de novo: ele reaproveita o que ja baixou.'
    Write-Host ''
    exit 1
}
