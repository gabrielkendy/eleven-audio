@echo off
title ELEVEN AUDIO - conferir a maquina
cd /d "%~dp0"
echo.
echo   Vou apenas OLHAR o que esta maquina tem. Nada sera instalado.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1" -SoVerificar
echo.
pause
