"""Traslada exclusivamente el lote ficticio entre una base aislada y el VPS.

Nunca restaura una base sobre producción ni importa usuarios/contraseñas al VPS.
Las respuestas y evidencias siguen siendo generadas por las funciones de la app.
"""
import argparse
from datetime import datetime, timedelta
import gzip
import json
from pathlib import Path
import sqlite3
import uuid

if __package__:
    from .cargar import Carga, bloqueo, conectar, guardar, leer
else:
    from cargar import Carga, bloqueo, conectar, guardar, leer


def paquete(carga):
    from django.core import serializers
    from django.contrib.auth import get_user_model
    from usuarios.models import Perfil
    from sesiones.models import SesionSemanal
    from chat.models import Mensaje
    from reportes.models import Evidencia
    ids = [carga.usuario(p['clave']).pk for p in carga.personas]
    objetos = []
    for qs in [get_user_model().objects.filter(pk__in=ids), Perfil.objects.filter(usuario_id__in=ids),
               SesionSemanal.objects.filter(usuario_id__in=ids), Mensaje.objects.filter(usuario_id__in=ids),
               Evidencia.objects.filter(mensaje__usuario_id__in=ids)]:
        objetos.extend(json.loads(serializers.serialize('json', qs)))
    return {'manifiesto': carga.manifiesto, 'objetos': objetos}


def escribir_comprimido(ruta, datos):
    contenido = gzip.compress(json.dumps(datos, ensure_ascii=False).encode('utf-8'))
    ruta = Path(ruta)
    temporal = ruta.with_suffix(ruta.suffix + '.tmp')
    temporal.write_bytes(contenido)
    temporal.chmod(0o600)
    temporal.replace(ruta)


def leer_comprimido(ruta):
    return json.loads(gzip.decompress(Path(ruta).read_bytes()))


def congelar_y_exportar(carga, destino):
    from django.conf import settings
    from django.db import transaction
    from django.utils import timezone
    from chat.models import Mensaje
    if not (carga.carpeta / 'detener').exists():
        raise ValueError('Primero detén el supervisor entre operaciones.')
    with bloqueo(carga.carpeta):
        ids = [carga.usuario(p['clave']).pk for p in carga.personas]
        activos = Mensaje.objects.filter(usuario_id__in=ids, analisis_estado='procesando', analisis_hasta__gt=timezone.now())
        if activos.exists():
            raise ValueError('Un análisis propio sigue activo; espera a que termine.')
        copia = carga.carpeta / 'respaldo-antes-de-acelerar.sqlite3'
        if not copia.exists():
            with sqlite3.connect(str(settings.DATABASES['default']['NAME'])) as db, sqlite3.connect(str(copia)) as respaldo:
                db.backup(respaldo)
            copia.chmod(0o600)
        with transaction.atomic():
            # Solo los mensajes pendientes de este lote; los chats reales continúan.
            Mensaje.objects.filter(usuario_id__in=ids).exclude(analisis_estado='listo').update(analisis_hasta=timezone.now() + timedelta(hours=6))
            escribir_comprimido(destino, paquete(carga))


def sembrar_local(origen, carpeta):
    """Requiere una BD nueva y migrada, seleccionada con DJANGO_DB_PATH."""
    from django.conf import settings
    from django.contrib.auth import get_user_model
    from django.core import serializers
    from django.db import transaction
    from chat.models import Mensaje
    from usuarios.models import Perfil
    carpeta = Path(carpeta).resolve()
    if Path(settings.DATABASES['default']['NAME']).resolve().parent != carpeta:
        raise ValueError('La base aislada debe estar dentro de la carpeta privada indicada.')
    if get_user_model().objects.exists():
        raise ValueError('No se puede sembrar una base con cuentas existentes.')
    datos = leer_comprimido(origen)
    permitidos = {'auth.user', 'usuarios.perfil', 'sesiones.sesionsemanal', 'chat.mensaje', 'reportes.evidencia'}
    if any(o['model'] not in permitidos for o in datos['objetos']):
        raise ValueError('El paquete incluye un modelo no permitido.')
    with transaction.atomic():
        for o in serializers.deserialize('json', json.dumps(datos['objetos'])):
            o.save()
        Perfil.objects.all().update(respuesta_hasta=None, respuesta_token='', conectado=False)
        Mensaje.objects.exclude(analisis_estado='listo').update(analisis_hasta=None, analisis_estado='pendiente')
    guardar(carpeta / 'manifiesto.json', datos['manifiesto'])


