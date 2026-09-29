@echo off
title ELEVEN AUDIO
cd /d "%~dp0"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0ABRIR.ps1"
if errorlevel 1 pause
