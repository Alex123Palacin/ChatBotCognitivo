import json

from django.core.management.base import BaseCommand, CommandError

from usuarios.retencion import limpiar_conversaciones


class Command(BaseCommand):
    help = 'Simula o elimina mensajes cuyo plazo aceptado venció; conserva datos heredados.'

    def add_arguments(self, parser):
        modo = parser.add_mutually_exclusive_group()
        modo.add_argument('--dry-run', action='store_true', help='Solo informa conteos, sin borrar (predeterminado).')
        modo.add_argument('--aplicar', action='store_true', help='Confirma la eliminación de mensajes elegibles y reportes derivados.')
        parser.add_argument('--limite', type=int, default=1000, help='Máximo de mensajes vencidos a tratar por lote (1–10000).')

    def handle(self, *args, **options):
        if not 1 <= options['limite'] <= 10000:
            raise CommandError('El límite debe estar entre 1 y 10000.')
        resultado = limpiar_conversaciones(aplicar=options['aplicar'], limite=options['limite'])
        self.stdout.write(json.dumps(resultado, ensure_ascii=False))
