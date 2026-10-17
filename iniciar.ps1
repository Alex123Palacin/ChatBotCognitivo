$ErrorActionPreference = 'Stop'
$raizProyecto = $PSScriptRoot
$pythonProyecto = Join-Path $raizProyecto 'backend\.venv\Scripts\python.exe'
$carpetaBackend = Join-Path $raizProyecto 'backend\principal'
$carpetaFrontend = Join-Path $raizProyecto 'frontend'
$carpetaLogs = Join-Path $raizProyecto 'logs'
$backendIniciado = $null
$inicioBackend = $null

function DetenerProcesoProyecto([int]$idProceso, [datetime]$inicioEsperado) {
    # Solo se detiene el árbol que este script acaba de iniciar.
    $procesoProyecto = Get-Process -Id $idProceso -ErrorAction SilentlyContinue
    if (-not $procesoProyecto) { return }
    if ([Math]::Abs(($procesoProyecto.StartTime.ToUniversalTime() - $inicioEsperado.ToUniversalTime()).TotalMilliseconds) -gt 2) { return }
    $hijosProyecto = Get-CimInstance Win32_Process -Filter "ParentProcessId = $idProceso" -ErrorAction SilentlyContinue
    foreach ($hijoProyecto in $hijosProyecto) { DetenerProcesoProyecto ([int]$hijoProyecto.ProcessId) ([datetime]$hijoProyecto.CreationDate) }
    Stop-Process -Id $idProceso -ErrorAction SilentlyContinue
}

if (-not (Test-Path -LiteralPath $pythonProyecto)) {
    throw 'Falta backend/.venv. Sigue la instalación del README antes de iniciar.'
}
if (-not (Test-Path -LiteralPath (Join-Path $carpetaFrontend 'node_modules'))) {
    throw 'Faltan las dependencias de React. Ejecuta npm install en frontend.'
}
foreach ($puertoProyecto in @(8000, 5173)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $puertoProyecto -ErrorAction SilentlyContinue) {
        throw "El puerto $puertoProyecto ya está ocupado. Cierra el servidor anterior y ejecuta de nuevo este script."
    }
}

try {
    Push-Location $carpetaBackend
    try {
        & $pythonProyecto manage.py migrate --noinput
        if ($LASTEXITCODE -ne 0) { throw 'No se pudieron preparar las tablas de Django.' }
    } finally { Pop-Location }
    New-Item -ItemType Directory -Path $carpetaLogs -Force | Out-Null
    $backendIniciado = Start-Process -FilePath $pythonProyecto -ArgumentList @('manage.py', 'iniciar_backend') -WorkingDirectory $carpetaBackend -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $carpetaLogs 'backend.log') -RedirectStandardError (Join-Path $carpetaLogs 'backend-error.log')
    $inicioBackend = $backendIniciado.StartTime
    $backendDisponible = $false
    for ($intentoProyecto = 0; $intentoProyecto -lt 30; $intentoProyecto++) {
        if ($backendIniciado.HasExited) { throw 'Django no pudo iniciar. Revisa logs/backend-error.log.' }
        try {
            $respuestaProyecto = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/csrf/' -TimeoutSec 1
            if ($respuestaProyecto.csrfToken) { $backendDisponible = $true; break }
        } catch { Start-Sleep -Milliseconds 300 }
    }
    if (-not $backendDisponible) { throw 'Django no respondió al iniciar. Revisa los archivos de logs/.' }
    Write-Host 'Backend y cierre semanal activos. Abre http://localhost:5173. Ctrl+C detiene el proyecto.'
    Write-Host 'Mantén Ollama abierto con deepseek-r1:8b.'
    Push-Location $carpetaFrontend
    try { & npm.cmd run dev }
    finally { Pop-Location }
} finally {
    if ($backendIniciado -and $inicioBackend) { DetenerProcesoProyecto $backendIniciado.Id $inicioBackend }
}
