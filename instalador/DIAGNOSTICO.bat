@echo off
title ELEVEN AUDIO - diagnostico
cd /d "%~dp0"
echo.
echo   ELEVEN AUDIO - diagnostico
echo.
echo   Vou olhar a maquina e gravar um relatorio na sua Area de Trabalho.
echo   Nada sera instalado, alterado ou apagado.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0DIAGNOSTICO.ps1"
echo.
if errorlevel 1 (
  echo   Terminou com erro. Rode de novo e anote o que aparecer.
)
pause
