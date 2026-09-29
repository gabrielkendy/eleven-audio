# Encerra a base e o estudio. Nao apaga nada: so derruba os dois processos.

$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

$Raiz = $PSScriptRoot
if (-not $Raiz) { $Raiz = Split-Path -Parent $MyInvocation.MyCommand.Path }

$Ajustes = Join-Path $Raiz 'local.ps1'
if (Test-Path -LiteralPath $Ajustes) { . $Ajustes }

$PortaBase = if ($PortaBase) { $PortaBase } else { 3900 }
$PortaApp = if ($PortaApp) { $PortaApp } else { 7800 }

function Encerrar([int]$p, [string]$nome) {
    $achou = $false
    try {
        $linhas = netstat -ano | Select-String ":$p\s" | Select-String 'LISTENING'
        foreach ($l in $linhas) {
            # $pid e reservado no PowerShell; usar outro nome
            $idProc = ($l -split '\s+')[-1]
            if ($idProc -match '^\d+$' -and $idProc -ne '0') {
                Stop-Process -Id ([int]$idProc) -Force -ErrorAction SilentlyContinue
                $achou = $true
            }
        }
    } catch { }
    if ($achou) {
        Write-Host "   [ok]   $nome encerrado" -ForegroundColor Green
    } else {
        Write-Host "   [--]   $nome nao estava no ar" -ForegroundColor Yellow
    }
}

Write-Host ''
Write-Host '   ELEVEN AUDIO  -  encerrando' -ForegroundColor Cyan
Write-Host ''

Encerrar $PortaApp 'estudio'
Encerrar $PortaBase 'base'

Write-Host ''
Write-Host '   tudo encerrado. seus audios continuam salvos.' -ForegroundColor Gray
Write-Host ''
Start-Sleep -Seconds 2