def incorporar(carga, datos):
    """Valida todo antes de insertar; jamás reemplaza respuestas ya guardadas."""
    from django.db import transaction
    from chat.models import Mensaje
    from reportes.models import Evidencia
    from reportes.services import actualizar_reporte
    from ml.analisis import INDICADORES, SENALES_INDICADOR
    from sesiones.models import SesionSemanal
    from usuarios.models import Perfil
    if datos['manifiesto'] != carga.manifiesto:
        raise ValueError('El manifiesto de origen no coincide con el lote del servidor.')
    previstos = {}
    sesiones = {}
    ids = []
    for persona in carga.personas:
        usuario = carga.usuario(persona['clave']); ids.append(usuario.pk)
        for n, textos in enumerate(persona['semanas'], 1):
            sesion = SesionSemanal.objects.get(usuario=usuario, numero=n)
            sesiones[sesion.pk] = sesion
            for t, texto in enumerate(textos):
                mid = carga.id_mensaje(persona['clave'], n, t)
                fecha = carga.fecha_visita(sesion, t, len(textos))
                previstos[mid] = (usuario.pk, sesion.pk, texto, fecha, 'usuario', None)
                previstos[uuid.uuid5(mid, 'asistente')] = (usuario.pk, sesion.pk, None, fecha + timedelta(seconds=20), 'asistente', mid)
    entrantes = {}
    evidencias = []
    for o in datos['objetos']:
        if o['model'] == 'chat.mensaje':
            mid = uuid.UUID(o['pk']); f = o['fields']
            if mid not in previstos or mid in entrantes:
                raise ValueError('Mensaje ajeno o repetido en el paquete.')
            uid, sid, texto, fecha, rol, padre = previstos[mid]
            if (f['usuario'], f['sesion'], f['remitente'], datetime.fromisoformat(f['fecha']), uuid.UUID(f['respuesta_a']) if f['respuesta_a'] else None) != (uid, sid, rol, fecha, padre):
                raise ValueError('El mensaje no coincide con su propietario, sesión o fecha prevista.')
            if not isinstance(f['contenido'], str) or not f['contenido'].strip() or (texto is not None and f['contenido'] != texto):
                raise ValueError('Contenido vacío o relato del estudiante modificado.')
            if f['analisis_estado'] != 'listo':
                raise ValueError('El paquete todavía contiene análisis pendientes.')
            if rol == 'usuario' and f['clave_envio'] != str(mid):
                raise ValueError('La clave de envío no coincide.')
            entrantes[mid] = f
        elif o['model'] == 'reportes.evidencia':
            evidencias.append(o['fields'])
        elif o['model'] not in {'auth.user', 'usuarios.perfil', 'sesiones.sesionsemanal'}:
            raise ValueError('El paquete incluye datos no permitidos.')
    for mid, f in entrantes.items():
        if f['remitente'] == 'asistente' and uuid.UUID(f['respuesta_a']) not in entrantes:
            raise ValueError('La respuesta carece de su mensaje de origen.')
        if f['remitente'] == 'usuario' and uuid.uuid5(mid, 'asistente') not in entrantes:
            raise ValueError('El mensaje del estudiante aún no tiene respuesta.')
    vistos = set()
    for e in evidencias:
        mid = uuid.UUID(e['mensaje']); f = entrantes.get(mid)
        clave = (mid, e['indicador'], e['cita'])
        if f is None or f['remitente'] != 'usuario' or e['indicador'] not in INDICADORES or e['senal'] not in SENALES_INDICADOR[e['indicador']] or not e['cita'].strip() or e['cita'] not in f['contenido'] or not e['observacion'].strip() or clave in vistos:
            raise ValueError('Evidencia inválida, repetida o ajena al mensaje.')
        vistos.add(clave)
    # Una sola transacción protege también contra un fallo a mitad de importación.
    with transaction.atomic():
        existentes = {m.pk: m for m in Mensaje.objects.filter(usuario_id__in=ids)}
        if any(mid not in entrantes for mid in existentes):
            raise ValueError('El paquete omite mensajes ya presentes en el servidor.')
        for mid, m in existentes.items():
            f = entrantes[mid]
            if (m.usuario_id, m.sesion_id, m.remitente, m.contenido, m.fecha, m.respuesta_a_id) != (f['usuario'], f['sesion'], f['remitente'], f['contenido'], datetime.fromisoformat(f['fecha']), uuid.UUID(f['respuesta_a']) if f['respuesta_a'] else None):
                raise ValueError('Un mensaje existente difiere; no se sobrescribió.')
            if m.remitente == 'usuario' and m.analisis_estado == 'listo':
                anteriores = set(m.evidencias.values_list('indicador', 'cita', 'senal', 'observacion'))
                nuevas = {(e['indicador'], e['cita'], e['senal'], e['observacion']) for e in evidencias if uuid.UUID(e['mensaje']) == mid}
                if anteriores != nuevas:
                    raise ValueError('El paquete pretende modificar un análisis ya finalizado.')
        for rol in ['usuario', 'asistente']:
            for mid, f in entrantes.items():
                if f['remitente'] != rol or mid in existentes:
                    continue
                Mensaje.objects.create(id=mid, usuario_id=f['usuario'], sesion_id=f['sesion'], contenido=f['contenido'], remitente=rol, fecha=datetime.fromisoformat(f['fecha']), clave_envio=f['clave_envio'], respuesta_a_id=f['respuesta_a'], analisis_estado='listo', analisis_intentos=f['analisis_intentos'])
        for e in evidencias:
            mid = uuid.UUID(e['mensaje'])
            anterior = existentes.get(mid)
            if anterior is None or anterior.analisis_estado != 'listo':
                Evidencia.objects.get_or_create(mensaje_id=mid, indicador=e['indicador'], cita=e['cita'], defaults={'senal': e['senal'], 'observacion': e['observacion']})
        Mensaje.objects.filter(pk__in=entrantes).update(analisis_estado='listo', analisis_hasta=None)
        for sid in sesiones:
            actualizar_reporte(sesiones[sid])
        for uid in ids:
            ultima = Mensaje.objects.filter(usuario_id=uid).order_by('-fecha').first()
            if ultima:
                Perfil.objects.filter(usuario_id=uid).update(ultima_actividad=ultima.fecha, conectado=False, respuesta_hasta=None, respuesta_token='')
    carga.estado(escribir=True)
    carga.exportar()
    return carga.estado()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('accion', choices=['exportar', 'sembrar', 'incorporar'])
    parser.add_argument('--carpeta', required=True)
    parser.add_argument('--archivo', required=True)
    parser.add_argument('--backend', default='/app')
    args = parser.parse_args()
    conectar(args.backend)
    if args.accion == 'sembrar':
        sembrar_local(args.archivo, args.carpeta)
        return
    carga = Carga(Path(__file__).with_name('historias.json'), args.carpeta, 'colegio-20261023-20')
    if args.accion == 'exportar':
        congelar_y_exportar(carga, args.archivo)
    else:
        if not (carga.carpeta / 'detener').exists():
            raise ValueError('El supervisor debe estar detenido antes de incorporar resultados.')
        with bloqueo(carga.carpeta):
            print(json.dumps(incorporar(carga, leer_comprimido(args.archivo))))


if __name__ == '__main__':
    main()
