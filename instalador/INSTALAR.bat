@echo off
title ELEVEN AUDIO - instalacao
cd /d "%~dp0"
echo.
echo   ELEVEN AUDIO - estudio de voz local
echo   Esta janela vai instalar tudo o que falta.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1"
echo.
if errorlevel 1 (
  echo   A instalacao parou. Leia a mensagem acima.
) else (
  echo   Tudo pronto.
)
echo.
pause
