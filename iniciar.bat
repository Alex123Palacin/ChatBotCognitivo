@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Chatbot Cognitivo - Inicio local
set "CHATBOT_INICIO_RAIZ=%~dp0"
rem Evita heredar modulos incompatibles si se abre desde PowerShell 7 o un IDE.
set "PSModulePath=%SystemRoot%\System32\WindowsPowerShell\v1.0\Modules;%ProgramFiles%\WindowsPowerShell\Modules"
echo La primera vez se descargaran las herramientas y los modelos que falten.
echo No necesitas instalar Python, Node.js, Ollama ni Docker manualmente.
echo Extrae primero el ZIP completo. Necesitas Internet en la primera preparacion.
echo Si Windows pide permisos o reiniciar, sigue su aviso y vuelve a abrir este archivo.
echo Espera a que aparezca LISTO y deja esta ventana abierta.
rem Desbloquea solo los dos scripts de este proyecto, sin cambiar la politica global.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -ExecutionPolicy RemoteSigned -Command "$inicio = Join-Path $env:CHATBOT_INICIO_RAIZ 'iniciar.ps1'; $ayudante = Join-Path $env:CHATBOT_INICIO_RAIZ 'herramientas\instalar_dependencias.ps1'; foreach ($script in @($inicio, $ayudante)) { if (-not (Test-Path -LiteralPath $script -PathType Leaf)) { Write-Host 'Faltan archivos del proyecto. Extrae el ZIP completo antes de iniciar.' -ForegroundColor Red; exit 1 }; Unblock-File -LiteralPath $script -ErrorAction Stop }; & $inicio" %*
set "resultado=%ERRORLEVEL%"
if not "%resultado%"=="0" (
    echo.
    echo El inicio no termino correctamente. Lee el mensaje anterior.
    pause
)
exit /b %resultado%
