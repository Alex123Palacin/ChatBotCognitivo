"""Importación acotada de actividad: valida, respalda e inserta sin reemplazos.

El paquete declara su procedencia y su método de anotación. Nunca se atribuye
aceptación de términos a cuentas creadas por una carga administrativa.
"""
import base64
from contextlib import closing
from copy import deepcopy
from datetime import date, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import uuid
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.validators import validate_email
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

from chat.models import Mensaje
from ml.analisis import SENALES_INDICADOR
from reportes.models import Evidencia
from reportes.services import actualizar_reporte
from sesiones.models import SesionSemanal
from usuarios.models import Perfil


MAX_BYTES = 64 * 1024 * 1024
SCHEMA = 'chatcognitivo.actividad.v1'
LIMA = ZoneInfo('America/Lima')
NOTA_CARGA = ' Procedencia: demostración. Evidencias de anotación estructurada verificadas contra los mensajes; esta carga no ejecutó inferencia del modelo.'
MIGRACIONES_REQUERIDAS = {
    ('usuarios', '0003_aceptacion_terminos'),
    ('chat', '0002_retencion_mensajes'),
    ('sesiones', '0002_conversacion_abierta'),
}
ERROR_VERSION = 'El código o la base del servicio no tienen la versión requerida. Actualiza el backend y aplica sus migraciones antes de cargar el archivo.'


class ErrorCarga(ValueError):
    pass


def _campos(item, campos, tipo):
    if not isinstance(item, dict) or set(item) != set(campos.split()):
        raise ErrorCarga(f'Campos no válidos en {tipo}.')


def _texto(valor, minimo, maximo, tipo):
    if not isinstance(valor, str) or not minimo <= len(valor) <= maximo or not valor.strip() or '\x00' in valor:
        raise ErrorCarga(f'Texto no válido en {tipo}.')
    return valor


def _fecha(valor):
    if not isinstance(valor, str) or len(valor) > 40:
        raise ErrorCarga('Fecha no válida.')
    try:
        resultado = datetime.fromisoformat(valor)
    except ValueError as exc:
        raise ErrorCarga('Fecha no válida.') from exc
    if resultado.tzinfo is None or resultado.utcoffset() != timedelta(hours=-5):
        raise ErrorCarga('Las fechas necesitan el desplazamiento horario de Lima (-05:00).')
    return resultado


def _uuid(valor):
    try:
        resultado = uuid.UUID(valor) if isinstance(valor, str) else None
    except ValueError as exc:
        raise ErrorCarga('Identificador de mensaje no válido.') from exc
    if resultado is None or str(resultado) != valor or resultado.int == 0:
        raise ErrorCarga('Identificador de mensaje no válido.')
    return resultado


def _hash_password(valor):
    if not isinstance(valor, str) or len(valor) > 256:
        raise ErrorCarga('Hash de contraseña no válido.')
    partes = valor.split('$')
    if len(partes) != 4 or partes[0] != 'pbkdf2_sha256' or not partes[1].isascii() or not partes[1].isdecimal():
        raise ErrorCarga('Se necesita un hash PBKDF2 SHA256 compatible con Django.')
    if not 100000 <= int(partes[1]) <= 5000000 or not re.fullmatch(r'[A-Za-z0-9]{12,128}', partes[2]):
        raise ErrorCarga('Parámetros PBKDF2 fuera de los límites admitidos.')
    try:
        longitud = len(base64.b64decode(partes[3], validate=True))
    except ValueError as exc:
        raise ErrorCarga('Hash PBKDF2 no válido.') from exc
    if longitud != 32:
        raise ErrorCarga('Hash PBKDF2 no válido.')


def _objeto_json(pares):
    objeto = {}
    for clave, valor in pares:
        if clave in objeto:
            raise ErrorCarga('El JSON contiene nombres de campos repetidos.')
        objeto[clave] = valor
    return objeto


