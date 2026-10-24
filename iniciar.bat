@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Chatbot Cognitivo - Inicio local
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0iniciar.ps1" %*
set "resultado=%ERRORLEVEL%"
if not "%resultado%"=="0" (
    echo.
    echo El inicio no termino correctamente. Lee el mensaje anterior.
    pause
)
exit /b %resultado%
