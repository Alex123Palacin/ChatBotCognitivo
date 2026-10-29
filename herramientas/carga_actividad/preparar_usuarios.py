"""Prepara un mapa de identidades y una entrega independiente del paquete inicial."""
import csv
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import zipfile

RAIZ = Path(__file__).resolve().parents[2]


def preparar():
    origen = RAIZ / 'entregas_locales/actividad_20260911'
    destino = RAIZ / 'entregas_locales/cambio_usuarios_20260911'
    destino.mkdir(parents=True, exist_ok=True)
    actividad = json.loads((origen / 'actividad.json').read_text(encoding='utf-8'))
    mapa_ruta = destino / 'mapa_usuarios.json'
    if mapa_ruta.exists():
        mapa = json.loads(mapa_ruta.read_text(encoding='utf-8'))
        if [c['anterior'] for c in mapa['cuentas']] != [c['email'] for c in actividad['cuentas']]:
            raise ValueError('El mapa existente corresponde a otro paquete.')
    else:
        nuevos = set()
        cuentas = []
        for cuenta in actividad['cuentas']:
            while True:
                nuevo = secrets.choice(('estudiante', 'persona', 'colegio', 'alumno', 'aula', 'escuela')) + str(secrets.randbelow(99990) + 10)
                if nuevo not in nuevos:
                    nuevos.add(nuevo)
                    break
            cuentas.append({'anterior': cuenta['email'], 'nuevo': nuevo, 'nombre_anterior': cuenta['nombre'],
                            'fecha_alta': cuenta['fecha_alta'], 'primer_mensaje_id': cuenta['mensajes'][0]['id'],
                            'ultimo_mensaje_id': cuenta['mensajes'][-1]['id']})
        mapa = {'schema': 'chatcognitivo.usuarios.v1', 'lote': 'usuarios-20260911-v1', 'cuentas': cuentas}
        mapa_ruta.write_text(json.dumps(mapa, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        mapa_ruta.chmod(0o600)
    sha = hashlib.sha256(mapa_ruta.read_bytes()).hexdigest()
    (destino / 'mapa_usuarios.sha256').write_text(f'{sha}  mapa_usuarios.json\n', encoding='utf-8')
    shutil.copyfile(RAIZ / 'backend/principal/usuarios/cambio_usuarios.py', destino / 'cambiar_usuarios.py')
    shutil.copyfile(RAIZ / 'backend/principal/usuarios/carga_actividad.py', destino / 'motor_carga.py')
    accesos = {c['email']: c for c in json.loads((origen / 'accesos_privados.json').read_text(encoding='utf-8'))}
    with (destino / 'accesos_usuarios.csv').open('w', encoding='utf-8-sig', newline='') as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(['usuario', 'password'])
        for cuenta in mapa['cuentas']:
            escritor.writerow([cuenta['nuevo'], accesos[cuenta['anterior']]['password']])
    (destino / 'accesos_usuarios.csv').chmod(0o600)
    comando = f'python /data/cargas/cambio_usuarios/cambiar_usuarios.py /data/cargas/cambio_usuarios/mapa_usuarios.json --sha256 {sha}'
    prompt = f'''Actualiza ChatBotCognitivo para utilizar nombres de usuario y aplica el paquete adjunto `paquete_cambio_usuarios.zip`.

PRIMERO: modifica el código del proyecto y despliega backend y frontend conservando volúmenes y credenciales.
- Login de estudiantes: campo Usuario de tipo texto, sin validación de correo y con autoComplete=username. Enviar username y password. Mantener el acceso del administrador y la compatibilidad de cuentas anteriores.
- Registro: sustituir correo por username. Validar en cliente y servidor 3–40 caracteres, empezando por letra, con letras ASCII, números, punto, guion y guion bajo; normalizar a minúsculas. Rechazar duplicados sin distinguir mayúsculas, sin conceder privilegios. No solicitar ni guardar correo para cuentas nuevas.
- Conservar aceptación explícita de términos, CSRF, conservación de 30 días, contraseñas seguras y autenticación por sesión.
- Incluir username en los datos de alumnos y sesión. En la barra lateral, listado, búsqueda y detalle de administración mostrar y buscar usuario/nombre. Quitar textos, placeholders, requisitos y validaciones de Gmail/correo de los formularios y pantallas. El campo email puede permanecer internamente para compatibilidad; no eliminar columnas ni datos de otras cuentas.
- Ejecutar pruebas de registro y acceso con usuarios como estudiante49, duplicados, permisos y términos; compilar frontend y desplegar ambos servicios. Verificar que el login de tipo texto funcione ANTES de convertir las cuentas.

DESPUÉS: extrae el ZIP en una carpeta privada y copia sus archivos al contenedor backend correcto bajo `/data/cargas/cambio_usuarios/`, con acceso para el usuario de la aplicación (UID 10001). No publiques estos archivos. Ejecuta desde la consola del backend:

{comando}

Debe validar 136 cuentas sin colisiones. Si la comprobación es correcta, ejecuta:

{comando} --aplicar

El script crea un respaldo consistente y cambia únicamente username, nombre visible y correo de las cuentas identificadas por el mapa. Conserva sus IDs, contraseñas, conversaciones, fechas, análisis y permisos. No cambia administradores ni otras cuentas. Una repetición coincidente es segura.

Valida nuevamente sin --aplicar: deben quedar 0 por_cambiar y 136 ya_convertidas. Comprueba acceso por usuario, listado, conversaciones, reportes y Excel. No imprimas claves, hashes ni contenidos. No vuelvas a importar el paquete de actividad anterior después de esta conversión.

Devuelve conteos finales, resultado de las comprobaciones y ruta del respaldo. Si hay colisiones o identidades distintas, detente sin forzar el script ni borrar registros.
'''
    (destino / 'PROMPT_AGENTE.txt').write_text(prompt, encoding='utf-8')
    instrucciones = f'''# Cambio de identificadores

Usar el orden de PROMPT_AGENTE.txt: primero habilitar y desplegar acceso/registro por usuario; después ejecutar el mapa. El script por sí solo no modifica el frontend ni la API de registro.

Validación: `{comando}`

Aplicación: `{comando} --aplicar`

La ruta predeterminada del backend es /app. Con otra instalación usar --backend RUTA. Se hereda la configuración existente y se comprueban migraciones y campos. Solo se acepta la base SQLite configurada y ya existente. Se respalda en /data/cargas antes de cambiar las identidades en una transacción completa. El modo sin --aplicar no escribe.

El mapa cambia únicamente las 136 cuentas ancladas a los mensajes del paquete. Una cuenta faltante, renombrada por fuera, administrativa o con respuesta activa detiene la operación. Los usuarios nuevos pueden ser estudiante, persona, colegio, alumno, aula o escuela seguidos de números. No se alteran textos antiguos: los saludos ya guardados se conservan literalmente.

accesos_usuarios.csv queda fuera del ZIP. Contiene los nuevos usuarios y las contraseñas originales. Si una contraseña se cambió posteriormente en el servidor, se conserva esa contraseña actual y se debe seguir utilizando; el script no la restablece. Mantener el CSV privado y fuera de Git.

No utilizar de nuevo el cargador del paquete de actividad original: conserva las identidades anteriores y rechazará esta conversión. No desactivar sus comprobaciones para forzarlo. Los IDs y enlaces de reportes permanecen iguales. La procedencia y el consentimiento de los perfiles no se modifican.
'''
    (destino / 'INSTRUCCIONES.md').write_text(instrucciones, encoding='utf-8')
    archivos = ['mapa_usuarios.json', 'mapa_usuarios.sha256', 'cambiar_usuarios.py', 'motor_carga.py', 'PROMPT_AGENTE.txt', 'INSTRUCCIONES.md']
    (destino / 'archivos.sha256').write_text(''.join(f'{hashlib.sha256((destino / n).read_bytes()).hexdigest()}  {n}\n' for n in archivos), encoding='utf-8')
    with zipfile.ZipFile(destino / 'paquete_cambio_usuarios.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archivo:
        for nombre in archivos + ['archivos.sha256']:
            archivo.write(destino / nombre, arcname=nombre)
    print(json.dumps({'carpeta': str(destino), 'cuentas': len(mapa['cuentas']), 'sha256': sha}))


if __name__ == '__main__':
    preparar()
