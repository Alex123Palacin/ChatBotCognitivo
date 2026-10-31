# Descargas oficiales para Windows. Se ejecuta desde iniciar.ps1.
function ArquitecturaLocal {
    $arquitectura = $env:PROCESSOR_ARCHITEW6432
    if (-not $arquitectura) { $arquitectura = $env:PROCESSOR_ARCHITECTURE }
    switch ($arquitectura) {
        'AMD64' { return 'x64' }
        'ARM64' { return 'arm64' }
        default { throw 'El inicio automatico necesita Windows de 64 bits (x64 o ARM64).' }
    }
}

function DescargarOficial([string]$url, [string]$destino) {
    $uri = [Uri]$url
    if ($uri.Scheme -ne 'https' -or $uri.Host -notin @('www.python.org', 'nodejs.org', 'ollama.com')) {
        throw 'La descarga debe proceder de un proveedor oficial autorizado.'
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $destino) -Force | Out-Null
    if (Test-Path -LiteralPath $destino -PathType Leaf) { return }
    $ProgressPreference = 'SilentlyContinue'
    $temporal = $destino + '.parte'
    for ($intentoDescarga = 1; $intentoDescarga -le 3; $intentoDescarga++) {
        try {
            Write-Host "Descargando desde $($uri.Host) (intento $intentoDescarga/3). No cierres esta ventana..." -ForegroundColor Yellow
            Invoke-WebRequest -Uri $url -OutFile $temporal -UseBasicParsing -TimeoutSec 3600
            if ((Get-Item -LiteralPath $temporal).Length -eq 0) { throw 'La descarga esta vacia.' }
            Move-Item -LiteralPath $temporal -Destination $destino -Force
            return
        } catch {
            # Nunca se ejecuta ni se reutiliza una descarga incompleta.
            if (Test-Path -LiteralPath $temporal) { Remove-Item -LiteralPath $temporal -Force }
            if ($intentoDescarga -eq 3) {
                throw "No se pudo descargar desde $($uri.Host). Revisa Internet y vuelve a abrir iniciar.bat."
            }
            Write-Host 'Se interrumpio la descarga. Se intentara nuevamente...' -ForegroundColor Yellow
            Start-Sleep -Seconds 2
        }
    }
}

function PrepararModeloLocal([string]$ejecutableOllama, [string]$nombreModelo) {
    for ($intentoModelo = 1; $intentoModelo -le 3; $intentoModelo++) {
        try {
            Write-Host "Preparando $nombreModelo (intento $intentoModelo/3). La primera vez puede tardar bastante." -ForegroundColor Yellow
            # Ollama reutiliza las partes que ya termino de descargar.
            & $ejecutableOllama pull $nombreModelo
            if ($LASTEXITCODE -ne 0) { throw 'La descarga del modelo no termino.' }
            $disponibles = Invoke-RestMethod -Uri 'http://127.0.0.1:11434/api/tags' -TimeoutSec 10
            if (-not @($disponibles.models | Where-Object { $_.name -eq $nombreModelo }).Count) {
                throw 'Ollama todavia no confirma el modelo descargado.'
            }
            return
        } catch {
            if ($intentoModelo -eq 3) {
                throw "No se pudo preparar $nombreModelo. Revisa Internet y el espacio libre; vuelve a abrir iniciar.bat para reanudar."
            }
            Write-Host 'Reintentando la descarga del modelo...' -ForegroundColor Yellow
            Start-Sleep -Seconds 2
        }
    }
}

function ComprobarFirma([string]$archivo, [string]$editor) {
    $firma = Get-AuthenticodeSignature -LiteralPath $archivo
    if ($firma.Status -ne 'Valid' -or -not $firma.SignerCertificate -or $firma.SignerCertificate.Subject -notmatch $editor) {
        throw "No se pudo verificar la firma de $archivo. No se ejecutara; elimina ese instalador de la cache e intentalo nuevamente."
    }
}

function EjecutarInstalador([string]$archivo, [string[]]$argumentos) {
    $proceso = Start-Process -FilePath $archivo -ArgumentList $argumentos -WindowStyle Hidden -Wait -PassThru
    if ($proceso.ExitCode -eq 3010 -or $proceso.ExitCode -eq 1641) {
        throw 'Windows indica que debes reiniciar el equipo. Reinicia y vuelve a abrir iniciar.bat.'
    }
    if ($proceso.ExitCode -ne 0) { throw "El instalador termino con el codigo $($proceso.ExitCode). Revisa logs/." }
}

