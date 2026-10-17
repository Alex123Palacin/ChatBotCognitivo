import subprocess
import sys
import time

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Inicia Django y el procesador de semanas juntos para desarrollo local.'

    def add_arguments(self, parser):
        parser.add_argument('--direccion', default='127.0.0.1:8000')
        parser.add_argument('--intervalo', type=int, default=15)

    def handle(self, *args, **options):
        if settings.DEBUG:
            call_command('preparar_admin', stdout=self.stdout, stderr=self.stderr)
        manage = str(settings.BASE_DIR / 'manage.py')
        procesos = []
        try:
            procesos.append(subprocess.Popen([sys.executable, manage, 'procesar_semanas', '--continuo', '--intervalo', str(max(1, options['intervalo']))]))
            procesos.append(subprocess.Popen([sys.executable, manage, 'runserver', options['direccion'], '--noreload']))
            self.stdout.write('Django y el procesador semanal están iniciados. Ctrl+C detiene ambos.')
            while all(p.poll() is None for p in procesos):
                time.sleep(1)
            fallidos = [p.returncode for p in procesos if p.poll() is not None and p.returncode]
            if fallidos:
                raise CommandError('Uno de los procesos no pudo continuar. Revisa su mensaje anterior.')
        except KeyboardInterrupt:
            pass
        finally:
            for proceso in procesos:
                if proceso.poll() is None:
                    proceso.terminate()
            for proceso in procesos:
                try:
                    proceso.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proceso.kill()
                    proceso.wait()
