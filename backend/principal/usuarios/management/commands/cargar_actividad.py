import json

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from usuarios.carga_actividad import ErrorCarga, importar_paquete, leer_paquete


class Command(BaseCommand):
    help = 'Valida o importa un paquete de actividad con huella SHA256, sin reemplazar datos existentes.'
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument('archivo', help='Ruta al paquete JSON dentro del servicio backend.')
        parser.add_argument('--sha256', required=True, help='Huella SHA256 de 64 caracteres obtenida del archivo original.')
        parser.add_argument('--aplicar', action='store_true', help='Confirma la escritura; por defecto solo valida.')
        parser.add_argument('--respaldo', help='Ruta nueva para el respaldo SQLite. Por defecto: carpeta cargas junto a la base activa.')

    def handle(self, *args, **options):
        try:
            datos = leer_paquete(options['archivo'], options['sha256'])
            resultado = importar_paquete(datos, aplicar=options['aplicar'], respaldo=options['respaldo'])
        except (ErrorCarga, OSError, DatabaseError) as exc:
            # Los errores de BD pueden incluir valores de columnas; no se imprimen
            # consultas, correos, contraseñas ni contenidos en los registros.
            if isinstance(exc, ErrorCarga):
                mensaje = str(exc)
            elif isinstance(exc, OSError):
                mensaje = 'No se pudo leer el archivo o escribir el respaldo. Revisa rutas y permisos.'
            else:
                mensaje = 'La base rechazó la operación. La transacción no se confirmó; revisa migraciones y concurrencia.'
            raise CommandError(mensaje) from exc
        self.stdout.write(json.dumps(resultado, ensure_ascii=False))
