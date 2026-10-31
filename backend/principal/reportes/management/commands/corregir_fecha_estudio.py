"""Corrección explícita y auditable de la fecha de la muestra existente."""
import json
import os
from contextlib import closing
from datetime import date, datetime, time, timedelta
from pathlib import Path
import sqlite3
from uuid import uuid4
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from chat.models import Mensaje
from reportes.estudio import muestra_actual, muestra_valida
from sesiones.models import SesionSemanal
from usuarios.models import Perfil

LIMA = ZoneInfo('America/Lima')


def plan_correccion(original, correcta):
    muestra = muestra_actual()
    if not muestra_valida(muestra):
        raise CommandError('Se requiere la muestra completa y válida de 110 estudiantes.')
    if original == correcta:
        raise CommandError('Las dos fechas deben ser diferentes.')
    dias_ventana = {muestra.inicio.astimezone(LIMA).date(), muestra.fin.astimezone(LIMA).date()}
    if dias_ventana not in ({original}, {correcta}):
        raise CommandError('La ventana no coincide con la fecha original ni la corregida.')
    ids = sorted(muestra.usuarios.values_list('pk', flat=True))
    # Exclusión adicional: incluso una membresía incorrecta no puede alterar cuentas de prueba.
    if muestra.usuarios.filter(username__iexact='sujetoprueba').exists():
        raise CommandError('SujetoPrueba no debe pertenecer a la muestra.')
    inicio = datetime.combine(original, time.min, tzinfo=LIMA)
    fin = inicio + timedelta(days=1)
    diferencia = correcta - original
    cambios = []
    campos = [
        (get_user_model(), 'pk__in', ['date_joined']),
        (Perfil, 'usuario_id__in', ['inicio_programa', 'ultima_actividad']),
        (SesionSemanal, 'usuario_id__in', ['inicio', 'fin']),
        (Mensaje, 'usuario_id__in', ['fecha']),
    ]
    for modelo, filtro, nombres in campos:
        for campo in nombres:
            registros = modelo.objects.filter(**{filtro: ids, campo+'__gte': inicio, campo+'__lt': fin})
            for pk, antes in registros.order_by('pk').values_list('pk', campo):
                despues = antes.astimezone(LIMA) + diferencia
                cambios.append({'modelo': modelo._meta.label, 'id': str(pk), 'campo': campo,
                                'antes': antes.isoformat(), 'despues': despues.isoformat()})
    for campo in ['inicio', 'fin']:
        antes = getattr(muestra, campo)
        if antes.astimezone(LIMA).date() == original:
            cambios.append({'modelo': muestra._meta.label, 'id': str(muestra.pk), 'campo': campo,
                            'antes': antes.isoformat(),
                            'despues': (antes.astimezone(LIMA) + diferencia).isoformat()})
    return muestra, ids, cambios


def respaldo_sqlite(destino):
    if connection.vendor != 'sqlite':
        raise CommandError('Este procedimiento de respaldo requiere SQLite.')
    connection.ensure_connection()
    with closing(sqlite3.connect(destino)) as copia:
        connection.connection.backup(copia)
        if copia.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise CommandError('El respaldo no superó la comprobación de integridad.')
    os.chmod(destino, 0o600)


class Command(BaseCommand):
    help = 'Corrige una fecha de la muestra sin volver a seleccionar estudiantes; primero simula.'

    def add_arguments(self, parser):
        parser.add_argument('--fecha-original', required=True)
        parser.add_argument('--fecha-correcta', required=True)
        parser.add_argument('--directorio', default='/data/cargas/correccion_fecha_estudio')
        parser.add_argument('--aplicar', action='store_true')

    def handle(self, *args, **options):
        try:
            original = date.fromisoformat(options['fecha_original'])
            correcta = date.fromisoformat(options['fecha_correcta'])
        except ValueError as exc:
            raise CommandError('Usa fechas con formato AAAA-MM-DD.') from exc
        muestra, ids, cambios = plan_correccion(original, correcta)
        resumen = {'seleccionados': len(ids), 'campos_por_cambiar': len(cambios),
                   'mensajes_por_cambiar': sum(c['modelo'] == 'chat.Mensaje' for c in cambios),
                   'fecha_original': str(original), 'fecha_correcta': str(correcta), 'aplicado': False}
        if not options['aplicar'] or not cambios:
            self.stdout.write(json.dumps(resumen))
            return
        carpeta = Path(options['directorio']).resolve()
        carpeta.mkdir(parents=True, exist_ok=True, mode=0o700)
        sufijo = timezone.now().strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:8]
        respaldo = carpeta / f'respaldo-{sufijo}.sqlite3'
        auditoria = carpeta / f'correccion-{sufijo}.json'
        respaldo_sqlite(respaldo)
        registro = {'estado': 'preparado', 'solicitud': 'Corrección de fecha declarada por el responsable; se conserva la hora de Lima.',
                    'registrado_en': timezone.now().isoformat(), 'zona_horaria': str(LIMA),
                    'muestra': muestra.pk, 'usuarios': ids, 'respaldo': str(respaldo), 'cambios': cambios}
        with auditoria.open('x', encoding='utf-8') as archivo:
            os.chmod(auditoria, 0o600)
            json.dump(registro, archivo, ensure_ascii=False, indent=2)
        from django.apps import apps
        with transaction.atomic():
            _, ids_actuales, actuales = plan_correccion(original, correcta)
            if ids_actuales != ids or actuales != cambios:
                raise CommandError('Los datos cambiaron durante la preparación. No se aplicó la corrección.')
            for cambio in cambios:
                modelo = apps.get_model(cambio['modelo'])
                filtro = {'pk': cambio['id'], cambio['campo']: datetime.fromisoformat(cambio['antes'])}
                if modelo.objects.filter(**filtro).update(**{cambio['campo']: datetime.fromisoformat(cambio['despues'])}) != 1:
                    raise CommandError('Un registro no coincide; se revierte la corrección completa.')
            if plan_correccion(original, correcta)[2]:
                raise CommandError('Quedan cambios pendientes; se revierte la corrección completa.')
        registro['estado'] = 'aplicado'
        auditoria.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding='utf-8')
        resumen.update(aplicado=True, respaldo=str(respaldo), auditoria=str(auditoria))
        self.stdout.write(json.dumps(resumen))
