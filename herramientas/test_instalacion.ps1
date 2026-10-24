# Pruebas sin descargas, instalacion ni cambios en programas del equipo.
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'instalar_dependencias.ps1')
$temporalPrueba = Join-Path ([IO.Path]::GetTempPath()) ('chatbot-instalacion-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temporalPrueba | Out-Null
$script:comprobaciones = 0
function Comprobar($condicion, [string]$mensaje) {
    if (-not $condicion) { throw $mensaje }
    $script:comprobaciones++
}
function DebeFallar([scriptblock]$accion) {
    $fallo = $false
    try { & $accion } catch { $fallo = $true }
    Comprobar $fallo 'Se esperaba rechazar esta operacion.'
}

# Sustituciones locales: jamas se ejecuta un instalador de verdad en estas pruebas.
$script:descargas = 0
$script:errorDescarga = $false
function Invoke-WebRequest {
    param($Uri, $OutFile, [switch]$UseBasicParsing, $TimeoutSec)
    $script:descargas++
    [IO.File]::WriteAllText($OutFile, 'contenido de prueba')
    if ($script:errorDescarga) { throw 'Conexion interrumpida' }
}
$script:firma = 'Valid'
$script:editor = 'CN=Python Software Foundation'
function Get-AuthenticodeSignature {
    param($LiteralPath)
    return [pscustomobject]@{ Status = $script:firma; SignerCertificate = [pscustomobject]@{ Subject = $script:editor } }
}
$script:salidaInstalador = 0
$script:inicios = 0
function Start-Process {
    param($FilePath, $ArgumentList, $WindowStyle, [switch]$Wait, [switch]$PassThru)
    Comprobar ($WindowStyle -eq 'Hidden' -and $Wait -and $PassThru) 'Se debe esperar la instalacion sin abrir ventanas.'
    $script:inicios++
    foreach ($argInstalacion in $ArgumentList) {
        if ($argInstalacion -match '^TargetDir="(.+)"$' -and $script:salidaInstalador -eq 0) {
            New-Item -ItemType Directory -Path $Matches[1] -Force | Out-Null
            [IO.File]::WriteAllText((Join-Path $Matches[1] 'python.exe'), 'archivo simulado')
        }
    }
    $script:ultimosArgumentos = $ArgumentList
    return [pscustomobject]@{ ExitCode = $script:salidaInstalador }
}
try {
    $archivo = Join-Path $temporalPrueba 'descargas\python.exe'
    DescargarOficial 'https://www.python.org/ftp/python/3.14.9/python-3.14.9-amd64.exe' $archivo
    Comprobar (Test-Path -LiteralPath $archivo) 'La descarga completa debe quedar disponible.'
    DescargarOficial 'https://www.python.org/ftp/python/3.14.9/python-3.14.9-amd64.exe' $archivo
    Comprobar ($script:descargas -eq 1) 'La descarga completa debe reutilizarse.'
    DebeFallar { DescargarOficial 'http://www.python.org/archivo.exe' (Join-Path $temporalPrueba 'inseguro.exe') }
    DebeFallar { DescargarOficial 'https://python.org.sitio-ajeno.invalid/archivo.exe' (Join-Path $temporalPrueba 'ajeno.exe') }
    $script:errorDescarga = $true
    $incompleto = Join-Path $temporalPrueba 'interrumpido.exe'
    DebeFallar { DescargarOficial 'https://ollama.com/download/OllamaSetup.exe' $incompleto }
    Comprobar (-not (Test-Path -LiteralPath $incompleto) -and -not (Test-Path -LiteralPath ($incompleto + '.parte'))) 'No se debe conservar un instalador incompleto.'
    ComprobarFirma $archivo 'Python Software Foundation'
    $script:firma = 'HashMismatch'
    DebeFallar { ComprobarFirma $archivo 'Python Software Foundation' }
    $script:firma = 'Valid'
    $script:editor = 'CN=Editor desconocido'
    DebeFallar { ComprobarFirma $archivo 'Python Software Foundation' }
    Comprobar ($script:inicios -eq 0) 'La validacion no debe ejecutar archivos.'
    EjecutarInstalador $archivo @('/quiet')
    $script:salidaInstalador = 3010
    DebeFallar { EjecutarInstalador $archivo @('/quiet') }
    $script:salidaInstalador = 1603
    DebeFallar { EjecutarInstalador $archivo @('/quiet') }
    $script:salidaInstalador = 0
    $script:errorDescarga = $false
    $script:editor = 'CN=Python Software Foundation'
    $carpetaProgramas = Join-Path $temporalPrueba "Programas de Alex's equipo"
    $carpetaDescargas = Join-Path $temporalPrueba 'cache'
    $carpetaLogs = $temporalPrueba
    $python = InstalarPythonLocal
    Comprobar ($python.Ruta -eq (Join-Path $carpetaProgramas 'python314\python.exe')) 'Python debe instalarse en una ruta privada con espacios y apostrofes.'
    Comprobar ($script:ultimosArgumentos -contains 'InstallAllUsers=0' -and $script:ultimosArgumentos -contains 'PrependPath=0') 'No debe requerir una instalacion global ni cambiar PATH.'
    # La descarga simulada de Node no tiene su hash oficial: debe rechazarse.
    DebeFallar { InstalarNodeLocal }
    Comprobar (-not (Test-Path -LiteralPath (Join-Path $carpetaProgramas 'node-v24.22.1-win-x64\node.exe'))) 'No se debe extraer un paquete sin integridad verificada.'
    function BuscarPrograma { param($nombre, $alternativas); return (Join-Path $temporalPrueba 'ollama.exe') }
    $script:editor = 'CN=Ollama Inc.'
    $script:firma = 'HashMismatch'
    $iniciosAnteriores = $script:inicios
    DebeFallar { InstalarOllamaLocal }
    Comprobar ($script:inicios -eq $iniciosAnteriores) 'Ollama no debe instalarse si su firma no es valida.'
    $script:firma = 'Valid'
    $ollamaPrueba = InstalarOllamaLocal
    Comprobar ($ollamaPrueba -eq (Join-Path $temporalPrueba 'ollama.exe')) 'Debe devolver la ruta de Ollama instalado.'
    Comprobar ($script:ultimosArgumentos -contains '/NORESTART' -and $script:ultimosArgumentos -contains '/VERYSILENT') 'La instalacion de Ollama no debe reiniciar Windows automaticamente.'
    Write-Host "$script:comprobaciones comprobaciones correctas. No se instalaron programas."
} finally {
    # El directorio se crea arriba; se valida antes de su unica limpieza recursiva.
    $resuelto = [IO.Path]::GetFullPath($temporalPrueba)
    $padre = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if ($resuelto.StartsWith($padre, [StringComparison]::OrdinalIgnoreCase) -and (Split-Path $resuelto -Leaf) -like 'chatbot-instalacion-*') {
        Remove-Item -LiteralPath $resuelto -Recurse -Force
    }
}
