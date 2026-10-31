import json
from datetime import datetime
from random import SystemRandom
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from reportes.estudio import CLAVE_ESTUDIO, muestra_actual, muestra_json, muestra_valida
from reportes.models import MuestraEstudio


class Command(BaseCommand):
    help = 'Selecciona una única muestra aleatoria de 110 entre los 136 participantes del 10/09/2026.'

    def add_arguments(self, parser):
        parser.add_argument('--aplicar', action='store_true')
        parser.add_argument('--si-procede', action='store_true',
                            help='En el arranque, espera si aún no están las 136 cuentas elegibles.')

    def handle(self, *args, **options):
        existente = muestra_actual()
        if existente:
            if not muestra_valida(existente):
                raise CommandError('La muestra guardada está incompleta o contiene cuentas ajenas. No se reemplaza ni se vuelve a sortear.')
            self.stdout.write(json.dumps({'existente': True, **muestra_json(existente)}))
            return
        lima = ZoneInfo('America/Lima')
        inicio, fin = datetime(2026, 9, 10, 13, tzinfo=lima), datetime(2026, 9, 10, 18, tzinfo=lima)
        ids = list(get_user_model().objects.filter(
            is_staff=False, is_superuser=False, mensajes_chat__remitente='usuario',
            mensajes_chat__fecha__gte=inicio, mensajes_chat__fecha__lt=fin,
        ).order_by('pk').values_list('pk', flat=True).distinct())
        if len(ids) != 136:
            if options['si_procede']:
                self.stdout.write(json.dumps({'aplicado': False, 'poblacion': len(ids),
                                             'a_seleccionar': 110, 'estado': 'pendiente_de_poblacion'}))
                return
            raise CommandError(f'Se esperaban 136 cuentas elegibles; hay {len(ids)}. No se alteró la selección.')
        if not options['aplicar']:
            self.stdout.write(json.dumps({'aplicado': False, 'poblacion': 136, 'a_seleccionar': 110}))
            return
        with transaction.atomic():
            muestra = MuestraEstudio.objects.create(clave=CLAVE_ESTUDIO, inicio=inicio, fin=fin, tamano=110, poblacion_ids=ids)
            muestra.usuarios.set(SystemRandom().sample(ids, 110))
        self.stdout.write(json.dumps({'aplicado': True, **muestra_json(muestra)}))
