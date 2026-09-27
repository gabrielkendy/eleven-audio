param(
    [string]$Start = "00:00:30",
    [int]$Seconds = 13
)

$ErrorActionPreference = "Stop"
$ffmpeg = "C:\Users\<usuario>\.venvs\comfy-agent\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
$source = "C:\Users\<usuario>\Downloads\PASTA-DE-CONTEUDO\09-CORTES\PARES-CANAL\2026-09-20_nemotron-ultra-3\2-CAMERA.mov"
$destination = Join-Path $PSScriptRoot "reference-gabriel-original-13s.wav"

if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
    throw "Fonte original nao encontrada: $source"
}

& $ffmpeg -hide_banner -loglevel error -ss $Start -i $source -t $Seconds -vn -ac 1 -ar 24000 -c:a pcm_s16le -y $destination
if ($LASTEXITCODE -ne 0) { throw "ffmpeg falhou com exit code $LASTEXITCODE" }
Get-Item -LiteralPath $destination | Select-Object FullName, Length, LastWriteTime
