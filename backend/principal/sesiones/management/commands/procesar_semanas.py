import time

from django.core.management.base import BaseCommand
from django.db import close_old_connections

from reportes.services import procesar_pendientes
from usuarios.retencion import limpiar_conversaciones


class Command(BaseCommand):
    help = 'Analiza mensajes pendientes, actualiza reportes y aplica los plazos de conservación aceptados.'

    def add_arguments(self, parser):
        parser.add_argument('--continuo', action='store_true', help='Mantiene activo el procesamiento automático.')
        parser.add_argument('--intervalo', type=int, default=15)
        parser.add_argument('--limite', type=int, default=5)

    def handle(self, *args, **options):
        intervalo = max(1, options['intervalo'])
        self.stdout.write('Procesador de conversaciones iniciado. Los plazos se consultan en la base de datos.')
        try:
            while True:
                close_old_connections()
                try:
                    limpieza = limpiar_conversaciones(aplicar=True)
                    if limpieza['mensajes_eliminados']:
                        self.stdout.write(f"Mensajes eliminados por su plazo aceptado: {limpieza['mensajes_eliminados']}.")
                    cantidad = procesar_pendientes(limite=max(1, options['limite']))
                    if cantidad:
                        self.stdout.write(f'Mensajes analizados: {cantidad}.')
                except Exception as exc:
                    # No imprime conversaciones ni contraseñas en los registros.
                    self.stderr.write(f'El procesamiento se reintentará. Tipo de fallo: {type(exc).__name__}.')
                    if not options['continuo']:
                        raise
                if not options['continuo']:
                    break
                time.sleep(intervalo)
        except KeyboardInterrupt:
            self.stdout.write('Procesador de conversaciones detenido.')
