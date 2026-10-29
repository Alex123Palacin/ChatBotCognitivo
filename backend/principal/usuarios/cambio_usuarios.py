"""Conversión acotada de identificadores; no modifica mensajes ni contraseñas."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import uuid


def leer_mapa(ruta, sha256):
    if not re.fullmatch(r'[a-fA-F0-9]{64}', sha256 or ''):
        raise ValueError('Se necesita la huella SHA256 completa del mapa.')
    with Path(ruta).open('rb') as archivo:
        contenido = archivo.read(1024 * 1024 + 1)
    if len(contenido) > 1024 * 1024 or hashlib.sha256(contenido).hexdigest() != sha256.lower():
        raise ValueError('La huella del mapa no coincide o supera el tamaño permitido.')
    def objeto(pares):
        resultado = {}
        for clave, valor in pares:
            if clave in resultado:
                raise ValueError('Campos repetidos en el mapa.')
            resultado[clave] = valor
        return resultado
    datos = json.loads(contenido, object_pairs_hook=objeto)
    if not isinstance(datos, dict) or set(datos) != {'schema', 'lote', 'cuentas'} or datos['schema'] != 'chatcognitivo.usuarios.v1':
        raise ValueError('Formato de mapa no compatible.')
    if not isinstance(datos['lote'], str) or not re.fullmatch(r'[a-z0-9-]{3,80}', datos['lote']):
        raise ValueError('Identificador de lote no válido.')
    if not isinstance(datos['cuentas'], list) or not 1 <= len(datos['cuentas']) <= 500:
        raise ValueError('Cantidad de cuentas no válida.')
    anteriores, nuevos, mensajes = set(), set(), set()
    for cuenta in datos['cuentas']:
        if not isinstance(cuenta, dict) or set(cuenta) != {'anterior', 'nuevo', 'nombre_anterior', 'fecha_alta', 'primer_mensaje_id', 'ultimo_mensaje_id'}:
            raise ValueError('Campos de cuenta no válidos.')
        anterior, nuevo = cuenta['anterior'], cuenta['nuevo']
        if not isinstance(anterior, str) or len(anterior) > 150 or not anterior.endswith('@example.com') or anterior != anterior.lower():
            raise ValueError('Identificador de origen no válido.')
        if not isinstance(nuevo, str) or not re.fullmatch(r'[a-z][a-z0-9._-]{2,39}', nuevo):
            raise ValueError('Nombre de usuario nuevo no válido.')
        if anterior in anteriores or nuevo in nuevos:
            raise ValueError('Hay identificadores repetidos en el mapa.')
        anteriores.add(anterior); nuevos.add(nuevo)
        if not isinstance(cuenta['nombre_anterior'], str) or not 1 <= len(cuenta['nombre_anterior']) <= 150:
            raise ValueError('Nombre de origen no válido.')
        fecha = datetime.fromisoformat(cuenta['fecha_alta'])
        if fecha.tzinfo is None:
            raise ValueError('Fecha de alta sin zona horaria.')
        for campo in ('primer_mensaje_id', 'ultimo_mensaje_id'):
            mid = uuid.UUID(cuenta[campo])
            if str(mid) != cuenta[campo] or mid in mensajes:
                raise ValueError('Ancla de conversación no válida o repetida.')
            mensajes.add(mid)
    return datos


def planificar(datos):
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    from django.db.models.functions import Lower
    from django.utils import timezone
    from chat.models import Mensaje
    cambios, existentes = [], 0
    for cuenta in datos['cuentas']:
        candidatos = list(get_user_model().objects.annotate(login_minus=Lower('username')).filter(
            Q(login_minus=cuenta['anterior']) | Q(login_minus=cuenta['nuevo'])
        ).select_related('perfil'))
        if len(candidatos) != 1:
            raise ValueError('Cuenta ausente o colisión de identificadores. Se canceló el lote completo.')
        usuario = candidatos[0]
        perfil = getattr(usuario, 'perfil', None)
        if usuario.is_staff or usuario.is_superuser or not usuario.is_active or usuario.groups.exists() or usuario.user_permissions.exists():
            raise ValueError('El mapa incluye una cuenta con permisos o estado incompatibles.')
        if perfil is None or perfil.origen_datos != 'demostracion' or usuario.date_joined != datetime.fromisoformat(cuenta['fecha_alta']):
            raise ValueError('La cuenta no pertenece al lote previsto.')
        if perfil.respuesta_hasta and perfil.respuesta_hasta > timezone.now():
            raise ValueError('Hay una respuesta en curso. Reintenta cuando finalice.')
        anclas = list(Mensaje.objects.filter(pk__in=[cuenta['primer_mensaje_id'], cuenta['ultimo_mensaje_id']]).select_related('sesion'))
        if len(anclas) != 2 or any(m.usuario_id != usuario.pk or m.sesion.usuario_id != usuario.pk for m in anclas):
            raise ValueError('No coinciden las conversaciones de la cuenta. No se modificó el lote.')
        if usuario.username == cuenta['nuevo'] and usuario.first_name == cuenta['nuevo'] and not usuario.email and not usuario.last_name:
            existentes += 1
        elif usuario.username == cuenta['anterior'] and usuario.email == cuenta['anterior'] and usuario.first_name == cuenta['nombre_anterior'] and not usuario.last_name:
            cambios.append((usuario, cuenta['nuevo']))
        else:
            raise ValueError('Una identidad cambió desde la preparación del mapa. Revisa esa cuenta antes de continuar.')
    return cambios, existentes


def ejecutar(datos, aplicar=False, respaldo=None, validar_entorno=True):
    from django.contrib.auth import get_user_model
    from django.db import connection, transaction
    try:
        from motor_carga import comprobar_entorno, _crear_respaldo
    except ModuleNotFoundError:
        from usuarios.carga_actividad import comprobar_entorno, _crear_respaldo
    if validar_entorno:
        comprobar_entorno()
    cambios, existentes = planificar(datos)
    resultado = {'lote': datos['lote'], 'modo': 'aplicar' if aplicar else 'validar', 'cuentas': len(datos['cuentas']),
                 'por_cambiar': len(cambios), 'ya_convertidas': existentes, 'convertidas': 0}
    if not aplicar or not cambios:
        return resultado
    resultado['respaldo'] = _crear_respaldo(respaldo)
    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute('UPDATE usuarios_perfil SET conectado = conectado WHERE 1 = 0')
        cambios, existentes = planificar(datos)
        for usuario, nuevo in cambios:
            # Solo identidad: PK, password, sesiones, fechas y contenido se conservan.
            get_user_model().objects.filter(pk=usuario.pk).update(username=nuevo, first_name=nuevo, last_name='', email='')
        resultado.update(convertidas=len(cambios), ya_convertidas=existentes)
    return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archivo', type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--backend', type=Path, default=Path('/app'))
    parser.add_argument('--aplicar', action='store_true')
    parser.add_argument('--respaldo', type=Path)
    args = parser.parse_args()
    if not (args.backend / 'manage.py').is_file():
        parser.error('La ruta --backend debe contener manage.py.')
    sys.path.insert(0, str(args.backend.resolve()))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'principal.settings')
    import django
    django.setup()
    from django.db import DatabaseError
    try:
        resultado = ejecutar(leer_mapa(args.archivo, args.sha256), args.aplicar, args.respaldo)
    except (ValueError, OSError, DatabaseError, RecursionError, TypeError) as exc:
        mensaje = str(exc) if isinstance(exc, ValueError) else 'La operación no se completó; revisa compatibilidad, rutas y permisos.'
        parser.exit(1, f'Error: {mensaje}\n')
    print(json.dumps(resultado, ensure_ascii=False))


if __name__ == '__main__':
    main()
