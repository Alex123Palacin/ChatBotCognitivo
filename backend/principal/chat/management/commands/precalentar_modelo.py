from django.core.management.base import BaseCommand

from ml.ollama import ErrorModelo, precalentar_modelo


class Command(BaseCommand):
    help = 'Carga el modelo de Ollama para reducir la espera de la primera conversación.'

    def handle(self, *args, **options):
        try:
            precalentar_modelo()
        except ErrorModelo:
            # Permite abrir el sitio aunque Ollama esté reiniciándose. El chat
            # conserva su manejo de errores y reintento al volver el modelo.
            self.stderr.write('Ollama no pudo precalentarse. Se volverá a intentar al conversar.')
            return
        self.stdout.write('Modelo cargado y disponible para conversar.')
