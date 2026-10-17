from django.conf import settings
from django.contrib.staticfiles.management.commands.runserver import Command as RunserverCommand
from django.core.management import call_command


class Command(RunserverCommand):
    def handle(self, *args, **options):
        # Se ejecuta al iniciar el servidor, cuando la base ya fue migrada.
        # No hay consultas a la base de datos al importar o cargar las apps.
        if settings.DEBUG:
            call_command('preparar_admin', stdout=self.stdout, stderr=self.stderr)
        return super().handle(*args, **options)