function InstalarNodeLocal {
    $arquitectura = ArquitecturaLocal
    $version = '24.22.1'
    $nombre = "node-v$version-win-$arquitectura"
    $carpeta = Join-Path $carpetaProgramas $nombre
    $ejecutable = Join-Path $carpeta 'node.exe'
    $archivo = Join-Path $carpetaDescargas "$nombre.zip"
    $huellas = @{
        x64 = 'd2046d28c2c3dcd211ac5145c0bf30e2047ef9dfb306693c8c6e2eccd8b95fa5'
        arm64 = 'a0c807319fede24c4a0d8f84564c82a619bd313b16b10c007c383c2609e99171'
    }
    if ((Test-Path -LiteralPath $ejecutable) -and (Test-Path -LiteralPath (Join-Path $carpeta 'npm.cmd'))) {
        try {
            if ((& $ejecutable --version).Trim() -eq "v$version" -and $LASTEXITCODE -eq 0) { return $ejecutable }
        } catch { }
    }
    Write-Host 'Preparando Node.js 24 LTS para este usuario...'
    DescargarOficial "https://nodejs.org/dist/v$version/$nombre.zip" $archivo
    if ((Get-FileHash -LiteralPath $archivo -Algorithm SHA256).Hash -ne $huellas[$arquitectura]) {
        Remove-Item -LiteralPath $archivo -Force
        throw 'La descarga de Node.js no coincide con su SHA256 oficial. Vuelve a iniciar para descargarla nuevamente.'
    }
    Expand-Archive -LiteralPath $archivo -DestinationPath $carpetaProgramas -Force
    if (-not (Test-Path -LiteralPath $ejecutable) -or -not (Test-Path -LiteralPath (Join-Path $carpeta 'npm.cmd'))) {
        throw 'No se pudo preparar Node.js y npm.'
    }
    return $ejecutable
}

function BuscarPythonLocal {
    $opciones = @()
    $privado = Join-Path $carpetaProgramas 'python314\python.exe'
    if (Test-Path -LiteralPath $privado) { $opciones += @{ Ruta = $privado; Args = @() } }
    foreach ($nombre in @('py.exe', 'python.exe')) {
        $ruta = BuscarPrograma $nombre
        if ($ruta -and $ruta -notlike '*\Microsoft\WindowsApps\*') {
            $argsPython = @()
            if ($nombre -eq 'py.exe') { $argsPython = @('-3') }
            $opciones += @{ Ruta = $ruta; Args = $argsPython }
        }
    }
    foreach ($version in @('314', '313', '312', '315')) {
        $ruta = Join-Path $env:LOCALAPPDATA "Programs\Python\Python$version\python.exe"
        if (Test-Path -LiteralPath $ruta) { $opciones += @{ Ruta = $ruta; Args = @() } }
    }
    # Instalaciones en otra unidad que no estan incluidas en PATH.
    foreach ($registro in @('HKCU:\Software\Python\PythonCore', 'HKLM:\Software\Python\PythonCore')) {
        foreach ($clave in @(Get-ChildItem -LiteralPath $registro -ErrorAction SilentlyContinue)) {
            $instalacion = Get-Item -LiteralPath ($clave.PSPath + '\InstallPath') -ErrorAction SilentlyContinue
            if ($instalacion) {
                $directorio = $instalacion.GetValue('')
                if ($directorio) {
                    $ruta = Join-Path $directorio 'python.exe'
                    if (Test-Path -LiteralPath $ruta) { $opciones += @{ Ruta = $ruta; Args = @() } }
                }
            }
        }
    }
    foreach ($opcion in $opciones) {
        try {
            $argsPython = $opcion.Args
            $ruta = $opcion.Ruta
            $version = (& $ruta @argsPython --version 2>$null | Out-String).Trim()
            if ($LASTEXITCODE -eq 0 -and $version -match '^Python 3\.(\d+)\.' -and [int]$Matches[1] -ge 12) {
                return $opcion
            }
        } catch { }
    }
    return $null
}

function InstalarPythonLocal {
    $arquitectura = ArquitecturaLocal
    $sufijo = 'amd64'
    if ($arquitectura -eq 'arm64') { $sufijo = 'arm64' }
    $version = '3.14.9'
    $archivo = Join-Path $carpetaDescargas "python-$version-$sufijo.exe"
    $destino = Join-Path $carpetaProgramas 'python314'
    Write-Host 'Preparando Python para este usuario...'
    DescargarOficial "https://www.python.org/ftp/python/$version/python-$version-$sufijo.exe" $archivo
    ComprobarFirma $archivo 'Python Software Foundation'
    EjecutarInstalador $archivo @('/quiet', 'InstallAllUsers=0', "TargetDir=`"$destino`"", 'Include_pip=1', 'Include_launcher=0', 'Include_test=0', 'Include_doc=0', 'Include_tcltk=0', 'AssociateFiles=0', 'Shortcuts=0', 'PrependPath=0', 'AppendPath=0', "/log `"$(Join-Path $carpetaLogs 'instalar-python.log')`"")
    $python = Join-Path $destino 'python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw 'El instalador no dejo Python en la carpeta esperada.' }
    return @{ Ruta = $python; Args = @() }
}

function InstalarOllamaLocal {
    [void](ArquitecturaLocal)
    $archivo = Join-Path $carpetaDescargas 'OllamaSetup.exe'
    Write-Host 'Preparando Ollama. La primera descarga puede ocupar varios GB...'
    DescargarOficial 'https://ollama.com/download/OllamaSetup.exe' $archivo
    ComprobarFirma $archivo 'Ollama'
    EjecutarInstalador $archivo @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', "/LOG=`"$(Join-Path $carpetaLogs 'instalar-ollama.log')`"")
    $ruta = BuscarPrograma 'ollama.exe' @((Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe'), (Join-Path $env:ProgramFiles 'Ollama\ollama.exe'))
    if (-not $ruta) { throw 'No se encontro Ollama despues de instalarlo.' }
    return $ruta
}