def leer_paquete(ruta, sha256):
    if not isinstance(sha256, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', sha256):
        raise ErrorCarga('Indica la huella SHA256 completa del archivo.')
    ruta = Path(ruta)
    if not ruta.is_file() or not 1 <= ruta.stat().st_size <= MAX_BYTES:
        raise ErrorCarga('Archivo ausente, vacío o mayor de 64 MiB.')
    with ruta.open('rb') as archivo:
        contenido = archivo.read(MAX_BYTES + 1)
    if len(contenido) > MAX_BYTES or hashlib.sha256(contenido).hexdigest() != sha256.lower():
        raise ErrorCarga('La huella SHA256 no coincide con el archivo recibido.')
    try:
        return validar_paquete(json.loads(contenido, object_pairs_hook=_objeto_json))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ErrorCarga('El archivo no contiene un JSON admitido.') from exc


def validar_paquete(datos):
    datos = deepcopy(datos)
    _campos(datos, 'schema lote fecha zona_horaria ventana_inicio ventana_fin origen analisis_metodo cuentas', 'paquete')
    if datos['schema'] != SCHEMA or datos['origen'] != 'demostracion' or datos['analisis_metodo'] != 'anotacion_estructurada_v1':
        raise ErrorCarga('Esquema, procedencia o método de análisis no compatible.')
    if not isinstance(datos['lote'], str) or not re.fullmatch(r'[a-z0-9-]{3,80}', datos['lote']) or datos['zona_horaria'] != 'America/Lima':
        raise ErrorCarga('Identificador de lote o zona horaria no válido.')
    try:
        dia = date.fromisoformat(datos['fecha'])
    except (ValueError, TypeError) as exc:
        raise ErrorCarga('Fecha del lote no válida.') from exc
    inicio, fin = _fecha(datos['ventana_inicio']), _fecha(datos['ventana_fin'])
    if inicio.date() != dia or fin.date() != dia or inicio.hour != 13 or inicio.minute or inicio.second or inicio.microsecond or fin != inicio + timedelta(hours=5):
        raise ErrorCarga('La ventana del lote debe abarcar de 13:00 a 18:00 del día indicado.')
    if fin > timezone.now():
        raise ErrorCarga('El lote no puede contener actividad futura.')
    cuentas = datos['cuentas']
    if not isinstance(cuentas, list) or not 1 <= len(cuentas) <= 500:
        raise ErrorCarga('El paquete necesita entre 1 y 500 cuentas.')
    claves, emails, ids = set(), set(), set()
    cantidad_mensajes = cantidad_evidencias = 0
    for cuenta in cuentas:
        _campos(cuenta, 'clave nombre email password_hash fecha_alta inicio mensajes', 'cuenta')
        if not isinstance(cuenta['clave'], str) or not re.fullmatch(r'a\d{3}', cuenta['clave']) or cuenta['clave'] in claves:
            raise ErrorCarga('Clave de cuenta repetida o no válida.')
        claves.add(cuenta['clave'])
        _texto(cuenta['nombre'], 2, 150, 'nombre')
        email = cuenta['email']
        try:
            validate_email(email)
        except (ValidationError, TypeError) as exc:
            raise ErrorCarga('Correo de cuenta no válido.') from exc
        if not isinstance(email, str) or len(email) > 150 or email != email.lower() or not email.endswith('@example.com') or email in emails:
            raise ErrorCarga('Las cuentas de esta carga necesitan correos únicos en example.com.')
        emails.add(email)
        _hash_password(cuenta['password_hash'])
        cuenta['fecha_alta'] = _fecha(cuenta['fecha_alta'])
        cuenta['inicio'] = _fecha(cuenta['inicio'])
        if not inicio - timedelta(days=30) <= cuenta['fecha_alta'] <= cuenta['inicio'] <= fin or cuenta['inicio'] < inicio:
            raise ErrorCarga('El alta o el inicio de una cuenta está fuera del periodo admitido.')
        mensajes = cuenta['mensajes']
        if not isinstance(mensajes, list) or not 40 <= len(mensajes) <= 60 or len(mensajes) % 2:
            raise ErrorCarga('Cada cuenta necesita de 40 a 60 mensajes alternados y completos.')
        anterior = None
        for indice, mensaje in enumerate(mensajes):
            _campos(mensaje, 'id remitente contenido fecha respuesta_a evidencias', 'mensaje')
            mensaje['id'] = _uuid(mensaje['id'])
            if mensaje['id'] in ids:
                raise ErrorCarga('Identificador de mensaje repetido.')
            ids.add(mensaje['id'])
            esperado = 'usuario' if indice % 2 == 0 else 'asistente'
            if mensaje['remitente'] != esperado:
                raise ErrorCarga('Los mensajes deben alternar estudiante y asistente.')
            _texto(mensaje['contenido'], 1, 2000, 'mensaje')
            mensaje['fecha'] = _fecha(mensaje['fecha'])
            if not inicio <= mensaje['fecha'] <= fin or (anterior and mensaje['fecha'] <= anterior['fecha']):
                raise ErrorCarga('Mensaje fuera de horario o fechas sin orden estricto.')
            if indice == 0 and mensaje['fecha'] != cuenta['inicio']:
                raise ErrorCarga('El periodo debe comenzar con el primer mensaje.')
            if esperado == 'usuario':
                if mensaje['respuesta_a'] is not None:
                    raise ErrorCarga('Un mensaje de estudiante no puede apuntar a una respuesta.')
            else:
                mensaje['respuesta_a'] = _uuid(mensaje['respuesta_a'])
                if mensaje['respuesta_a'] != anterior['id']:
                    raise ErrorCarga('La respuesta no pertenece al mensaje anterior de su cuenta.')
            evidencias = mensaje['evidencias']
            if not isinstance(evidencias, list) or len(evidencias) > 21 or (esperado == 'asistente' and evidencias):
                raise ErrorCarga('Evidencias no válidas para el mensaje.')
            vistas = set()
            for evidencia in evidencias:
                _campos(evidencia, 'indicador cita senal observacion', 'evidencia')
                codigo, senal = evidencia['indicador'], evidencia['senal']
                if not isinstance(codigo, str) or codigo not in SENALES_INDICADOR or senal not in SENALES_INDICADOR[codigo]:
                    raise ErrorCarga('Indicador o señal no válido.')
                cita = _texto(evidencia['cita'], 1, 400, 'cita')
                _texto(evidencia['observacion'], 1, 1000, 'observación')
                if cita not in mensaje['contenido'] or (codigo, cita) in vistas:
                    raise ErrorCarga('Cita ajena al mensaje o evidencia duplicada.')
                vistas.add((codigo, cita))
            cantidad_evidencias += len(evidencias)
            anterior = mensaje
        cantidad_mensajes += len(mensajes)
    if cantidad_mensajes > 30000 or cantidad_evidencias > 60000:
        raise ErrorCarga('El paquete supera los límites de mensajes o evidencias.')
    datos['_conteos'] = {'cuentas': len(cuentas), 'mensajes': cantidad_mensajes, 'evidencias': cantidad_evidencias}
    return datos


def comprobar_entorno():
    if connection.vendor != 'sqlite':
        raise ErrorCarga('Este comando de carga requiere la base SQLite configurada por el proyecto.')
    # Un servicio antiguo puede considerar su propio grafo de migraciones
    # completo aunque todavía no conozca los cambios que necesita este paquete.
    requeridos_modelos = {
        Perfil: ('origen_datos', 'terminos_version', 'terminos_aceptados_en'),
        Mensaje: ('eliminar_despues_de', 'retencion_version'),
        SesionSemanal: ('fin',),
    }
    try:
        for modelo, campos in requeridos_modelos.items():
            for campo in campos:
                modelo._meta.get_field(campo)
        if not SesionSemanal._meta.get_field('fin').null:
            raise ErrorCarga(ERROR_VERSION)
    except FieldDoesNotExist as exc:
        raise ErrorCarga(ERROR_VERSION) from exc
    nombre = str(connection.settings_dict['NAME'])
    if nombre == ':memory:' or nombre.startswith('file:') or not Path(nombre).is_file():
        raise ErrorCarga('La base configurada debe existir y estar migrada; no se creará una base nueva.')
    executor = MigrationExecutor(connection)
    if not MIGRACIONES_REQUERIDAS.issubset(executor.loader.disk_migrations) or not MIGRACIONES_REQUERIDAS.issubset(executor.loader.applied_migrations):
        raise ErrorCarga(ERROR_VERSION)
    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
        raise ErrorCarga('Hay migraciones pendientes. Aplícalas antes de realizar la carga.')
    requeridos = {'usuarios_perfil', 'sesiones_sesionsemanal', 'chat_mensaje', 'reportes_evidencia', 'reportes_reportesemanal'}
    if not requeridos.issubset(set(connection.introspection.table_names())):
        raise ErrorCarga('La base configurada no contiene las tablas requeridas.')
    with connection.cursor() as cursor:
        for modelo, campos in requeridos_modelos.items():
            columnas = {campo.name: campo for campo in connection.introspection.get_table_description(cursor, modelo._meta.db_table)}
            if any(modelo._meta.get_field(nombre_campo).column not in columnas for nombre_campo in campos):
                raise ErrorCarga(ERROR_VERSION)
            if modelo is SesionSemanal and not columnas['fin'].null_ok:
                raise ErrorCarga(ERROR_VERSION)


def _planificar(datos):
    User = get_user_model()
    emails = [c['email'] for c in datos['cuentas']]
    candidatas = list(User.objects.annotate(_login=Lower('username'), _correo=Lower('email')).filter(Q(_login__in=emails) | Q(_correo__in=emails)).select_related('perfil'))
    por_correo = {}
    for usuario in candidatas:
        for correo in {usuario.username.lower(), usuario.email.lower()} & set(emails):
            if correo in por_correo:
                raise ErrorCarga('Colisión entre identidades existentes. No se modificó ninguna cuenta.')
            por_correo[correo] = usuario
    esperados = {m['id']: (c, m) for c in datos['cuentas'] for m in c['mensajes']}
    existentes = {m.pk: m for m in Mensaje.objects.filter(pk__in=esperados)}
    ids_existentes = list(existentes)
    pruebas = {}
    for evidencia in Evidencia.objects.filter(mensaje_id__in=ids_existentes):
        pruebas.setdefault(evidencia.mensaje_id, set()).add((evidencia.indicador, evidencia.cita, evidencia.senal, evidencia.observacion))
    nuevas, omitidas = [], []
    for cuenta in datos['cuentas']:
        usuario = por_correo.get(cuenta['email'])
        if usuario is None:
            if any(m['id'] in existentes for m in cuenta['mensajes']):
                raise ErrorCarga('Un identificador del paquete ya pertenece a otra cuenta.')
            nuevas.append(cuenta)
            continue
        perfil = getattr(usuario, 'perfil', None)
        identidad = (usuario.username, usuario.email, usuario.first_name, usuario.password, usuario.date_joined)
        prevista = (cuenta['email'], cuenta['email'], cuenta['nombre'], cuenta['password_hash'], cuenta['fecha_alta'])
        if identidad != prevista or not usuario.is_active or usuario.is_staff or usuario.is_superuser or usuario.groups.exists() or usuario.user_permissions.exists():
            raise ErrorCarga('Una cuenta existente no coincide con la identidad del paquete. Carga cancelada.')
        if perfil is None or perfil.origen_datos != 'demostracion' or perfil.inicio_programa != cuenta['inicio'] or perfil.terminos_version or perfil.terminos_aceptados_en is not None:
            raise ErrorCarga('Una cuenta existente no tiene la procedencia y configuración esperadas.')
        if perfil.respuesta_hasta and perfil.respuesta_hasta > timezone.now():
            raise ErrorCarga('Una cuenta del paquete tiene una respuesta en curso. Reintenta más tarde.')
        sesion = SesionSemanal.objects.filter(usuario=usuario, numero=1).first()
        if sesion is None or sesion.inicio != cuenta['inicio'] or sesion.fin is not None or sesion.estado != 'activa':
            raise ErrorCarga('El periodo existente no coincide con el paquete.')
        for item in cuenta['mensajes']:
            mensaje = existentes.get(item['id'])
            estado = (usuario.pk, sesion.pk, item['remitente'], item['contenido'], item['fecha'], item['respuesta_a'], item['id'] if item['remitente'] == 'usuario' else None)
            if mensaje is None or (mensaje.usuario_id, mensaje.sesion_id, mensaje.remitente, mensaje.contenido, mensaje.fecha, mensaje.respuesta_a_id, mensaje.clave_envio) != estado:
                raise ErrorCarga('Un mensaje existente difiere del paquete. No se sobrescribió.')
            if mensaje.analisis_estado != 'listo' or mensaje.analisis_hasta is not None or mensaje.respuesta_error or mensaje.eliminar_despues_de is not None or mensaje.retencion_version:
                raise ErrorCarga('Un mensaje existente tiene un estado incompatible con la carga.')
            pruebas_esperadas = {(e['indicador'], e['cita'], e['senal'], e['observacion']) for e in item['evidencias']}
            if pruebas.get(mensaje.pk, set()) != pruebas_esperadas:
                raise ErrorCarga('Las evidencias existentes difieren del paquete. No se sobrescribieron.')
        omitidas.append(cuenta)
    return nuevas, omitidas


def _crear_respaldo(ruta=None):
    origen = Path(connection.settings_dict['NAME']).resolve()
    if ruta is None:
        nombre = timezone.now().strftime('%Y%m%dT%H%M%S%f')
        ruta = origen.parent / 'cargas' / f'respaldo-{nombre}-{uuid.uuid4().hex[:8]}.sqlite3'
    ruta = Path(ruta).resolve()
    if ruta == origen or ruta.exists() or str(ruta).startswith(str(origen) + '-'):
        raise ErrorCarga('El respaldo necesita una ruta nueva, distinta de la base activa.')
    ruta.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(str(ruta), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with closing(sqlite3.connect(origen.as_uri() + '?mode=ro', uri=True, timeout=20)) as db, closing(sqlite3.connect(str(ruta))) as destino:
            db.backup(destino, pages=128)
    except Exception:
        ruta.unlink(missing_ok=True)
        raise
    return str(ruta)


def importar_paquete(datos, aplicar=False, respaldo=None, validar_entorno=True):
    """Recibe el resultado de leer_paquete/validar_paquete, nunca fixtures Django.

    validar_entorno=False se reserva para las bases temporales del test runner.
    """
    if validar_entorno:
        comprobar_entorno()
    nuevas, omitidas = _planificar(datos)
    resultado = {'lote': datos['lote'], 'modo': 'aplicar' if aplicar else 'validar', **datos['_conteos'], 'cuentas_nuevas': len(nuevas), 'cuentas_existentes': len(omitidas), 'cuentas_creadas': 0}
    if not aplicar or not nuevas:
        return resultado
    resultado['respaldo'] = _crear_respaldo(respaldo)
    with transaction.atomic():
        # SQLite reserva la escritura antes de las lecturas de colisiones. Ninguna
        # fila se modifica; una transacción competidora no puede intercalarse.
        with connection.cursor() as cursor:
            cursor.execute('UPDATE usuarios_perfil SET conectado = conectado WHERE 1 = 0')
        nuevas, omitidas = _planificar(datos)
        for cuenta in nuevas:
            usuario = get_user_model().objects.create(username=cuenta['email'], email=cuenta['email'], first_name=cuenta['nombre'], password=cuenta['password_hash'], date_joined=cuenta['fecha_alta'], is_active=True, is_staff=False, is_superuser=False)
            Perfil.objects.create(usuario=usuario, inicio_programa=cuenta['inicio'], ultima_actividad=cuenta['mensajes'][-1]['fecha'], conectado=False, origen_datos='demostracion', terminos_version='', terminos_aceptados_en=None)
            sesion = SesionSemanal.objects.create(usuario=usuario, numero=1, inicio=cuenta['inicio'], fin=None, estado='activa')
            for item in cuenta['mensajes']:
                mensaje = Mensaje.objects.create(id=item['id'], usuario=usuario, sesion=sesion, contenido=item['contenido'], remitente=item['remitente'], fecha=item['fecha'], clave_envio=item['id'] if item['remitente'] == 'usuario' else None, respuesta_a_id=item['respuesta_a'], analisis_estado='listo')
                Evidencia.objects.bulk_create([Evidencia(mensaje=mensaje, **e) for e in item['evidencias']])
            reporte = actualizar_reporte(sesion)
            reporte.nota += NOTA_CARGA
            reporte.save(update_fields=['nota'])
        resultado.update(cuentas_creadas=len(nuevas), cuentas_existentes=len(omitidas))
    return resultado
