"""Construye la entrega portable; las claves legibles permanecen fuera del ZIP."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

RAIZ = Path(__file__).resolve().parents[2]
FUENTES = Path(__file__).resolve().parent


def empaquetar(salida):
    salida = Path(salida).resolve()
    huella = (salida / 'actividad.sha256').read_text(encoding='utf-8').split()[0]
    assert hashlib.sha256((salida / 'actividad.json').read_bytes()).hexdigest() == huella
    shutil.copyfile(FUENTES / 'cargar_paquete.py', salida / 'cargar_paquete.py')
    shutil.copyfile(RAIZ / 'backend/principal/usuarios/carga_actividad.py', salida / 'motor_carga.py')
    contenido = f'''# Operación de carga

1. Localiza el servicio **backend** de esta aplicación en Dokploy. Conserva la base, los volúmenes, las variables de entorno y las credenciales actuales.
2. Extrae este paquete en una carpeta privada del servidor. No publiques los archivos en el frontend, una URL ni el repositorio. No uses `loaddata` ni restaures una base SQLite encima de la activa.
3. Copia la carpeta al servicio backend bajo `/data/cargas/actividad_20260911/`, con lectura para el usuario del servicio (UID 10001). El archivo JSON contiene hashes de acceso y debe tratarse como privado. No cambies permisos del volumen completo.
4. Dentro del **backend**, ejecuta primero la validación:

```sh
python /data/cargas/actividad_20260911/cargar_paquete.py /data/cargas/actividad_20260911/actividad.json --sha256 {huella}
```

5. Si termina con código 0, muestra `cuentas: 136` y no informa colisiones ni migraciones pendientes, ejecuta:

```sh
python /data/cargas/actividad_20260911/cargar_paquete.py /data/cargas/actividad_20260911/actividad.json --sha256 {huella} --aplicar
```

6. La operación crea un respaldo nuevo bajo `/data/cargas/` antes de insertar. Conserva la ruta que devuelve. Ejecuta el mismo comando de validación al terminar: debe indicar `cuentas_nuevas: 0` y `cuentas_existentes: 136`.
7. Comprueba `/api/salud/`, el listado administrativo y un historial. No abras sesiones de estudiantes ni exportes contraseñas al registro de consola. El administrador conserva su acceso actual. La exportación web admite grupos de hasta 100 cuentas por solicitud.
8. Entrega el código de salida, los conteos finales y la ruta del respaldo. No muestres variables de entorno, hashes, claves, mensajes ni el contenido del archivo.

## Si usas SSH en el host

Obtén primero el ID del contenedor correcto por las etiquetas de Compose y el proyecto de Dokploy. No elijas automáticamente el primer contenedor de la máquina:

```sh
docker ps --filter label=com.docker.compose.service=backend --format '{{{{.ID}}}}  {{{{.Names}}}}'
```

Usa el ID confirmado para preparar la carpeta con el usuario de la aplicación:

```sh
docker exec --user 10001:10001 CONTENEDOR_BACKEND mkdir -p /data/cargas/actividad_20260911
docker cp CARPETA_EXTRAIDA/. CONTENEDOR_BACKEND:/data/cargas/actividad_20260911/
docker exec --user 0 CONTENEDOR_BACKEND chown -R 10001:10001 /data/cargas/actividad_20260911
docker exec --user 10001:10001 CONTENEDOR_BACKEND chmod -R go-rwx /data/cargas/actividad_20260911
```

Luego ejecuta los comandos Python de arriba con `docker exec --user 10001:10001 CONTENEDOR_BACKEND` delante. `CONTENEDOR_BACKEND` y `CARPETA_EXTRAIDA` deben sustituirse por valores verificados.

## Compatibilidad

El servicio debe contener el código actual y las migraciones `usuarios.0003_aceptacion_terminos`, `chat.0002_retencion_mensajes` y `sesiones.0002_conversacion_abierta`, aplicadas a su base configurada. Si la validación las rechaza, actualiza el despliegue y aplica las migraciones del repositorio sin eliminar volúmenes. No alteres las comprobaciones del cargador para forzar la importación.

El cargador portable se ejecuta con la configuración del backend y no necesita un proceso adicional permanente. No instala paquetes, no descarga modelos, no cambia `.env`, no asigna permisos administrativos ni reemplaza cuentas. El comando es idempotente: una repetición completa y coincidente no duplica registros; una discrepancia detiene toda la carga.
'''
    (salida / 'INSTRUCCIONES_VPS.md').write_text(contenido, encoding='utf-8')
    prompt = f'''Realiza una carga administrativa en el backend de ChatBotCognitivo desplegado en Dokploy utilizando el paquete adjunto `paquete_actividad_20260911.zip`.

Extrae el paquete en una ubicación privada y sigue `INSTRUCCIONES_VPS.md`. Identifica el contenedor backend correcto de esta aplicación y usa su configuración y su base actuales. La huella SHA256 esperada de `actividad.json` es `{huella}`.

Ejecuta primero el cargador sin `--aplicar`. Si valida correctamente, ejecútalo con `--aplicar`; después vuelve a validar y comprueba que informe 0 cuentas nuevas y 136 existentes. Conserva la ruta del respaldo generado y verifica salud, listado e historial administrativo. Respeta los límites de exportación existentes.

Conserva los volúmenes, las credenciales, las variables de entorno y los registros existentes. No uses `loaddata`, no reemplaces bases ni fuerces comprobaciones que fallen. No publiques el paquete ni imprimas su contenido o datos de acceso. Si hay incompatibilidad de código o migraciones, resuélvela con la versión del repositorio y sus migraciones antes de importar. Devuélveme únicamente el resultado operativo, los conteos, la ruta del respaldo y cualquier incidencia.
'''
    (salida / 'PROMPT_AGENTE.txt').write_text(prompt, encoding='utf-8')
    ficheros = ['actividad.json', 'actividad.sha256', 'cargar_paquete.py', 'motor_carga.py', 'INSTRUCCIONES_VPS.md', 'PROMPT_AGENTE.txt']
    manifiesto = {nombre: hashlib.sha256((salida / nombre).read_bytes()).hexdigest() for nombre in ficheros}
    (salida / 'archivos.sha256').write_text(''.join(f'{huella_archivo}  {nombre}\n' for nombre, huella_archivo in manifiesto.items()), encoding='utf-8')
    ruta_zip = salida / 'paquete_actividad_20260911.zip'
    with zipfile.ZipFile(ruta_zip, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archivo:
        for nombre in ficheros + ['archivos.sha256']:
            archivo.write(salida / nombre, arcname=nombre)
    ruta_zip.chmod(0o600)
    (salida / 'paquete.sha256').write_text(f'{hashlib.sha256(ruta_zip.read_bytes()).hexdigest()}  {ruta_zip.name}\n', encoding='utf-8')
    return {'archivo': str(ruta_zip), 'bytes': ruta_zip.stat().st_size, 'json_sha256': huella}


if __name__ == '__main__':
    print(json.dumps(empaquetar(sys.argv[1] if len(sys.argv) > 1 else RAIZ / 'entregas_locales/actividad_20260911'), indent=2))
