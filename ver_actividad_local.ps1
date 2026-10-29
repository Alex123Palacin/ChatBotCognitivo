param([switch]$Verificar, [switch]$SinAbrir)
$ErrorActionPreference = 'Stop'
$raizActividad = $PSScriptRoot
$entregaActividad = Join-Path $raizActividad 'entregas_locales\actividad_20260911'
$pythonActividad = Join-Path $raizActividad 'backend\.venv\Scripts\python.exe'
$frontendActividad = Join-Path $raizActividad 'frontend'
$variablesPreviasActividad = @{}
$procesosActividad = New-Object System.Collections.ArrayList

function DetenerActividadPropia([int]$idActividad, [datetime]$inicioActividad) {
    $procesoActividad = Get-Process -Id $idActividad -ErrorAction SilentlyContinue
    if (-not $procesoActividad) { return }
    if ([Math]::Abs(($procesoActividad.StartTime.ToUniversalTime() - $inicioActividad.ToUniversalTime()).TotalMilliseconds) -gt 2) { return }
    $hijosActividad = Get-CimInstance Win32_Process -Filter "ParentProcessId = $idActividad" -ErrorAction SilentlyContinue
    foreach ($hijoActividad in $hijosActividad) {
        DetenerActividadPropia ([int]$hijoActividad.ProcessId) ([datetime]$hijoActividad.CreationDate)
    }
    Stop-Process -Id $idActividad -ErrorAction SilentlyContinue
}

function EsperarActividad([string]$urlActividad, $procesoActividad) {
    $limiteActividad = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $limiteActividad) {
        $procesoActividad.Refresh()
        if ($procesoActividad.HasExited) { throw 'Un servicio se cerro. Revisa los logs de la entrega.' }
        try {
            $respuestaActividad = Invoke-WebRequest -Uri $urlActividad -UseBasicParsing -TimeoutSec 2
            if ($respuestaActividad.StatusCode -eq 200) { return }
        } catch { }
        Start-Sleep -Milliseconds 300
    }
    throw "No respondio $urlActividad. Revisa los logs de la entrega."
}

try {
    if (-not (Test-Path -LiteralPath (Join-Path $entregaActividad 'actividad_local.sqlite3'))) {
        throw 'Primero prepara y verifica la entrega con herramientas/carga_actividad/verificar_local.py.'
    }
    if (-not (Test-Path -LiteralPath $pythonActividad)) { throw 'Falta Python del proyecto.' }
    $nodeActividad = Get-Command node.exe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source
    if (-not $nodeActividad) {
        $runtimesActividad = Join-Path $env:LOCALAPPDATA 'ChatbotCognitivo\runtimes'
        if (Test-Path -LiteralPath $runtimesActividad) {
            $nodeActividad = Get-ChildItem -LiteralPath $runtimesActividad -Filter node.exe -Recurse -File | Select-Object -First 1 -ExpandProperty FullName
        }
    }
    if (-not $nodeActividad) { throw 'Falta Node.js. Usa el runtime instalado para el proyecto.' }
    $viteActividad = Join-Path $frontendActividad 'node_modules\vite\bin\vite.js'
    if (-not (Test-Path -LiteralPath $viteActividad)) { throw 'Faltan las dependencias del frontend.' }
    foreach ($puertoActividad in @(8021, 5192)) {
        if (Get-NetTCPConnection -State Listen -LocalPort $puertoActividad -ErrorAction SilentlyContinue) {
            throw "El puerto $puertoActividad esta ocupado. No se detuvo ningun servicio existente."
        }
    }
    $variablesActividad = @{
        DJANGO_DB_PATH = (Join-Path $entregaActividad 'actividad_local.sqlite3')
        DJANGO_DEBUG = 'true'
        DJANGO_ALLOWED_HOSTS = 'localhost,127.0.0.1,[::1]'
        DJANGO_CSRF_TRUSTED_ORIGINS = 'http://localhost:5192,http://127.0.0.1:5192'
        DJANGO_SECURE_SSL_REDIRECT = 'false'
        DJANGO_COOKIE_SECURE = 'false'
        DJANGO_TRUST_PROXY_HEADERS = 'false'
        PYTHONIOENCODING = 'utf-8'
    }
    foreach ($claveActividad in $variablesActividad.Keys) {
        $variablesPreviasActividad[$claveActividad] = [Environment]::GetEnvironmentVariable($claveActividad, 'Process')
        [Environment]::SetEnvironmentVariable($claveActividad, $variablesActividad[$claveActividad], 'Process')
    }
    $configActividad = Join-Path $entregaActividad 'vite.actividad.config.mts'
    $rutaFrontendJsonActividad = ConvertTo-Json ($frontendActividad.Replace('\','/')) -Compress
    $configTextoActividad = @"
import base from '../../frontend/vite.config.ts';
export default { ...base, root: $rutaFrontendJsonActividad, server: { ...base.server, host: '127.0.0.1', port: 5192, strictPort: true, proxy: { '/api': { target: 'http://127.0.0.1:8021', changeOrigin: true, timeout: 200000, proxyTimeout: 200000 } } } };
"@
    Set-Content -LiteralPath $configActividad -Value $configTextoActividad -Encoding utf8
    $servidorActividad = Join-Path $raizActividad 'herramientas\carga_actividad\servir_local.py'
    $backendActividad = Start-Process -FilePath $pythonActividad -ArgumentList @('"' + $servidorActividad + '"') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $entregaActividad 'backend.log') -RedirectStandardError (Join-Path $entregaActividad 'backend-error.log')
    [void]$procesosActividad.Add(@{Id=$backendActividad.Id; Inicio=$backendActividad.StartTime})
    EsperarActividad 'http://127.0.0.1:8021/api/salud/' $backendActividad
    $interfazActividad = Start-Process -FilePath $nodeActividad -ArgumentList @(('"' + $viteActividad + '"'), '--config', ('"' + $configActividad + '"')) -WorkingDirectory $frontendActividad -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $entregaActividad 'frontend.log') -RedirectStandardError (Join-Path $entregaActividad 'frontend-error.log')
    [void]$procesosActividad.Add(@{Id=$interfazActividad.Id; Inicio=$interfazActividad.StartTime})
    EsperarActividad 'http://127.0.0.1:5192' $interfazActividad
    Write-Host 'Actividad local disponible en http://127.0.0.1:5192' -ForegroundColor Green
    Write-Host 'Los accesos estan en acceso_admin_local.json y accesos.csv, dentro de la entrega privada.'
    if (-not $Verificar) {
        if (-not $SinAbrir) { Start-Process 'http://127.0.0.1:5192' }
        [void](Read-Host 'Presiona ENTER para cerrar esta revision local')
    }
} finally {
    for ($indiceActividad = $procesosActividad.Count - 1; $indiceActividad -ge 0; $indiceActividad--) {
        $registroActividad = $procesosActividad[$indiceActividad]
        DetenerActividadPropia $registroActividad.Id $registroActividad.Inicio
    }
    foreach ($claveActividad in $variablesPreviasActividad.Keys) {
        [Environment]::SetEnvironmentVariable($claveActividad, $variablesPreviasActividad[$claveActividad], 'Process')
    }
}
