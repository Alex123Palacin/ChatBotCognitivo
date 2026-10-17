from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from usuarios.models import Perfil


class Command(BaseCommand):
    help = 'Prepara el administrador admin/admin exclusivamente para desarrollo local.'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('El administrador predeterminado solo se prepara con DEBUG=True.')

        # get_or_create y la transacción impiden duplicados si se inician dos procesos.
        with transaction.atomic():
            usuario, creado = get_user_model().objects.get_or_create(
                username='admin',
                defaults={
                    'password': make_password('admin'),
                    'first_name': 'Administrador',
                    'is_staff': True,
                    'is_superuser': False,
                    'is_active': True,
                },
            )
            if creado:
                Perfil.objects.create(usuario=usuario)
            elif not usuario.is_staff or not usuario.is_active:
                raise CommandError(
                    'Ya existe el usuario admin sin acceso administrativo activo. '
                    'No se modificó su contraseña ni sus permisos.'
                )

        if creado:
            self.stdout.write(self.style.SUCCESS('Administrador local creado: usuario admin.'))
        else:
            self.stdout.write('El administrador local ya existe; se conservaron su contraseña y sus permisos.')
